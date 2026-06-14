"""Smoke test — every shipped `.slide.dsl` layout renders cleanly with the
`feinschliff` brand tokens and produces a non-empty `.pptx`.

This is the safety-net test: it catches grammar regressions, missing
compounds, token-resolution breaks, or emitter crashes for the entire
layout catalog in one shot.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from feinschliff.dsl.expander import (
    expand_compounds,
    interpolate_nodes,
    load_compounds_for_brand,
)
from feinschliff.dsl.parser import parse_file
from feinschliff.dsl.pptx_emit import build_presentation
from feinschmiede.dsl.tokens import load_tokens


REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
LAYOUT_DIR = REPO_ROOT / "layouts"
BRANDS_DIR = REPO_ROOT / "brands"
STD_COMPOUNDS = REPO_ROOT / "compounds"
EXAMPLES_V2 = REPO_ROOT / "examples" / "v2"

LAYOUTS = sorted(LAYOUT_DIR.glob("*.slide.dsl"))


# Minimal generic fixture: covers the most-common slots across the catalog.
# Per-layout YAMLs in examples/v2/ override these when available.
_FALLBACK_CTX: dict = {
    "logo":         "",
    "pgmeta":       "Smoke test",
    "tracker":      "Smoke test",
    "eyebrow":      "Smoke",
    "kicker":       "",
    "title":        "Title placeholder",
    "subtitle":     "Subtitle placeholder",
    "action_title": "Headline takeaway",
    "body":         "Body placeholder",
    "lede":         "Lede placeholder",
    "quote":        "A memorable line.",
    "attribution":  "Attribution",
    "source":       "Source · placeholder",
    "footer_left":  "Jan 2026 · Smoke",
    "footer_right": "Slide 1 / 1",
    # Many layouts iterate over these arrays; provide 8 empty entries so
    # `items[7]` lookups never miss.
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


def _ctx_for_layout(layout_path: Path) -> dict:
    """Return the fixture content for a given layout — its example YAML if
    present, otherwise the minimal fallback dict."""
    example = EXAMPLES_V2 / f"{layout_path.stem.removesuffix('.slide')}.yaml"
    if example.is_file():
        merged = dict(_FALLBACK_CTX)
        merged.update(yaml.safe_load(example.read_text()) or {})
        return merged
    return dict(_FALLBACK_CTX)


@pytest.mark.parametrize("dsl_path", LAYOUTS, ids=lambda p: p.stem.removesuffix(".slide"))
def test_layout_builds_pptx(dsl_path: Path, tmp_path: Path):
    """End-to-end: parse → load tokens + compounds → interpolate → expand →
    emit. Asserts the .pptx file is written, non-empty, and has one slide."""
    brand_dir = BRANDS_DIR / "feinschliff"
    tokens = load_tokens(brand_dir, brands_dir=BRANDS_DIR)
    compounds = load_compounds_for_brand(
        brand_dir, std_dir=STD_COMPOUNDS, brands_dir=BRANDS_DIR
    )
    layout_nodes, layout_compounds = parse_file(dsl_path)
    for cd in layout_compounds:
        compounds[cd.name] = cd

    ctx = _ctx_for_layout(dsl_path)
    interp = interpolate_nodes(layout_nodes, ctx)
    primitives, _diagnostics = expand_compounds(interp, compounds)

    prs = build_presentation(primitives, tokens, asset_root=brand_dir / "assets")
    out = tmp_path / f"{dsl_path.stem}.pptx"
    prs.save(str(out))

    assert out.is_file(), f"no .pptx written for {dsl_path.name}"
    assert out.stat().st_size > 1000, f"suspiciously small .pptx for {dsl_path.name}"
    assert len(prs.slides) == 1
