"""`feinschliff decompile` — inverse of `build`: .pptx → per-slide .slide.dsl.

  feinschliff decompile <input.pptx> --brand <id> -o <output-dir>
                        [--assets-dir <path>] [--with-svg]

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

## Backends

Two decompiler backends are available:

- **Default (`pptx_decompile`):** primitive-level reverse mapping. Fast,
  no external dependencies, lossy on chart geometry and custGeom shapes
  that inherit their xfrm from the layout.

- **Hybrid (`--with-svg`):** uses `pptx_svg_decompile` — combines PPTX
  XML (semantics) with optional SVG (geometry, rendered from each
  slide's PDF page via `pdf2svg`). Higher fidelity on charts and
  custGeom; requires `pdf2svg` binary if SVG cross-check is enabled
  (the current implementation reserves the SVG path but does not yet
  invoke it from the CLI — PPTX-only mode of the hybrid is the
  default behaviour of `--with-svg`).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from lib.dsl.pptx_decompile import decompile_pptx


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
    parser.add_argument("--with-svg", action="store_true",
                        help="Use the hybrid PPTX+SVG decompiler "
                             "(lib/dsl/pptx_svg_decompile) — higher fidelity on "
                             "charts and custGeom shapes. Emits one slide-NN.slide.dsl "
                             "per slide named by index. Asset extraction is not yet "
                             "supported in this mode (pictures land as placeholder slots).")
    parser.set_defaults(func=cmd_decompile)


def cmd_decompile(args) -> int:
    from lib.brand_discovery import find_brand
    pptx_path = Path(args.pptx).resolve()
    if not pptx_path.is_file():
        print(f"error: {pptx_path} not found", flush=True)
        return 1
    # Try discovery first; fall back to bare path (out-of-tree brand packs).
    try:
        brand_obj = find_brand(args.brand)
        brand_dir = brand_obj.root
    except ValueError:
        brand_dir = Path(args.brand).resolve()
        if not brand_dir.is_dir():
            print(f"error: brand pack not found: {args.brand!r}", flush=True)
            return 1
        brand_obj = None

    output_dir = Path(args.output_dir).resolve()
    assets_dir = Path(args.assets_dir).resolve() if args.assets_dir else None
    if args.brands_dir:
        brands_dir = Path(args.brands_dir).resolve()
    elif brand_obj is not None:
        brands_dir = brand_obj.root.parent
    else:
        brands_dir = brand_dir.parent

    if args.with_svg:
        return _decompile_with_svg(pptx_path, brand_dir, output_dir, args.brand)

    count = decompile_pptx(pptx_path, brand_dir, output_dir, assets_dir,
                           brands_dir=brands_dir)
    print(f"decompiled {count} slide(s) from {pptx_path.name} → {output_dir}")
    return 0


def _decompile_with_svg(pptx_path: Path, brand_dir: Path,
                        output_dir: Path, brand_name: str) -> int:
    """Hybrid backend — uses lib.dsl.pptx_svg_decompile.derive() per slide."""
    from lib.dsl.pptx_svg_decompile import derive
    from pptx import Presentation

    output_dir.mkdir(parents=True, exist_ok=True)
    tokens_path = brand_dir / "tokens.json"
    pres = Presentation(str(pptx_path))
    n = len(pres.slides)
    count = 0
    for i in range(1, n + 1):
        layout_name = f"slide-{i:02d}"
        dsl = derive(
            pptx_path,
            slide_idx=i,
            tokens_path=tokens_path if tokens_path.exists() else None,
            layout_name=layout_name,
            theme_name=brand_name,
        )
        target = output_dir / f"{layout_name}.slide.dsl"
        target.write_text(dsl, encoding="utf-8")
        count += 1
    print(f"decompiled {count} slide(s) from {pptx_path.name} → {output_dir} (hybrid mode)")
    return 0
