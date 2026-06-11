"""Batch visual verifier for a brand pack vs. its source slide deck.

For each `<layout>: <source_slide_no>` mapping in the brand's
`verify-map.yaml`, loads the source slide PNG and the rendered layout PNG
and computes:

  - mean_abs_diff        — average absolute pixel difference (0-255)
  - total_diff_ratio     — fraction of pixels with abs-diff > threshold
  - struct_diff_ratio    — same but with picture-slot regions masked out
                           (parses `picture X,Y WxH` primitives from the
                           layout DSL and zeros those pixels first)
  - block_diff_ratio     — the part of struct that survives a morphological
                           opening: solid mismatched regions a DSL edit can
                           fix. The signal the improve-brand loop gates on.
  - edge_diff_ratio      — struct minus block: the thin anti-aliasing /
                           sub-pixel font-metric halo LibreOffice produces
                           against the source PNG. The renderer floor — no
                           DSL tweak removes it. When block ≈ 0 and edge is
                           stuck, the layout is at its fidelity asymptote.
  - regions              — connected components of the block mask, top-N by
                           area: where the fixable mismatch actually is.
  - ssim                 — scikit-image structural similarity 0..1

Per-layout artefacts in `output_dir`:
  - slide-NN_<layout>_overlay.png — 3-panel: source | render | red diff
  - slide-NN_<layout>_mask.png    — single ghost overlay + red mismatch
  - report.json                   — full metrics dict
  - score-trace.jsonl             — append-only per-run scores (for plateau)

Entry point: :func:`run_visual_diff` — returns a process-style exit code
(0 = every requested layout scored, 1 = some layout missing/errored) and
never raises on per-layout problems, so orchestrators
(`scripts/brand_verify_loop.py`) can merge the code into their own
failure accounting instead of losing the partial report to an exception.
The CLI wrapper lives in `scripts/brand_visual_diff.py`.

`verify-map.yaml` schema (in brand pack root):
  layouts:
    cover-dark: 1
    quote: 11
    …
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from feinschliff_builder.verify.verify_map import load_verify_map

DESIGN_W, DESIGN_H = 1920, 1080
DIFF_THRESHOLD = 30
# Morphological opening iterations used to split the structural diff into a
# "block" component (solid mismatched regions — a misplaced/missing/wrong-fill
# element, the part a DSL edit can fix) and an "edge" component (the thin
# anti-aliasing / sub-pixel font-metric halo along every glyph contour, which
# LibreOffice produces against the source PNG export and no DSL tweak removes
# — the renderer floor). 2 iterations with the default 3×3 cross removes
# features thinner than ~4px while preserving solid blocks.
_BLOCK_OPEN_ITERS = 2
# Region attribution: connected components of the block mask smaller than this
# (px) are noise, not a reportable structural region.
_REGION_MIN_AREA = 400
_REGION_TOP_N = 5

_PICTURE_RE = re.compile(
    r"^\s*picture\s+(\d+)\s*,\s*(\d+)\s+(\d+)\s*x\s*(\d+)\b", re.MULTILINE
)


def _picture_boxes(layout_dsl: Path) -> list[tuple[int, int, int, int]]:
    if not layout_dsl.is_file():
        return []
    return [(int(x), int(y), int(w), int(h))
            for x, y, w, h in _PICTURE_RE.findall(layout_dsl.read_text())]


def _picture_mask(boxes: list[tuple[int, int, int, int]]) -> np.ndarray:
    mask = np.zeros((DESIGN_H, DESIGN_W), dtype=bool)
    for x, y, w, h in boxes:
        x0 = max(0, min(DESIGN_W, x))
        y0 = max(0, min(DESIGN_H, y))
        x1 = max(0, min(DESIGN_W, x + w))
        y1 = max(0, min(DESIGN_H, y + h))
        mask[y0:y1, x0:x1] = True
    return mask


def _load_norm(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB").resize((DESIGN_W, DESIGN_H), Image.LANCZOS)
    return np.asarray(im, dtype=np.uint8)


def _open_mask(mask: np.ndarray, iters: int = _BLOCK_OPEN_ITERS) -> np.ndarray:
    """Morphological opening — strip thin features, keep solid blocks.

    The opened mask is the *block* component of the diff: the part that
    survives because it's a contiguous filled region (a misplaced or missing
    element), not a 1–few-px halo along a glyph edge. Returns the input
    unchanged when scipy is unavailable (block then equals struct — the
    metric degrades gracefully rather than failing).
    """
    if not mask.any():
        return mask
    try:
        from scipy import ndimage
    except ImportError:
        return mask
    return ndimage.binary_opening(mask, iterations=iters)


def _block_regions(block_mask: np.ndarray,
                   min_area: int = _REGION_MIN_AREA,
                   top_n: int = _REGION_TOP_N) -> list[dict]:
    """Connected components of the block mask → top-N structural regions.

    Each region is ``{"area", "bbox": [x1,y1,x2,y2], "centroid": [cx,cy]}``.
    These tell the improve-brand loop *where* the fixable mismatch is, so a
    sub-agent can target the specific primitive instead of squinting at a
    full-slide scalar.
    """
    try:
        from scipy import ndimage
    except ImportError:
        return []
    if not block_mask.any():
        return []
    labeled, n = ndimage.label(block_mask)
    if n == 0:
        return []
    sizes = ndimage.sum(block_mask, labeled, range(1, n + 1))
    indexed = sorted(
        [(int(s), i + 1) for i, s in enumerate(sizes) if s >= min_area],
        key=lambda x: -x[0],
    )
    regions = []
    for area, lbl in indexed[:top_n]:
        ys, xs = np.where(labeled == lbl)
        regions.append({
            "area": area,
            "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "centroid": [int(xs.mean()), int(ys.mean())],
        })
    return regions


def _compute_metrics(src: np.ndarray, ren: np.ndarray,
                     pic_mask: np.ndarray | None) -> tuple[dict, np.ndarray, np.ndarray]:
    """Return ``(metrics, struct_per_pixel, block_mask)``.

    ``struct_diff_ratio`` is the flat fraction of non-picture pixels above
    the diff threshold (unchanged, for trace continuity). It is split into:

      - ``block_diff_ratio`` — diff surviving a morphological opening: solid
        mismatched regions a DSL edit can fix. **Gate the loop on this.**
      - ``edge_diff_ratio``  — the thin remainder: the renderer/font-metric
        floor. When block ≈ 0 and edge is stuck, the layout is at the
        asymptote and further DSL tweaking is a budget sink.
    """
    diff = np.abs(src.astype(np.int16) - ren.astype(np.int16)).astype(np.uint8)
    per_pixel = diff.max(axis=2)
    metrics = {
        "mean_abs_diff": round(float(diff.mean()), 2),
        "total_diff_ratio": round(float((per_pixel > DIFF_THRESHOLD).mean()), 4),
    }
    if pic_mask is not None and pic_mask.any():
        # Always mask out picture regions before scoring. Picture slots
        # render the brand's placeholder (or a slot default) where the
        # source has the original illustration, so any diff inside the
        # picture bbox is by-design and tells us nothing about the DSL.
        # Score only the non-picture pixels.
        metrics["picture_coverage"] = round(float(pic_mask.mean()), 3)
        struct = per_pixel.copy()
        struct[pic_mask] = 0
        non_pic = int((~pic_mask).sum())
    else:
        metrics["picture_coverage"] = 0.0
        struct = per_pixel
        non_pic = int(per_pixel.size)

    if non_pic == 0:
        # Pathological: every pixel is inside a picture slot. Fall back to
        # total so the metrics remain defined.
        struct_ratio = metrics["total_diff_ratio"]
        block_mask = np.zeros_like(struct, dtype=bool)
        block_ratio = struct_ratio
    else:
        struct_mask = struct > DIFF_THRESHOLD
        struct_ratio = float(struct_mask.sum() / non_pic)
        block_mask = _open_mask(struct_mask)
        block_ratio = float(block_mask.sum() / non_pic)

    metrics["struct_diff_ratio"] = round(struct_ratio, 4)
    metrics["block_diff_ratio"] = round(block_ratio, 4)
    metrics["edge_diff_ratio"] = round(max(0.0, struct_ratio - block_ratio), 4)

    try:
        from skimage.metrics import structural_similarity as ssim_fn
        metrics["ssim"] = round(float(ssim_fn(src, ren, channel_axis=2, data_range=255)), 4)
    except ImportError:
        metrics["ssim"] = None
    return metrics, struct, block_mask


def _three_panel(src: np.ndarray, ren: np.ndarray, diff_mask: np.ndarray,
                 label: str) -> Image.Image:
    src_gray = np.dot(src[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
    backdrop = np.stack([src_gray] * 3, axis=2)
    diff_img = backdrop.copy()
    diff_img[diff_mask > DIFF_THRESHOLD] = [255, 32, 32]

    panel_w, panel_h = DESIGN_W // 2, DESIGN_H // 2
    gap, header_h = 12, 70
    total_w = panel_w * 3 + gap * 2
    total_h = panel_h + header_h
    page = Image.new("RGB", (total_w, total_h), (250, 250, 250))
    for i, arr in enumerate([src, ren, diff_img]):
        thumb = Image.fromarray(arr).resize((panel_w, panel_h), Image.LANCZOS)
        page.paste(thumb, (i * (panel_w + gap), header_h))
    draw = ImageDraw.Draw(page)
    try:
        font_lg = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except OSError:
        font_lg = font_sm = ImageFont.load_default()
    draw.text((12, 12), label, fill=(20, 20, 20), font=font_lg)
    for i, txt in enumerate(["SOURCE", "RENDER", "DIFF (red = mismatch)"]):
        draw.text((i * (panel_w + gap) + 12, header_h - 24),
                  txt, fill=(80, 80, 80), font=font_sm)
    return page


def _ghost_overlay(src: np.ndarray, ren: np.ndarray,
                   diff_mask: np.ndarray) -> Image.Image:
    blended = ((src.astype(np.float32) + ren.astype(np.float32)) * 0.5).clip(0, 255).astype(np.uint8)
    blended[diff_mask > DIFF_THRESHOLD] = [255, 32, 32]
    return Image.fromarray(blended)


def _render_with_noise(ren: np.ndarray, diff_mask: np.ndarray) -> Image.Image:
    """Render image with red pixels painted wherever it diverges from source.

    Single-layer view — the rendered slide as the base, red ink on every pixel
    the diff scorer counted as a mismatch. Lets a reviewer see "where the
    render is wrong" without the three-image ghosting of `_ghost_overlay`.
    """
    out = ren.copy()
    out[diff_mask > DIFF_THRESHOLD] = [255, 32, 32]
    return Image.fromarray(out)


def _find_diff_hotspots(diff_mask: np.ndarray, min_area: int = 500,
                        top_n: int = 4) -> list[dict]:
    """Connected-component analysis on the diff mask → top-N hotspots.

    Returns `[{"area": int, "bbox": (x1, y1, x2, y2)}]` sorted by area desc.
    Used by the `--loupe` view to crop each high-mismatch region tightly
    so a reviewer (or sub-agent) can read the per-pixel offset that's
    invisible at slide scale.
    """
    try:
        from scipy import ndimage
    except ImportError:
        return []
    mask = diff_mask > DIFF_THRESHOLD
    if not mask.any():
        return []
    labeled, n = ndimage.label(mask)
    if n == 0:
        return []
    sizes = ndimage.sum(mask, labeled, range(1, n + 1))
    indexed = sorted(
        [(int(s), i + 1) for i, s in enumerate(sizes) if s >= min_area],
        key=lambda x: -x[0],
    )
    hotspots = []
    for area, lbl in indexed[:top_n]:
        ys, xs = np.where(labeled == lbl)
        hotspots.append({
            "area": area,
            "bbox": (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
        })
    return hotspots


def _build_loupe_page(layout: str, slide_no: int, hotspot_idx: int,
                      total_hotspots: int, hotspot: dict,
                      src: np.ndarray, ren: np.ndarray,
                      redline: Image.Image, pad: int = 30) -> Image.Image:
    """Render one loupe page: source / render / redline crops at the hotspot."""
    x1, y1, x2, y2 = hotspot["bbox"]
    h_img, w_img = src.shape[:2]
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w_img, x2 + pad)
    y2 = min(h_img, y2 + pad)
    bw, bh = x2 - x1, y2 - y1
    PAGE_W, PAGE_H = 2200, 1200
    page = Image.new("RGB", (PAGE_W, PAGE_H), (252, 252, 252))
    draw = ImageDraw.Draw(page)
    try:
        title_f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        label_f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        foot_f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except OSError:
        title_f = label_f = foot_f = ImageFont.load_default()
    draw.text((40, 30),
              f"{layout}  ·  slide {slide_no:02d}  ·  hotspot {hotspot_idx}/{total_hotspots}",
              fill=(20, 20, 20), font=title_f)
    draw.text((40, 72),
              f"bbox ({x1},{y1})–({x2},{y2})  ·  {bw}×{bh}px  ·  area {hotspot['area']}px",
              fill=(120, 120, 120), font=label_f)
    target_w = (PAGE_W - 80 - 60) // 3
    target_h = max(80, min(int(target_w * bh / max(bw, 1)), PAGE_H - 200))
    top_y = 130
    draw.text((40, top_y - 26), "SOURCE", fill=(60, 90, 200), font=label_f)
    draw.text((40 + target_w + 30, top_y - 26), "RENDER", fill=(200, 60, 60), font=label_f)
    draw.text((40 + 2 * (target_w + 30), top_y - 26), "REDLINE", fill=(120, 60, 140), font=label_f)
    src_crop = Image.fromarray(src).crop((x1, y1, x2, y2)).resize((target_w, target_h), Image.LANCZOS)
    rnd_crop = Image.fromarray(ren).crop((x1, y1, x2, y2)).resize((target_w, target_h), Image.LANCZOS)
    rl_crop = redline.crop((x1, y1, x2, y2)).resize((target_w, target_h), Image.LANCZOS)
    page.paste(src_crop, (40, top_y))
    page.paste(rnd_crop, (40 + target_w + 30, top_y))
    page.paste(rl_crop, (40 + 2 * (target_w + 30), top_y))
    draw.text((40, PAGE_H - 40),
              "loupe view — cropped + scaled to the largest mismatch region; "
              "zoom in to read fine offsets.",
              fill=(140, 140, 140), font=foot_f)
    return page


def _redline_diff(src: np.ndarray, ren: np.ndarray) -> Image.Image:
    """Two-tone diff: source ink in BLUE, render ink in RED, overlap in PURPLE.

    Classic film/print redline. White background, every source-darker-than-mid
    pixel tints blue, every render-darker-than-mid pixel tints red. Where both
    layers have ink at the same place the channels add to purple — instantly
    distinguishing "source only" (blue ghost = thing we should have drawn but
    didn't), "render only" (red ghost = thing we drew that source doesn't have),
    and "matching content" (purple = both layers agree on ink position).
    """
    src_lum = np.dot(src[..., :3], [0.299, 0.587, 0.114])
    ren_lum = np.dot(ren[..., :3], [0.299, 0.587, 0.114])
    # Ink intensity = how dark the pixel is, normalised 0..1. Use a soft floor
    # so the brightest backgrounds don't add residual tint.
    src_ink = np.clip((220.0 - src_lum) / 220.0, 0.0, 1.0)
    ren_ink = np.clip((220.0 - ren_lum) / 220.0, 0.0, 1.0)
    h, w = src_lum.shape
    out = np.full((h, w, 3), 250, dtype=np.uint8)
    # Source ink pulls R+G (leaves blue), render ink pulls G+B (leaves red);
    # overlap pulls G from both sides → purple.
    out[..., 0] = np.clip(250 - src_ink * 220, 0, 255).astype(np.uint8)
    out[..., 1] = np.clip(250 - src_ink * 220 - ren_ink * 220, 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(250 - ren_ink * 220, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


def run_visual_diff(brand_pack: Path, source_dir: Path, render_dir: Path,
                    output_dir: Path, *, only: list[str] | None = None,
                    loupe: bool = False, loupe_top_n: int = 4,
                    loupe_min_area: int = 500) -> int:
    """Score every mapped layout; write overlays + report.json + trace.

    Returns a process-style exit code: 0 when every requested layout was
    scored, 1 when the verify map is missing/malformed, ``only`` matched
    nothing, or any layout was skipped (missing PNG) / errored (corrupt
    PNG). Per-layout problems never raise — the partial report.json and a
    non-zero code are the contract orchestrators rely on.
    """
    try:
        _vm = load_verify_map(brand_pack)
    except FileNotFoundError as exc:
        print(f"{exc} — required for batch verification", flush=True)
        return 1
    except ValueError as exc:
        print(str(exc), flush=True)
        return 1
    layouts_map = dict(_vm.layouts)
    if only:
        wanted = set(only)
        layouts_map = {k: v for k, v in layouts_map.items() if k in wanted}
        if not layouts_map:
            print(f"--only matched no layouts in {brand_pack / 'verify-map.yaml'}",
                  flush=True)
            return 1

    layouts_dir = brand_pack / "layouts"
    output_dir.mkdir(parents=True, exist_ok=True)

    # `scored_now` holds ONLY the layouts freshly scored this run. It is
    # merged into any existing report.json at the end (so a subset run does
    # not delete un-run layouts) and is what the score-trace row records (so
    # plateau detection sees real per-run measurements, not carried-over
    # values). `missing`/`errored` make a partial run fail loudly instead of
    # exiting 0 as if complete.
    scored_now: dict = {}
    missing: list[str] = []
    errored: list[str] = []
    # Loupe pages accumulate across layouts and flush to a single PDF at
    # the end.
    loupe_pages: list[Image.Image] = []
    print(f"{'layout':<28}{'slide':<7}{'total':>8}{'struct':>9}{'block':>8}{'edge':>8}{'ssim':>8}{'cover':>8}")
    print("-" * 86)
    for layout, slide_no in layouts_map.items():
        src_path = source_dir / f"slide-{slide_no:02d}.png"
        ren_path = render_dir / f"{layout}.png"
        if not src_path.is_file() or not ren_path.is_file():
            print(f"{layout:<28}{slide_no:<7}MISSING")
            missing.append(layout)
            continue
        # One corrupt/truncated PNG must not abort the whole batch and leave
        # the prior report.json on disk looking current. Isolate per-layout.
        try:
            src = _load_norm(src_path)
            ren = _load_norm(ren_path)
            boxes = _picture_boxes(layouts_dir / f"{layout}.slide.dsl")
            pic_mask = _picture_mask(boxes) if boxes else None
            metrics, diff, block_mask = _compute_metrics(src, ren, pic_mask)
            regions = _block_regions(block_mask)
        except Exception as exc:  # noqa: BLE001 — surfaced + non-zero exit below
            print(f"{layout:<28}{slide_no:<7}ERROR: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            errored.append(f"{layout}: {type(exc).__name__}: {exc}")
            continue
        scored_now[layout] = {"slide": slide_no, "picture_slots": len(boxes),
                              **metrics, "regions": regions}

        prefix = f"slide-{slide_no:02d}_{layout}"
        label = (f"{layout}   ·   slide-{slide_no:02d}   ·   "
                 f"block {metrics['block_diff_ratio']*100:.1f}%   "
                 f"(struct {metrics['struct_diff_ratio']*100:.1f}%, "
                 f"edge {metrics['edge_diff_ratio']*100:.1f}%)")
        _three_panel(src, ren, diff, label).save(
            output_dir / f"{prefix}_overlay.png", format="PNG", optimize=False)
        _ghost_overlay(src, ren, diff).save(
            output_dir / f"{prefix}_mask.png", format="PNG", optimize=False)
        # Single-layer "render with red where it diverges" — clearer signal
        # for both reviewers and sub-agents than the three-image ghost view.
        # Consumed by the iteration loop's per-layout improvement prompts.
        _render_with_noise(ren, diff).save(
            output_dir / f"{prefix}_noise.png", format="PNG", optimize=False)
        # Redline view: source ink in blue, render ink in red, overlap in
        # purple. Lets a reviewer see at a glance "thing we should have
        # drawn but didn't" (blue ghost) vs "thing we drew that doesn't
        # belong" (red ghost) vs "matching content" (purple).
        redline_img = _redline_diff(src, ren)
        redline_img.save(output_dir / f"{prefix}_redline.png",
                         format="PNG", optimize=False)

        # Loupe hotspots (Split-and-Polish technique): connected-component
        # analysis of the diff mask surfaces the 3-5 worst localised
        # mismatches per layout, each cropped + scaled so per-pixel offsets
        # become readable. Lets a reviewer or sub-agent target specific
        # primitives instead of squinting at the full-slide redline.
        if loupe:
            hotspots = _find_diff_hotspots(diff, min_area=loupe_min_area,
                                           top_n=loupe_top_n)
            for idx, hs in enumerate(hotspots, 1):
                loupe_pages.append(_build_loupe_page(
                    layout, slide_no, idx, len(hotspots), hs,
                    src, ren, redline_img,
                ))

        ssim_s = f"{metrics['ssim']:.3f}" if metrics["ssim"] is not None else "—"
        print(f"{layout:<28}{slide_no:<7}"
              f"{metrics['total_diff_ratio']*100:>7.2f}%"
              f"{metrics['struct_diff_ratio']*100:>8.2f}%"
              f"{metrics['block_diff_ratio']*100:>7.2f}%"
              f"{metrics['edge_diff_ratio']*100:>7.2f}%"
              f"{ssim_s:>8}"
              f"{metrics['picture_coverage']*100:>7.1f}%")

    # Merge into any existing report.json so a subset run (--only) UPDATES the
    # scored layouts without deleting the rest. Reading the full layout set
    # from report.json (e.g. the improve-brand selector) then still sees every
    # known layout, with the ones scored this run refreshed.
    report_path = output_dir / "report.json"
    report: dict = {}
    if report_path.is_file():
        try:
            report = json.loads(report_path.read_text())
            if not isinstance(report, dict):
                report = {}
        except (json.JSONDecodeError, OSError):
            report = {}
    report.update(scored_now)
    report_path.write_text(json.dumps(report, indent=2))
    trace_path = output_dir / "score-trace.jsonl"
    # The trace row records ONLY layouts measured THIS run — plateau detection
    # must not mistake a carried-over score for a fresh measurement.
    with open(trace_path, "a") as f:
        f.write(json.dumps({
            "ts": int(time.time()),
            # `scores` stays struct_diff_ratio for plateau-tool continuity;
            # `block_scores` tracks the fixable signal the loop now gates on.
            "scores": {k: v["struct_diff_ratio"] for k, v in scored_now.items()},
            "block_scores": {k: v["block_diff_ratio"] for k, v in scored_now.items()},
        }) + "\n")
    print(f"\nwrote {len(scored_now)} overlay+mask pairs to {output_dir}")
    print(f"wrote {report_path} ({len(scored_now)} scored this run, "
          f"{len(report)} total)")
    print(f"appended to {trace_path}")
    if loupe_pages:
        loupe_pdf = output_dir / "loupe-hotspots.pdf"
        loupe_pages[0].save(loupe_pdf, format="PDF", save_all=True,
                            append_images=loupe_pages[1:], resolution=150)
        print(f"wrote loupe view → {loupe_pdf} ({len(loupe_pages)} pages)")
    # A partial run must not read as a clean one. Surface skipped/errored
    # layouts and return non-zero so the orchestrator counts the run partial.
    if missing or errored:
        if missing:
            print(f"\n⚠ {len(missing)} layout(s) had no source/render PNG and "
                  f"were NOT scored: {', '.join(missing)}", file=sys.stderr)
        for e in errored:
            print(f"  ✗ {e}", file=sys.stderr)
        return 1
    return 0
