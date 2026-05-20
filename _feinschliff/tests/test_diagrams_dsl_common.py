"""Tests for `lib.diagrams._dsl_common` — coord parsing, canvas scale,
sizing helpers shared by both `excalidraw_expand` and `svg_expand`.

Before 2026-05-16 each expander had its own copy (svg_expand: `_parse_xy`,
`_parse_wh`, `_parse_canvas`, `_sz`; excalidraw_expand: inline list
comprehensions). The shared helpers normalize this. Tests pin the
contract so a future drift between expanders fails loudly here rather
than as a silent rendering bug.
"""
from __future__ import annotations

import pytest

from lib.diagrams._dsl_common import (
    Canvas,
    canvas_scale,
    parse_canvas,
    parse_wh,
    parse_xy,
    scaled_int,
)


# ─── canvas_scale ─────────────────────────────────────────────────────────


def test_canvas_scale_under_baseline_returns_one():
    """Legacy small canvases (800-, 1280-, 1920-wide) all get scale=1.0."""
    assert canvas_scale(800) == 1.0
    assert canvas_scale(1280) == 1.0
    assert canvas_scale(1720) == 1.0


def test_canvas_scale_full_bleed_doubles():
    """The 6880-wide full-bleed diagram canvas scales 4× into the 1720 slot."""
    assert canvas_scale(6880) == pytest.approx(4.0)


def test_canvas_scale_none_returns_one():
    assert canvas_scale(None) == 1.0
    assert canvas_scale(0) == 1.0


# ─── parse_xy / parse_wh ─────────────────────────────────────────────────


def test_parse_xy_ints():
    assert parse_xy("100,200") == (100, 200)


def test_parse_xy_floats_truncate():
    assert parse_xy("100.7,200.4") == (100, 200)


def test_parse_xy_negative():
    assert parse_xy("-10,-20") == (-10, -20)


def test_parse_wh_basic():
    assert parse_wh("400x300") == (400, 300)


def test_parse_wh_floats():
    assert parse_wh("400.5x300.5") == (400, 300)


# ─── parse_canvas ────────────────────────────────────────────────────────


def test_parse_canvas_basic():
    assert parse_canvas("canvas 1920x1080") == Canvas(w=1920, h=1080)


def test_parse_canvas_extra_whitespace():
    assert parse_canvas("canvas   6880x2880") == Canvas(w=6880, h=2880)


def test_parse_canvas_bad_line_raises():
    with pytest.raises(ValueError, match="bad canvas line"):
        parse_canvas("canvas not-a-size")


# ─── scaled_int ──────────────────────────────────────────────────────────


def test_scaled_int_basic():
    assert scaled_int(16, 4.0) == 64
    assert scaled_int(16, 1.0) == 16


def test_scaled_int_rounds():
    assert scaled_int(13.4, 1.0) == 13
    assert scaled_int(13.5, 1.0) == 14


def test_scaled_int_floor_is_one():
    """Even very small bases / scales floor to 1 so primitives never disappear."""
    assert scaled_int(0.1, 0.1) == 1
    assert scaled_int(0, 5) == 1
