#!/usr/bin/env python3
"""Extract source-slide regions as brand assets for verification.

Two extraction modes, both driven by `<brand-pack>/verify-map.yaml`:

  1. **Picture slots**: for each `picture X,Y WxH path:<expr>` primitive in
     a layout DSL, crop the matching source slide at the same design-px
     bbox (scaled to source PNG native resolution) and save the crop as
     `assets/source-<layout>-<idx>.png`.

  2. **Chart regions** (optional): for layouts in `chart_bboxes:`, crop a
     hand-specified region of the source slide and save as
     `assets/source-<layout>-chart.png`. Use this when a layout's "chart"
     is composed natively (rects, ovals, lines) but you want to verify
     against the source pixel content rather than the composition.

After extraction, wire each asset into the corresponding content YAML
field. Renders then match source pixel-for-pixel in those regions,
leaving only structural chrome to diff.

Usage:
  python scripts/brand_source_extract.py \
      --brand-pack brands/<brand> \
      --source-dir <source-png-dir>

`verify-map.yaml` schema:
  layouts:
    cover-orange: 5
    quote: 11
    …
  chart_bboxes:                          # optional
    quote: [75, 195, 1770, 410]          # [x, y, w, h] in 1920x1080
    timeline: [55, 165, 1810, 660]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from feinschliff_builder.verify.verify_map import load_verify_map

DESIGN_W, DESIGN_H = 1920, 1080

_PICTURE_RE = re.compile(
    r"^\s*picture\s+(\d+)\s*,\s*(\d+)\s+(\d+)\s*x\s*(\d+)\s+path:([^\s]+)",
    re.MULTILINE,
)


def _crop_to_design(src_im: Image.Image, x: int, y: int, w: int, h: int) -> Image.Image:
    sw, sh = src_im.size
    scale_x, scale_y = sw / DESIGN_W, sh / DESIGN_H
    sx0 = max(0, min(sw, int(round(x * scale_x))))
    sy0 = max(0, min(sh, int(round(y * scale_y))))
    sx1 = max(0, min(sw, int(round((x + w) * scale_x))))
    sy1 = max(0, min(sh, int(round((y + h) * scale_y))))
    return src_im.crop((sx0, sy0, sx1, sy1))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--brand-pack", type=Path, required=True)
    p.add_argument("--source-dir", type=Path, required=True,
                   help="Directory with slide-NN.png exports from source deck")
    args = p.parse_args()

    try:
        _vm = load_verify_map(args.brand_pack)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1
    except ValueError as exc:
        print(str(exc))
        return 1
    layouts_map = dict(_vm.layouts)
    chart_bboxes = dict(_vm.chart_bboxes)

    layouts_dir = args.brand_pack / "layouts"
    assets_dir = args.brand_pack / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'layout':<28}{'slide':<7}{'kind':<10}{'design bbox':<22}asset")
    print("-" * 90)

    for layout, slide_no in layouts_map.items():
        src_path = args.source_dir / f"slide-{slide_no:02d}.png"
        dsl_path = layouts_dir / f"{layout}.slide.dsl"
        if not src_path.is_file():
            continue
        src_im = Image.open(src_path).convert("RGB")

        # Picture-slot crops.
        if dsl_path.is_file():
            matches = _PICTURE_RE.findall(dsl_path.read_text())
            for idx, (x, y, w, h, _expr) in enumerate(matches, start=1):
                x, y, w, h = int(x), int(y), int(w), int(h)
                crop = _crop_to_design(src_im, x, y, w, h)
                asset = assets_dir / f"source-{layout}-{idx}.png"
                crop.save(asset, format="PNG", optimize=False)
                print(f"{layout:<28}{slide_no:<7}picture[{idx}]  "
                      f"({x},{y}) {w}x{h:<10}{asset.name}")

        # Chart-region crop (single per-layout).
        if layout in chart_bboxes:
            x, y, w, h = chart_bboxes[layout]
            crop = _crop_to_design(src_im, x, y, w, h)
            asset = assets_dir / f"source-{layout}-chart.png"
            crop.save(asset, format="PNG", optimize=False)
            print(f"{layout:<28}{slide_no:<7}{'chart':<10}"
                  f"({x},{y}) {w}x{h:<10}{asset.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
