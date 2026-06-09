"""feinbild diagram subcommands — thin wrappers over the feinschmiede engine.

`expand` resolves brand colors (DSL string -> SVG/Excalidraw string); `render`
rasterizes an already-expanded .svg/.excalidraw to PNG (brand-agnostic). We call
the engine's public functions directly — never shell out, never import the
render backends (render keeps its lazy rough-first / playwright-fallback logic).
"""

from __future__ import annotations

import sys
from pathlib import Path

from feinschmiede.diagrams import excalidraw_expand, svg_expand
from feinschmiede.diagrams.brand_bridge import resolve_brand_dir, strip_brand_directive
from feinschmiede.diagrams.render import render as _render


def _expand(expander, src: Path, out: Path | None, brand: str | None, expanded_suffix: str, dsl_suffix: str) -> int:
    dsl, directive = strip_brand_directive(src.read_text())
    brand_dir = resolve_brand_dir(directive=directive, cli_flag=brand)
    out = out or src.with_name(src.name.replace(dsl_suffix, expanded_suffix))
    out.write_text(expander.expand(dsl, brand_dir))
    print(f"feinbild: wrote {out}", file=sys.stderr)
    return 0


def cmd_svg_expand(src: Path, out: Path | None = None, brand: str | None = None) -> int:
    return _expand(svg_expand, src, out, brand, ".svg", ".svg.dsl")


def cmd_excalidraw_expand(src: Path, out: Path | None = None, brand: str | None = None) -> int:
    return _expand(excalidraw_expand, src, out, brand, ".excalidraw", ".exc.dsl")


def cmd_render(src: Path, out: Path | None = None) -> int:
    out = out or src.with_suffix(".png")
    _render(src, out)
    print(f"feinbild: wrote {out}", file=sys.stderr)
    return 0
