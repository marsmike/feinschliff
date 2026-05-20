#!/usr/bin/env python3
"""Batch visual verifier for a brand pack vs. its source slide deck.

For each `<layout>: <source_slide_no>` mapping in the brand's
`verify-map.yaml`, loads the source slide PNG and the rendered layout PNG
and computes:

  - mean_abs_diff        — average absolute pixel difference (0-255)
  - total_diff_ratio     — fraction of pixels with abs-diff > threshold
  - struct_diff_ratio    — same but with picture-slot regions masked out
                           (parses `picture X,Y WxH` primitives from the
                           layout DSL and zeros those pixels first)
  - ssim                 — scikit-image structural similarity 0..1

Per-layout artefacts in `<output-dir>/`:
  - slide-NN_<layout>_overlay.png — 3-panel: source | render | red diff
  - slide-NN_<layout>_mask.png    — single ghost overlay + red mismatch
  - report.json                   — full metrics dict
  - score-trace.jsonl             — append-only per-run scores (for plateau)

Usage:
  python scripts/brand_visual_diff.py \
      --brand-pack brands/<brand> \
      --source-dir <source-png-dir> \
      --render-dir out/png \
      --output-dir out/verify

`verify-map.yaml` schema (in brand pack root):
  layouts:
    cover-dark: 1
    quote: 11
    …
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

DESIGN_W, DESIGN_H = 1920, 1080
DIFF_THRESHOLD = 30

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


def _compute_metrics(src: np.ndarray, ren: np.ndarray,
                     pic_mask: np.ndarray | None) -> tuple[dict, np.ndarray]:
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
        coverage = float(pic_mask.mean())
        metrics["picture_coverage"] = round(coverage, 3)
        struct = per_pixel.copy()
        struct[pic_mask] = 0
        non_pic = int((~pic_mask).sum())
        if non_pic == 0:
            # Pathological: every pixel is inside a picture slot. Fall
            # back to total so the metric remains defined.
            metrics["struct_diff_ratio"] = metrics["total_diff_ratio"]
        else:
            metrics["struct_diff_ratio"] = round(
                float((struct > DIFF_THRESHOLD).sum() / non_pic), 4
            )
        per_pixel = struct
    else:
        metrics["struct_diff_ratio"] = metrics["total_diff_ratio"]
        metrics["picture_coverage"] = 0.0
    try:
        from skimage.metrics import structural_similarity as ssim_fn
        metrics["ssim"] = round(float(ssim_fn(src, ren, channel_axis=2, data_range=255)), 4)
    except ImportError:
        metrics["ssim"] = None
    return metrics, per_pixel


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
    # Subtract source ink from R+G channels (leaves blue), render ink from G+B
    # (leaves red). Overlap subtracts G from both → purple.
    out[..., 0] = np.clip(250 - src_ink * 220, 0, 255).astype(np.uint8)  # source pulls R
    out[..., 1] = np.clip(250 - src_ink * 220 - ren_ink * 220, 0, 255).astype(np.uint8)  # both pull G
    out[..., 2] = np.clip(250 - ren_ink * 220, 0, 255).astype(np.uint8)  # render pulls B
    # Correction: above subtracts source ink from R channel — we want the
    # opposite (source = blue, so subtract from R+G, leave B). Recompute clean:
    out[..., 0] = np.clip(250 - src_ink * 220, 0, 255).astype(np.uint8)
    out[..., 1] = np.clip(250 - src_ink * 220 - ren_ink * 220, 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(250 - ren_ink * 220, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--brand-pack", type=Path, required=True,
                   help="Brand pack root (contains verify-map.yaml + layouts/)")
    p.add_argument("--source-dir", type=Path, required=True,
                   help="Directory with slide-NN.png exports from the source deck")
    p.add_argument("--render-dir", type=Path, required=True,
                   help="Directory with <layout>.png renders of the brand pack")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="Where to write overlay/mask images + report.json + score trace")
    p.add_argument("--only", nargs="*",
                   help="Restrict to a subset of layouts (by name). Keeps the "
                        "report and score-trace consistent when an orchestrator "
                        "is iterating on a subset of verify-map.yaml.")
    args = p.parse_args()

    map_path = args.brand_pack / "verify-map.yaml"
    if not map_path.is_file():
        print(f"missing {map_path} — required for batch verification", flush=True)
        return 1
    verify_map = yaml.safe_load(map_path.read_text())
    layouts_map = verify_map.get("layouts", {})
    if args.only:
        wanted = set(args.only)
        layouts_map = {k: v for k, v in layouts_map.items() if k in wanted}
        if not layouts_map:
            print(f"--only matched no layouts in {map_path}", flush=True)
            return 1

    layouts_dir = args.brand_pack / "layouts"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report = {}
    print(f"{'layout':<28}{'slide':<7}{'total':>8}{'struct':>9}{'ssim':>8}{'cover':>8}")
    print("-" * 70)
    for layout, slide_no in layouts_map.items():
        src_path = args.source_dir / f"slide-{slide_no:02d}.png"
        ren_path = args.render_dir / f"{layout}.png"
        if not src_path.is_file() or not ren_path.is_file():
            print(f"{layout:<28}{slide_no:<7}MISSING")
            continue
        src = _load_norm(src_path)
        ren = _load_norm(ren_path)
        boxes = _picture_boxes(layouts_dir / f"{layout}.slide.dsl")
        pic_mask = _picture_mask(boxes) if boxes else None
        metrics, diff = _compute_metrics(src, ren, pic_mask)
        report[layout] = {"slide": slide_no, "picture_slots": len(boxes), **metrics}

        prefix = f"slide-{slide_no:02d}_{layout}"
        label = (f"{layout}   ·   slide-{slide_no:02d}   ·   "
                 f"struct {metrics['struct_diff_ratio']*100:.1f}%   "
                 f"(total {metrics['total_diff_ratio']*100:.1f}%)")
        _three_panel(src, ren, diff, label).save(
            args.output_dir / f"{prefix}_overlay.png", format="PNG", optimize=False)
        _ghost_overlay(src, ren, diff).save(
            args.output_dir / f"{prefix}_mask.png", format="PNG", optimize=False)
        # Single-layer "render with red where it diverges" — clearer signal
        # for both reviewers and sub-agents than the three-image ghost view.
        # Consumed by the iteration loop's per-layout improvement prompts.
        _render_with_noise(ren, diff).save(
            args.output_dir / f"{prefix}_noise.png", format="PNG", optimize=False)
        # Redline view: source ink in blue, render ink in red, overlap in
        # purple. Lets a reviewer see at a glance "thing we should have
        # drawn but didn't" (blue ghost) vs "thing we drew that doesn't
        # belong" (red ghost) vs "matching content" (purple).
        _redline_diff(src, ren).save(
            args.output_dir / f"{prefix}_redline.png", format="PNG", optimize=False)

        ssim_s = f"{metrics['ssim']:.3f}" if metrics["ssim"] is not None else "—"
        print(f"{layout:<28}{slide_no:<7}"
              f"{metrics['total_diff_ratio']*100:>7.2f}%"
              f"{metrics['struct_diff_ratio']*100:>8.2f}%"
              f"{ssim_s:>8}"
              f"{metrics['picture_coverage']*100:>7.1f}%")

    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2))
    trace_path = args.output_dir / "score-trace.jsonl"
    with open(trace_path, "a") as f:
        f.write(json.dumps({
            "ts": int(time.time()),
            "scores": {k: v["struct_diff_ratio"] for k, v in report.items()},
        }) + "\n")
    print(f"\nwrote {len(report)} overlay+mask pairs to {args.output_dir}")
    print(f"wrote {args.output_dir / 'report.json'}")
    print(f"appended to {trace_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
