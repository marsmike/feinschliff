#!/usr/bin/env python3
"""Compose a before/after PDF from a completed improve-brand iteration.

Given a brand pack that has run the verify-loop with
`--snapshot-baseline` (which copies the first-iteration renders into
`render-png.before/`) and then iterated to a final set of renders, this
script produces a single PDF: one page per layout, three panels
(source | before | after) with the per-layout struct_diff_ratio at each
stage so a reviewer can see at a glance which layouts improved.

Drop-in usage (after improve-brand has converged):

  uv run python scripts/brand_before_after_pdf.py \\
      --brand-pack brands/<brand>

Outputs `<output-dir>/before-after.pdf` (defaults to
`out/<brand>/verify-loop/before-after.pdf`).

Reads:
  <output-dir>/source-png/slide-NN.png         — required (every slide in verify-map)
  <output-dir>/render-png.before/<layout>.png  — required (the baseline snapshot)
  <output-dir>/render-png/<layout>.png         — required (the latest render)
  <output-dir>/diff/score-trace.jsonl          — optional (first + last row give
                                                 per-layout score deltas)
  <output-dir>/diff/report.json                — optional (current per-layout scores)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]

PAGE_W, PAGE_H = 1920, 1080      # rendering canvas (px); PDF inherits aspect
PANEL_W, PANEL_H = 580, 326      # 16:9 thumbnails
GAP = 30
TOP_BAND = 110
CAPTION_GAP = 18
CAPTION_H = 80


def _font(size: int) -> ImageFont.ImageFont:
    """Best-effort font lookup. Falls back to PIL default at small sizes."""
    for cand in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        if Path(cand).is_file():
            return ImageFont.truetype(cand, size)
    return ImageFont.load_default()


def _load_score_history(score_trace: Path) -> tuple[dict, dict]:
    """Return (first, last) {layout: struct_diff_ratio} maps from score-trace.jsonl."""
    if not score_trace.is_file():
        return {}, {}
    rows = [json.loads(line) for line in score_trace.read_text().splitlines() if line.strip()]
    if not rows:
        return {}, {}
    return rows[0].get("scores", {}), rows[-1].get("scores", {})


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x * 100:.2f}%"


def _verdict(before: float | None, after: float | None) -> tuple[str, tuple[int, int, int]]:
    if before is None or after is None:
        return "—", (90, 90, 90)
    delta = before - after
    if after <= 0.05:
        return f"GREEN  Δ{delta * 100:+.2f} pp", (40, 130, 60)
    if delta >= 0.005:
        return f"improved Δ{delta * 100:+.2f} pp", (40, 90, 160)
    if delta <= -0.005:
        return f"regressed Δ{delta * 100:+.2f} pp", (170, 60, 40)
    return f"plateau Δ{delta * 100:+.2f} pp", (140, 100, 30)


def _panel(canvas: Image.Image, png_path: Path, x: int, y: int,
           caption: str, sub: str | None = None) -> None:
    box_color = (215, 215, 215)
    canvas.paste(box_color, (x, y, x + PANEL_W, y + PANEL_H))
    if png_path.is_file():
        thumb = Image.open(png_path).convert("RGB")
        thumb.thumbnail((PANEL_W, PANEL_H), Image.LANCZOS)
        ox = x + (PANEL_W - thumb.width) // 2
        oy = y + (PANEL_H - thumb.height) // 2
        canvas.paste(thumb, (ox, oy))
    draw = ImageDraw.Draw(canvas)
    cap_y = y + PANEL_H + CAPTION_GAP
    draw.text((x, cap_y), caption, fill=(35, 35, 35), font=_font(28))
    if sub:
        draw.text((x, cap_y + 36), sub, fill=(90, 90, 90), font=_font(22))


def _page(layout: str, slide_no: int, source_png: Path, before_png: Path,
          after_png: Path, before_score: float | None,
          after_score: float | None, brand_name: str) -> Image.Image:
    canvas = Image.new("RGB", (PAGE_W, PAGE_H), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((60, 36), f"{layout}", fill=(20, 20, 20), font=_font(46))
    draw.text((60, 86), f"slide {slide_no:02d}  ·  brand {brand_name}",
              fill=(120, 120, 120), font=_font(24))
    verdict_text, verdict_color = _verdict(before_score, after_score)
    bbox = draw.textbbox((0, 0), verdict_text, font=_font(28))
    draw.text((PAGE_W - 60 - (bbox[2] - bbox[0]), 56),
              verdict_text, fill=verdict_color, font=_font(28))

    panel_y = TOP_BAND + 30
    total_w = 3 * PANEL_W + 2 * GAP
    x0 = (PAGE_W - total_w) // 2
    _panel(canvas, source_png, x0, panel_y,
           "SOURCE", f"target — {Path(source_png).name}")
    _panel(canvas, before_png, x0 + PANEL_W + GAP, panel_y,
           "BEFORE  (iteration 0)", f"struct_diff_ratio  {_pct(before_score)}")
    _panel(canvas, after_png, x0 + 2 * (PANEL_W + GAP), panel_y,
           "AFTER  (final)", f"struct_diff_ratio  {_pct(after_score)}")
    return canvas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand-pack", required=True, type=Path,
                    help="Brand pack root (must contain verify-map.yaml)")
    ap.add_argument("--output-dir", type=Path,
                    help="Verify-loop output root (default: out/<brand>/verify-loop)")
    ap.add_argument("--pdf", type=Path,
                    help="Destination PDF (default: <output-dir>/before-after.pdf)")
    ap.add_argument("--only", nargs="*",
                    help="Restrict to a subset of layouts (by name)")
    args = ap.parse_args()

    brand_pack: Path = args.brand_pack.resolve()
    if not brand_pack.is_dir():
        sys.exit(f"brand pack not found: {brand_pack}")
    verify_map = brand_pack / "verify-map.yaml"
    if not verify_map.is_file():
        sys.exit(f"missing verify-map.yaml in {brand_pack}")
    brand_name = brand_pack.name
    out_root: Path = (args.output_dir or REPO / "out" / brand_name / "verify-loop").resolve()
    source_png_dir = out_root / "source-png"
    before_dir = out_root / "render-png.before"
    after_dir = out_root / "render-png"
    score_trace = out_root / "diff" / "score-trace.jsonl"
    if not before_dir.is_dir():
        sys.exit(f"missing baseline snapshot: {before_dir}\n"
                 f"Run `brand_verify_loop.py --snapshot-baseline` once before "
                 f"iterating so the before/after PDF has a reference point.")
    if not after_dir.is_dir():
        sys.exit(f"missing render-png/: {after_dir}\nRun the verify loop first.")
    pdf_path: Path = args.pdf or out_root / "before-after.pdf"

    mapping: dict[str, int] = yaml.safe_load(verify_map.read_text())["layouts"]
    if args.only:
        wanted = set(args.only)
        mapping = {k: v for k, v in mapping.items() if k in wanted}
        if not mapping:
            sys.exit("--only matched no layouts")

    first_scores, last_scores = _load_score_history(score_trace)

    pages: list[Image.Image] = []
    for layout, slide_no in mapping.items():
        src = source_png_dir / f"slide-{slide_no:02d}.png"
        bef = before_dir / f"{layout}.png"
        aft = after_dir / f"{layout}.png"
        page = _page(layout, slide_no, src, bef, aft,
                     first_scores.get(layout), last_scores.get(layout),
                     brand_name)
        pages.append(page)
        print(f"  · {layout}: before {_pct(first_scores.get(layout))} "
              f"→ after {_pct(last_scores.get(layout))}")

    if not pages:
        sys.exit("no pages produced (verify-map.yaml was empty?)")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(pdf_path, "PDF", save_all=True,
                  append_images=pages[1:], resolution=144.0)
    print(f"\nwrote {pdf_path}  ({len(pages)} page{'s' if len(pages) != 1 else ''})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
