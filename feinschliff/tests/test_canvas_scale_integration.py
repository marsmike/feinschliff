"""Integration tests for canvas-scale plumbing across the diagram pipeline.

Covers the two bugs Codex flagged on the first Tier B push:
  1. SVG primitives emitted fixed font sizes regardless of canvas — text
     became unreadable at virtual 4× canvases.
  2. The wireframe parser hardcoded font_size=16 for Excalidraw box
     labels, so the validator applied the virtual-canvas downscale to
     unscaled metadata and false-failed `diagram-text-too-small`.

These tests intentionally exercise the *integrated* path (expander →
wireframe parser → validator) rather than mocking metadata, so a future
regression in any single layer surfaces here."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from feinschmiede.diagrams import svg_expand
from feinschmiede.diagrams.diagram_wireframe import (
    primitives_from_excalidraw_dsl,
    primitives_from_svg_dsl,
)
from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.expander import expand_diagram_blocks
from feinschliff.layout_validator import validate_diagrams_text_size


def _brand_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "brands" / "feinschliff"


@pytest.fixture(autouse=True)
def _stub_render(monkeypatch):
    """Bypass real rendering — these tests check pipeline plumbing, not pixels."""
    monkeypatch.setattr(
        "feinschmiede.diagrams.render.render",
        lambda src, out, **_kw: out.write_bytes(b"\x89PNG\r\n\x1a\n") or out,
    )


# ============================================================================
# SVG canvas scaling — Codex finding #1.
# ============================================================================

def _font_sizes(svg: str) -> list[int]:
    return [int(m) for m in re.findall(r'font-size="(\d+)"', svg)]


def test_svg_text_primitive_scales_with_large_canvas():
    """`text ... body` at 6880 canvas should render ≈4× the size of the
    same primitive at the 1720 baseline canvas."""
    narrow = svg_expand.expand(
        "canvas 1720x480\ntext t 100,100 body \"hello\"",
        brand_dir=_brand_dir(),
    )
    virtual = svg_expand.expand(
        "canvas 6880x2880\ntext t 100,100 body \"hello\"",
        brand_dir=_brand_dir(),
    )
    assert _font_sizes(narrow) == [14]
    assert _font_sizes(virtual) == [56]  # 14 * 4.0


def test_svg_label_box_scales_with_large_canvas():
    narrow = svg_expand.expand(
        "canvas 1720x480\nlabel_box lb 0,0 200x80 \"x\" variant:title",
        brand_dir=_brand_dir(),
    )
    virtual = svg_expand.expand(
        "canvas 6880x2880\nlabel_box lb 0,0 200x80 \"x\" variant:title",
        brand_dir=_brand_dir(),
    )
    # Title variant = 22px at baseline → 88 at 4× canvas.
    assert _font_sizes(narrow) == [22]
    assert _font_sizes(virtual) == [88]


def test_svg_callout_bubble_text_scales():
    narrow = svg_expand.expand(
        "canvas 1720x480\ncallout c anchor:300,300 at:500,500 200x80 \"note\"",
        brand_dir=_brand_dir(),
    )
    virtual = svg_expand.expand(
        "canvas 6880x2880\ncallout c anchor:300,300 at:500,500 200x80 \"note\"",
        brand_dir=_brand_dir(),
    )
    # Callout bubble text = 14px baseline → 56 at 4× canvas.
    assert 14 in _font_sizes(narrow)
    assert 56 in _font_sizes(virtual)


def test_svg_brace_label_scales():
    virtual = svg_expand.expand(
        'canvas 6880x2880\nbrace b from:100,100 to:100,400 side:right depth:30 "label"',
        brand_dir=_brand_dir(),
    )
    assert 52 in _font_sizes(virtual)  # 13 * 4.0


def test_svg_axis_labels_scale():
    virtual = svg_expand.expand(
        'canvas 6880x2880\naxis a horizontal 100,500 400 "A,B,C,D"',
        brand_dir=_brand_dir(),
    )
    assert 44 in _font_sizes(virtual)  # 11 * 4.0


def test_svg_swatch_grid_labels_scale():
    virtual = svg_expand.expand(
        'canvas 6880x2880\nswatch_grid g 100,100 cols:2 swatches:primary,one;secondary,two',
        brand_dir=_brand_dir(),
    )
    # 12 * 4.0 = 48 — but also the cell layout dimensions scale.
    assert 48 in _font_sizes(virtual)


def test_svg_canvas_below_baseline_does_not_scale():
    """Legacy small-canvas examples keep their existing behavior."""
    out = svg_expand.expand(
        "canvas 800x400\ntext t 100,100 body \"hello\"",
        brand_dir=_brand_dir(),
    )
    assert _font_sizes(out) == [14]


# ============================================================================
# Excalidraw validator integration — Codex finding #2.
# ============================================================================

def test_excalidraw_full_layout_default_box_label_passes_validator(tmp_path: Path):
    """The original bug: a full-slide Excalidraw diagram with a default
    box label was emitted with fontSize=64 (correctly scaled) but the
    wireframe parser produced metadata with font_size=16 (unscaled). The
    validator then applied the 4× downscale to 16 → 3.58pt → fatal
    `diagram-text-too-small`. After the wireframe-parser fix, metadata
    matches what the renderer emits and the validator is satisfied."""
    src = """
