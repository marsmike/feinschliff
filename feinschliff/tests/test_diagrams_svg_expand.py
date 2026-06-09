"""Tests for lib/diagrams/svg_expand.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschmiede.diagrams.svg_expand import expand


def _brand_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "brands" / "feinschliff"


def test_canvas_only_emits_valid_svg():
    dsl = "canvas 400x300"
    svg = expand(dsl, brand_dir=_brand_dir())
    assert svg.startswith("<?xml") or svg.startswith("<svg")
    assert 'viewBox="0 0 400 300"' in svg


def test_rect_primitive():
    dsl = """
canvas 400x300
rect bg 0,0 400x300 paper
"""
    svg = expand(dsl, brand_dir=_brand_dir())
    assert "<rect" in svg
    assert 'width="400"' in svg
    assert 'height="300"' in svg


def test_unknown_color_rejected():
    dsl = """
canvas 400x300
rect bg 0,0 400x300 royal-blue
"""
    with pytest.raises(Exception, match="unknown color"):
        expand(dsl, brand_dir=_brand_dir())


SAMPLE_DSL = """
canvas 600x400
rect bg 0,0 600x400 paper
text t1 300,30 title "Q1 Revenue"
axis x1 horizontal 80,350 480 "Q1,Q2,Q3,Q4"
bar b1 120,150 80x200 primary value:"$85k"
bar b2 220,200 80x150 secondary value:"$62k"
bar b3 320,100 80x250 success value:"$98k"
bar b4 420,250 80x100 tertiary value:"$41k"
legend lg 240,380 primary:"EMEA" secondary:"APAC" success:"AMER" tertiary:"LATAM"
"""


def test_rect_label_emits_centered_text():
    """`rect ... label:"text"` adds a centered <text> element on the shape."""
    dsl = """
canvas 400x300
rect bg 100,100 200x80 primary label:"Hero"
"""
    svg = expand(dsl, brand_dir=_brand_dir())
    assert "<rect" in svg
    assert ">Hero<" in svg
    assert "text-anchor=\"middle\"" in svg


def test_circle_label_emits_centered_text():
    dsl = """
canvas 400x300
circle node 200,150 40 accent label:"X"
"""
    svg = expand(dsl, brand_dir=_brand_dir())
    assert "<circle" in svg
    assert ">X<" in svg


def _locate_brand(name: str) -> Path:
    core = Path(__file__).resolve().parent.parent / "brands" / name
    if core.exists():
        return core
    extra = Path(__file__).resolve().parent.parent.parent / "feinschliff-extra" / "brands" / name
    return extra  # may not exist; caller should skip


@pytest.mark.parametrize("brand_name", [
    "feinschliff", "catppuccin-macchiato", "nord", "gruvbox-dark",
])
def test_chart_renders_across_brands(brand_name):
    brand_dir = _locate_brand(brand_name)
    if not brand_dir.exists():
        pytest.skip(f"brand {brand_name} not present")
    svg = expand(SAMPLE_DSL, brand_dir=brand_dir)
    assert "<svg" in svg
    assert svg.count("<rect") >= 5  # bg + 4 bars + 4 legend chips
    assert svg.count("<text") >= 9  # title + values + axis labels + legend labels
    assert "</svg>" in svg
