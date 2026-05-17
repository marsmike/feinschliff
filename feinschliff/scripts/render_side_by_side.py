"""Render two PPTXs at a given slide index, composite them horizontally."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from PIL import Image

from lib.soffice import pptx_to_png


def main() -> int:
    ap = argparse.ArgumentParser(prog="render_side_by_side")
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    ap.add_argument("--before-slide", type=int, required=True)
    ap.add_argument("--after-slide", type=int, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--gap", type=int, default=20)
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        before_png = pptx_to_png(args.before, tmp_dir,
                                 slide_index=args.before_slide, prefix=args.before.stem)
        after_png = pptx_to_png(args.after, tmp_dir,
                                slide_index=args.after_slide, prefix=args.after.stem)
        b = Image.open(before_png)
        a = Image.open(after_png)
        target_h = max(b.height, a.height)
        if b.height != target_h:
            b = b.resize((int(b.width * target_h / b.height), target_h))
        if a.height != target_h:
            a = a.resize((int(a.width * target_h / a.height), target_h))
        composite = Image.new("RGB", (b.width + args.gap + a.width, target_h), "white")
        composite.paste(b, (0, 0))
        composite.paste(a, (b.width + args.gap, 0))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        composite.save(args.output)
        print(f"wrote {args.output} ({composite.width}x{composite.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
