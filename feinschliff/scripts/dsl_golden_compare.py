"""Golden-compare a v2 .slide.dsl render against a canonical .pptx baseline.

Pipeline:
  1. `feinschliff build` the .slide.dsl with the supplied content YAML.
  2. soffice-render both the v2 output and the canonical baseline to PNG.
  3. phash both, report distance + verdict against threshold (default 8).

Failed compares keep the rendered PNGs around in --out-dir for eyeballing.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import imagehash
from PIL import Image

from lib.io.soffice import pptx_to_png


REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dsl-golden-compare")
    ap.add_argument("layout", help="Path to .slide.dsl (under feinschliff/layouts/)")
    ap.add_argument("--brand", default="feinschliff", help="Brand id (default: feinschliff)")
    ap.add_argument("--content", required=True, help="YAML content fixture")
    ap.add_argument("--baseline", required=True, help="Canonical .pptx baseline")
    ap.add_argument("--threshold", type=int, default=8,
                    help="Max phash distance (0 = identical; 8 = perceivable diff)")
    ap.add_argument("--out-dir", default=None,
                    help="Where to keep renders (defaults to /tmp/golden-<layout>)")
    ap.add_argument("--keep", action="store_true",
                    help="Keep rendered PNGs even on pass")
    args = ap.parse_args(argv)

    layout = Path(args.layout).resolve()
    content = Path(args.content).resolve()
    baseline = Path(args.baseline).resolve()
    name = layout.stem.replace(".slide", "")
    out_dir = Path(args.out_dir) if args.out_dir else Path(tempfile.gettempdir()) / f"golden-{name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    v2_pptx = out_dir / f"{name}.v2.pptx"
    subprocess.run(
        ["uv", "run", "feinschliff", "build",
         str(layout), "--brand", args.brand,
         "--content", str(content), "-o", str(v2_pptx)],
        cwd=REPO_ROOT, check=True,
    )

    v2_png = pptx_to_png(v2_pptx, out_dir / "v2")
    if baseline.suffix.lower() == ".png":
        baseline_png = baseline
    else:
        baseline_png = pptx_to_png(baseline, out_dir / "baseline")
    shutil.copy(v2_png, out_dir / "v2.png")
    shutil.copy(baseline_png, out_dir / "baseline.png")

    h1 = imagehash.phash(Image.open(out_dir / "baseline.png"))
    h2 = imagehash.phash(Image.open(out_dir / "v2.png"))
    distance = h1 - h2
    verdict = "pass" if distance <= args.threshold else "fail"
    print(f"phash_distance={distance} threshold={args.threshold} verdict={verdict}")
    print(f"renders kept at: {out_dir}")

    if verdict == "pass" and not args.keep:
        # leave the PNGs for human eyeballing anyway; cheap to keep
        pass
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
