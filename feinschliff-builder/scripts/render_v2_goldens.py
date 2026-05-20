"""Render every shipped v2 `.slide.dsl` to a golden PNG.

Replaces the v1-era PNGs under `tests/golden/feinschliff/` with the
output of the current v2 emitter for each layout. Uses
`tests/fixtures/layouts/<layout>.yaml` content when present; otherwise the minimal
fallback dict from `tests/test_dsl_smoke.py` (kept in sync via duplication).

    uv run python scripts/render_v2_goldens.py --out-dir tests/golden/feinschliff

This is a one-shot baseline-refresh tool. No pytest test currently gates
against these PNGs — they exist as fidelity references for
`scripts/dsl_golden_compare.py`.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from lib.io.soffice import pptx_to_png
from lib.dsl.expander import (
    expand_compounds,
    expand_diagram_blocks,
    interpolate_nodes,
    load_compounds_for_brand,
)
from lib.dsl.parser import parse_file
from lib.dsl.pptx_emit import build_presentation
from lib.dsl.tokens import load_tokens


REPO_ROOT = Path(__file__).resolve().parents[1]


_FALLBACK_CTX: dict = {
    "logo":         "",
    "pgmeta":       "Golden",
    "tracker":      "Golden",
    "eyebrow":      "Golden",
    "kicker":       "",
    "title":        "Title placeholder",
    "subtitle":     "Subtitle placeholder",
    "action_title": "Headline takeaway",
    "body":         "Body placeholder",
    "lede":         "Lede placeholder",
    "quote":        "A memorable line.",
    "attribution":  "Attribution",
    "source":       "Source · placeholder",
    "footer_left":  "Jan 2026 · Golden",
    "footer_right": "Slide 1 / 1",
    "items":   [{"counter": "", "title": "", "description": ""}] * 8,
    "kpis":    [{"value": "", "unit": "", "key": "", "delta": ""}] * 8,
    "cards":   [{"counter": "", "heading": "", "body": ""}] * 8,
    "cells":   [{"tag": "", "heading": "", "body": "", "focus": False}] * 8,
    "columns": [{"counter": "", "heading": "", "body": ""}] * 8,
    "rows":    [{"label": "", "cells": ["", "", "", "", "", "", "", ""]}] * 8,
    "bars":    [{"label": "", "value": "", "width": 0, "kind": "up"}] * 8,
    "series":  [{"name": "", "points": [0, 0, 0, 0, 0]}] * 4,
    "periods": ["", "", "", "", ""],
}


def _ctx_for_layout(layout_path: Path, examples_dir: Path) -> dict:
    example = examples_dir / f"{layout_path.stem.removesuffix('.slide')}.yaml"
    if example.is_file():
        merged = dict(_FALLBACK_CTX)
        merged.update(yaml.safe_load(example.read_text()) or {})
        return merged
    return dict(_FALLBACK_CTX)


def main() -> int:
    ap = argparse.ArgumentParser(prog="render_v2_goldens")
    ap.add_argument("--out-dir", required=True, type=Path,
                    help="Output directory for the new golden PNGs")
    ap.add_argument("--brand", default="feinschliff")
    ap.add_argument("--clean", action="store_true",
                    help="Remove existing PNGs in out-dir first")
    args = ap.parse_args()

    out_dir: Path = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.clean:
        for p in out_dir.glob("*.png"):
            p.unlink()

    brand_dir = REPO_ROOT / "brands" / args.brand
    layouts_dir = REPO_ROOT / "layouts"
    examples_dir = REPO_ROOT / "tests" / "fixtures" / "layouts"
    std_compounds = REPO_ROOT / "compounds"
    brands_dir = REPO_ROOT / "brands"

    tokens = load_tokens(brand_dir, brands_dir=brands_dir)
    compounds = load_compounds_for_brand(
        brand_dir, std_dir=std_compounds, brands_dir=brands_dir
    )

    layouts = sorted(layouts_dir.glob("*.slide.dsl"))
    if not layouts:
        print("render_v2_goldens: no layouts found", file=sys.stderr)
        return 2

    for i, layout in enumerate(layouts, 1):
        name = layout.stem.removesuffix(".slide")
        try:
            layout_nodes, layout_compounds = parse_file(layout)
            local_compounds = dict(compounds)
            for cd in layout_compounds:
                local_compounds[cd.name] = cd
            ctx = _ctx_for_layout(layout, examples_dir)
            interp = interpolate_nodes(layout_nodes, ctx)

            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                diagrams_out = tmp_dir / "diagrams"
                diagrams_out.mkdir(exist_ok=True)
                interp = expand_diagram_blocks(
                    interp,
                    brand_dir=brand_dir,
                    out_dir=diagrams_out,
                    layout_dir=layout.parent,
                )
                primitives, _ = expand_compounds(interp, local_compounds)
                prs = build_presentation(primitives, tokens, asset_root=brand_dir / "assets")

                pptx_path = tmp_dir / f"{name}.pptx"
                prs.save(str(pptx_path))
                png = pptx_to_png(pptx_path, tmp_dir)
                target = out_dir / f"{name}.png"
                shutil.copy(png, target)
            print(f"  {i:>2}/{len(layouts)}  {name}  →  {target.name}")
        except Exception as exc:
            print(f"  {i:>2}/{len(layouts)}  {name}  FAILED: {exc}", file=sys.stderr)

    print(f"render_v2_goldens: wrote PNGs to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
