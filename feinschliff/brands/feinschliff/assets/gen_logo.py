"""Rasterize logo.svg and logo-light.svg to high-resolution PNGs.

Usage (from repo root):
    uv run --directory feinschliff python brands/feinschliff/assets/gen_logo.py

Output:
    brands/feinschliff/assets/logo.png       600x80  (ink on paper — light theme)
    brands/feinschliff/assets/logo-light.png 600x80  (paper on dark — dark theme)

This is a one-shot author tool — not wired to CI. The output PNGs are committed
so every consumer gets the rasterized asset without needing cairosvg at runtime.
"""
from __future__ import annotations

from pathlib import Path

import cairosvg

ASSETS = Path(__file__).resolve().parent

# Output dimensions: 600×80 is high enough for any slide-size embedding;
# python-pptx scales the embedded raster down to the declared picture size.
OUT_W = 600
OUT_H = 80


def rasterize(src: Path, dst: Path) -> None:
    cairosvg.svg2png(
        url=str(src),
        write_to=str(dst),
        output_width=OUT_W,
        output_height=OUT_H,
    )
    print(f"wrote {dst}  ({OUT_W}x{OUT_H})")


def main() -> None:
    rasterize(ASSETS / "logo.svg", ASSETS / "logo.png")
    rasterize(ASSETS / "logo-light.svg", ASSETS / "logo-light.png")


if __name__ == "__main__":
    main()
