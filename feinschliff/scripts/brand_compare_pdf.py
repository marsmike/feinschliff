#!/usr/bin/env python3
"""Build a side-by-side source-vs-render comparison PDF for a brand pack.

For each `<layout>: <source_slide_no>` mapping in the brand's
`verify-map.yaml`, lays the source slide (left) next to the rendered
layout (right) on one landscape-A4 page. Also writes a matching per-page
PNG to `<output-dir>/` so individual layouts can be opened by source
slide number.

Companion to `brand_visual_diff.py`: that one produces per-slide overlay
+ mask PNGs (with a red diff mask). This one is for clean visual review
without the diff highlight — useful for stakeholder walkthrough.

Usage:
  python scripts/brand_compare_pdf.py \
      --brand-pack brands/<brand> \
      --source-dir <source-png-dir> \
      --render-dir out/<brand>/png \
      --output-dir out/<brand>/compare

`verify-map.yaml` schema (same as brand_visual_diff): see
`skills/compile/references/verification-pipeline.md`.
"""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import img2pdf
import yaml
from PIL import Image, ImageDraw, ImageFont


# A4 landscape at 150 dpi.
PAGE_W, PAGE_H = 1754, 1240
MARGIN = 30
GUTTER = 30
HEADER_H = 70
FOOTER_H = 30
PANEL_W = (PAGE_W - 2 * MARGIN - GUTTER) // 2
PANEL_H = PAGE_H - HEADER_H - FOOTER_H - 2 * MARGIN


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_image(path: Path, box_w: int, box_h: int) -> Image.Image:
    im = Image.open(path).convert("RGB")
    scale = min(box_w / im.width, box_h / im.height)
    return im.resize((int(im.width * scale), int(im.height * scale)),
                     Image.LANCZOS)


def _build_page(layout: str, slide_no: int,
                src: Path, render: Path) -> Image.Image:
    page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    draw = ImageDraw.Draw(page)

    header_font = _load_font(28)
    sub_font = _load_font(18)
    label_font = _load_font(16)
    footer_font = _load_font(14)

    draw.text((MARGIN, MARGIN), layout, fill=(20, 20, 20), font=header_font)
    sub = f"Source: slide-{slide_no:02d}.png   ·   Render: {render.name}"
    draw.text((MARGIN, MARGIN + 36), sub, fill=(110, 110, 110), font=sub_font)

    panel_top = HEADER_H + MARGIN
    left_x = MARGIN
    right_x = MARGIN + PANEL_W + GUTTER

    if src.is_file():
        src_img = _fit_image(src, PANEL_W, PANEL_H - 30)
        sx = left_x + (PANEL_W - src_img.width) // 2
        sy = panel_top + 30 + (PANEL_H - 30 - src_img.height) // 2
        page.paste(src_img, (sx, sy))
    else:
        draw.text((left_x, panel_top + 100),
                  f"(source PNG not found: {src.name})",
                  fill=(180, 80, 80), font=label_font)
    draw.text((left_x, panel_top), "SOURCE",
              fill=(80, 80, 80), font=label_font)

    if render.is_file():
        rd_img = _fit_image(render, PANEL_W, PANEL_H - 30)
        rx = right_x + (PANEL_W - rd_img.width) // 2
        ry = panel_top + 30 + (PANEL_H - 30 - rd_img.height) // 2
        page.paste(rd_img, (rx, ry))
    else:
        draw.text((right_x, panel_top + 100),
                  f"(render PNG not found: {render.name})",
                  fill=(180, 80, 80), font=label_font)
    draw.text((right_x, panel_top), "RENDER",
              fill=(80, 80, 80), font=label_font)

    draw.text((MARGIN, PAGE_H - FOOTER_H),
              "Brand-pack visual review — feinschliff",
              fill=(160, 160, 160), font=footer_font)
    return page


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--brand-pack", type=Path, required=True)
    p.add_argument("--source-dir", type=Path, required=True,
                   help="Directory with slide-NN.png exports from source")
    p.add_argument("--render-dir", type=Path, required=True,
                   help="Directory with <layout>.png renders")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="Where to write compare.pdf + per-page PNGs")
    args = p.parse_args()

    map_path = args.brand_pack / "verify-map.yaml"
    if not map_path.is_file():
        print(f"missing {map_path}")
        return 1
    layouts_map = yaml.safe_load(map_path.read_text()).get("layouts", {})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = args.output_dir / "compare.pdf"

    page_paths: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for layout, slide_no in layouts_map.items():
            src = args.source_dir / f"slide-{slide_no:02d}.png"
            render = args.render_dir / f"{layout}.png"
            page = _build_page(layout, slide_no, src, render)
            # Save per-page PNG to the output dir for direct opening.
            page_png = args.output_dir / f"slide-{slide_no:02d}_{layout}.png"
            page.save(page_png, format="PNG", optimize=False)
            # And a copy in tmp for the PDF assembly (img2pdf reads files).
            tmp_page = tmp_path / f"page-{slide_no:02d}_{layout}.png"
            page.save(tmp_page, format="PNG", optimize=False)
            page_paths.append(str(tmp_page))

        if not page_paths:
            print("no pages built")
            return 1
        layout_fun = img2pdf.get_layout_fun(
            pagesize=(img2pdf.mm_to_pt(297), img2pdf.mm_to_pt(210))
        )
        with open(out_pdf, "wb") as f:
            f.write(img2pdf.convert(page_paths, layout_fun=layout_fun))
    print(f"wrote {out_pdf}  ({len(page_paths)} pages)")
    print(f"wrote {len(page_paths)} per-page PNGs to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