excalidraw d 100,300 1720x720 virtual:6880x2880 {
  box mcu 400,400 1500x500 "MCU"
}
"""
    nodes, _ = parse_lines(src)
    out = expand_diagram_blocks(
        nodes,
        brand_dir=_brand_dir(),
        out_dir=tmp_path,
        layout_dir=tmp_path,
        slide_index=1,
    )
    defects = validate_diagrams_text_size(
        out, slide_index=1, slide_w=1920, slide_h=1080,
    )
    assert defects == [], f"unexpected text-too-small defect on full-slide box: {defects}"


def test_excalidraw_narrow_layout_box_label_still_passes_validator(tmp_path: Path):
    """Legacy narrow path: no virtual viewport, baseline font, no scale.
    Validator should still pass — the 1× scale produces font_size=16,
    on-slide pt = 16 * (1720/1920) = 14.3 → above 12pt body min."""
    src = """
excalidraw d 100,360 1720x480 {
  box a 100,100 600x200 "Hello"
}
"""
    nodes, _ = parse_lines(src)
    out = expand_diagram_blocks(
        nodes, brand_dir=_brand_dir(),
        out_dir=tmp_path, layout_dir=tmp_path, slide_index=1,
    )
    defects = validate_diagrams_text_size(
        out, slide_index=1, slide_w=1920, slide_h=1080,
    )
    assert defects == [], f"legacy narrow path regressed: {defects}"


def test_wireframe_parser_scales_excalidraw_box_label():
    """Direct check: passing canvas_w into the parser scales font_size."""
    dsl = "box mcu 100,100 600x200 \"x\""
    narrow = primitives_from_excalidraw_dsl(dsl, _brand_dir(), canvas_w=1720)
    virtual = primitives_from_excalidraw_dsl(dsl, _brand_dir(), canvas_w=6880)
    narrow_label = next(p for p in narrow if p.kind == "text")
    virtual_label = next(p for p in virtual if p.kind == "text")
    assert narrow_label.font_size == 16.0
    assert virtual_label.font_size == 64.0  # 16 * (6880/1720) = 64


def test_wireframe_parser_scales_svg_text():
    dsl = "text t 100,100 body \"x\""
    narrow = primitives_from_svg_dsl(dsl, _brand_dir(), canvas_w=1720)
    virtual = primitives_from_svg_dsl(dsl, _brand_dir(), canvas_w=6880)
    narrow_text = next(p for p in narrow if p.kind == "text")
    virtual_text = next(p for p in virtual if p.kind == "text")
    assert narrow_text.font_size == 14.0
    assert virtual_text.font_size == 56.0  # 14 * 4
