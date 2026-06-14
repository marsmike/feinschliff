"""Tests for the Tier B SVG DSL extensions: group/endgroup, polyline,
polygon, path (allowlisted), area, stacked_bar, brace, callout,
swatch_grid, label_box."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from feinschmiede.diagrams.svg_expand import expand


def _brand_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "feinschliff" / "brands" / "feinschliff"


def _wrap(body: str) -> str:
    return f"canvas 1920x1080\n{body}\n"


# ============================================================================
# Group
# ============================================================================

def test_group_emits_g_element():
    out = expand(_wrap('group g1 transform:translate(100,200)\nrect r 0,0 50x50 primary\nendgroup'),
                 brand_dir=_brand_dir())
    assert '<g id="g1"' in out
    assert 'transform="translate(100,200)"' in out
    assert "</g>" in out


def test_unclosed_group_raises():
    with pytest.raises(ValueError, match="unclosed group"):
        expand(_wrap("group g1\nrect r 0,0 50x50 primary"), brand_dir=_brand_dir())


def test_endgroup_without_open_raises():
    with pytest.raises(ValueError, match="endgroup"):
        expand(_wrap("endgroup"), brand_dir=_brand_dir())


def test_group_transform_rejects_unknown_function():
    with pytest.raises(ValueError, match="transform"):
        expand(_wrap("group g1 transform:skewX(5)\nendgroup"), brand_dir=_brand_dir())


# ============================================================================
# Polyline / polygon
# ============================================================================

def test_polyline_emits_points_list():
    out = expand(_wrap("polyline p 0,0 100,50 200,150 stroke:primary"), brand_dir=_brand_dir())
    assert "<polyline" in out
    # Float formatting is acceptable — the renderer accepts either.
    assert 'points="0.0,0.0 100.0,50.0 200.0,150.0"' in out


def test_polyline_dashed_sets_dasharray():
    out = expand(_wrap("polyline p 0,0 100,50 dashed"), brand_dir=_brand_dir())
    assert "stroke-dasharray" in out


def test_polygon_closed_default_fill():
    out = expand(_wrap("polygon pg 0,0 100,0 50,86"), brand_dir=_brand_dir())
    assert "<polygon" in out
    assert 'points="0.0,0.0 100.0,0.0 50.0,86.0"' in out


def test_polyline_too_few_points_raises():
    with pytest.raises(ValueError, match="points"):
        expand(_wrap("polyline p 0,0"), brand_dir=_brand_dir())


# ============================================================================
# Path allowlist
# ============================================================================

def test_path_with_valid_d_renders():
    out = expand(_wrap('path p "M 10,20 L 30,40 C 50,60 70,80 90,100 Z" stroke:primary'),
                 brand_dir=_brand_dir())
    assert "<path" in out
    assert "M 10,20" in out


def test_path_rejects_script_in_d():
    with pytest.raises(ValueError, match="path d"):
        expand(_wrap('path p "<script>alert(1)</script>" stroke:primary'),
               brand_dir=_brand_dir())


def test_path_rejects_unknown_letter():
    """`X` is not in the SVG path command set."""
    with pytest.raises(ValueError, match="path d"):
        expand(_wrap('path p "M 0,0 X 10,10"'), brand_dir=_brand_dir())


def test_path_rejects_style_attr_injection():
    with pytest.raises(ValueError, match="path d"):
        expand(_wrap('path p "M 0,0 L 10,10 style=evil"'), brand_dir=_brand_dir())


# ============================================================================
# Area
# ============================================================================

def test_area_closes_at_baseline():
    out = expand(_wrap("area a 0,100 100,50 200,80 baseline:200 fill:primary"),
                 brand_dir=_brand_dir())
    # Polygon should contain the baseline-close points (float formatting OK).
    assert "200.0,200.0" in out and "0.0,200.0" in out


def test_area_without_baseline_raises():
    with pytest.raises(ValueError, match="baseline"):
        expand(_wrap("area a 0,100 100,50 fill:primary"), brand_dir=_brand_dir())


# ============================================================================
# Stacked bar
# ============================================================================

def test_stacked_bar_vertical_sums_normalize():
    out = expand(_wrap("stacked_bar sb 100,100 200x400 orient:vertical segments:3,primary;1,secondary"),
                 brand_dir=_brand_dir())
    # Two rects emitted; combined heights = 400 (the bar height).
    rects = re.findall(r'<rect[^/]+height="([\d.]+)"', out)
    heights = [float(h) for h in rects]
    assert pytest.approx(sum(heights), rel=0.01) == 400.0


def test_stacked_bar_horizontal_orientation():
    out = expand(_wrap("stacked_bar sb 100,100 400x60 orient:horizontal segments:1,primary;1,secondary"),
                 brand_dir=_brand_dir())
    # Two rects with width=200 each (400 / 2 segments).
    widths = re.findall(r'<rect[^/]+width="([\d.]+)"', out)
    assert all(190 <= float(w) <= 210 for w in widths), widths


def test_stacked_bar_bad_orient_raises():
    with pytest.raises(ValueError, match="orient"):
        expand(_wrap("stacked_bar sb 0,0 100x100 orient:diagonal segments:1,primary"),
               brand_dir=_brand_dir())


# ============================================================================
# Brace
# ============================================================================

def test_brace_emits_path_with_curves():
    out = expand(_wrap('brace b from:100,100 to:100,400 side:right depth:30 "third-party"'),
                 brand_dir=_brand_dir())
    assert "<path" in out
    # The label text should be present somewhere.
    assert "third-party" in out


def test_brace_missing_required_attr_raises():
    with pytest.raises(ValueError, match="brace"):
        expand(_wrap('brace b from:100,100 to:100,400 depth:30 "label"'),
               brand_dir=_brand_dir())


# ============================================================================
# Callout
# ============================================================================

def test_callout_emits_bubble_and_tail():
    out = expand(_wrap('callout c anchor:300,300 at:500,500 200x80 "Note" fill:warning'),
                 brand_dir=_brand_dir())
    # Bubble = rect; tail = polygon.
    assert "<rect" in out and "<polygon" in out
    assert "Note" in out


def test_callout_tail_none_omits_polygon():
    """With `tail:none`, only the bubble rect should be emitted (no polygon tail)."""
    out = expand(_wrap('callout c anchor:300,300 at:500,500 200x80 "Note" tail:none'),
                 brand_dir=_brand_dir())
    assert "<rect" in out
    assert "<polygon" not in out


# ============================================================================
# Swatch grid
# ============================================================================

def test_swatch_grid_emits_one_rect_per_swatch():
    out = expand(_wrap('swatch_grid g 100,100 cols:2 swatches:primary,first;secondary,second;tertiary,third'),
                 brand_dir=_brand_dir())
    # 3 swatches → 3 rects.
    assert out.count("<rect") == 3
    for word in ("first", "second", "third"):
        assert word in out


# ============================================================================
# Label box
# ============================================================================

def test_label_box_emits_rect_and_centered_text():
    out = expand(_wrap('label_box lb 100,100 200x80 "Hello" variant:title fill:primary'),
                 brand_dir=_brand_dir())
    assert "<rect" in out and "<text" in out
    assert "Hello" in out


def test_label_box_variant_changes_font_size():
    out_title = expand(_wrap('label_box lb 0,0 200x80 "x" variant:title'),
                       brand_dir=_brand_dir())
    out_detail = expand(_wrap('label_box lb 0,0 200x80 "x" variant:detail'),
                        brand_dir=_brand_dir())
    title_size = int(re.search(r'font-size="(\d+)"[^>]*>x</text>', out_title).group(1))
    detail_size = int(re.search(r'font-size="(\d+)"[^>]*>x</text>', out_detail).group(1))
    assert title_size > detail_size


def test_unknown_attribute_raises():
    with pytest.raises(ValueError, match="unknown attribute"):
        expand(_wrap('label_box lb 0,0 200x80 "x" fill:primary unknown_attr:nope'),
               brand_dir=_brand_dir())
