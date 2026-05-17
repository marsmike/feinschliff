"""`feinschliff decompile` — inverse of `build`: .pptx → per-slide .slide.dsl.

  feinschliff decompile <input.pptx> --brand <id> -o <output-dir>
                        [--assets-dir <path>]

Walks each slide in the input deck, emits one `slide-NN.slide.dsl` file
under `output-dir`. Each emitted DSL uses the brand's resolved color
tokens (reverse-mapped from hex) and style bundles (reverse-mapped from
font/size/weight/color tuples) where possible; falls back to inline
literal overrides when no token matches.

Picture shapes are extracted to `--assets-dir` (default:
`brands/<brand>/assets/`) under names like `source-slide-NN-K.<ext>`.

Day-one scope is *primitive* level: one DSL primitive per source shape.
Compound recognition (e.g. detecting 5 shapes as a `footer(…)` call)
and slot extraction (replacing literal strings with `{{ title }}`) are
out of scope for this command; run a separate pass over the emitted DSL.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from lib.dsl.pptx_decompile import decompile_pptx


REPO_ROOT = Path(__file__).resolve().parents[1]
BRANDS_DIR = REPO_ROOT / "brands"


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("pptx", help="Path to the input .pptx file")
    parser.add_argument("--brand", required=True,
                        help="Brand id (dir name under brands/) "
                             "— used to reverse-map colors and styles")
    parser.add_argument("-o", "--output-dir", required=True,
                        help="Directory to write per-slide .slide.dsl files")
    parser.add_argument("--assets-dir",
                        help="Directory to write extracted images "
                             "(default: brands/<brand>/assets/)")
    parser.add_argument("--brands-dir",
                        help="Where to resolve the brand's `extends:` parent "
                             "(default: brands/ in the toolkit repo). Use this "
                             "when the brand pack lives outside the toolkit tree.")
    parser.set_defaults(func=cmd_decompile)


def cmd_decompile(args) -> int:
    pptx_path = Path(args.pptx).resolve()
    if not pptx_path.is_file():
        print(f"error: {pptx_path} not found", flush=True)
        return 1
    brand_dir = (BRANDS_DIR / args.brand).resolve()
    if not brand_dir.is_dir():
        # Allow an absolute brand-pack path as a fallback for out-of-tree
        # brand packs (e.g. customer brands kept outside the repo).
        brand_dir = Path(args.brand).resolve()
        if not brand_dir.is_dir():
            print(f"error: brand pack not found at {brand_dir}", flush=True)
            return 1

    output_dir = Path(args.output_dir).resolve()
    assets_dir = Path(args.assets_dir).resolve() if args.assets_dir else None
    brands_dir = Path(args.brands_dir).resolve() if args.brands_dir else BRANDS_DIR

    count = decompile_pptx(pptx_path, brand_dir, output_dir, assets_dir,
                           brands_dir=brands_dir)
    print(f"decompiled {count} slide(s) from {pptx_path.name} → {output_dir}")
    return 0
