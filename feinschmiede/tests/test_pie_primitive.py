"""Data-driven `pie` primitive for the SVG diagram DSL.

Wedge angles must scale to the slice VALUES (honest part-to-whole), not be
fixed geometry. One <path> wedge per slice, brand-resolved fills.
"""
import re

from feinschmiede.brand_discovery import find_brand
from feinschmiede.diagrams.svg_expand import expand

_BRAND = find_brand("feinschliff").root


def _wedges(dsl: str):
    svg = expand(dsl, _BRAND)
    return re.findall(r'<path d="([^"]*)"[^>]*?fill="([^"]*)"', svg)


def test_pie_emits_one_wedge_per_slice_with_resolved_fills():
    wedges = _wedges(
        "canvas 600x600\n"
        "pie p 300,300 r:200 slices:40,chart-series-1;35,chart-series-2;25,chart-series-3\n"
    )
    assert len(wedges) == 3
    for d, fill in wedges:
        assert fill.startswith("#"), f"fill not brand-resolved: {fill!r}"


def test_pie_wedge_arc_large_flag_scales_to_value():
    # 75% wedge spans 270deg (> 180 -> large-arc-flag 1); 25% spans 90deg (flag 0).
    wedges = _wedges(
        "canvas 600x600\npie p 300,300 r:200 slices:75,chart-series-1;25,chart-series-2\n"
    )
    assert len(wedges) == 2
    flags = []
    for d, _ in wedges:
        m = re.search(r"A [\d.]+,[\d.]+ 0 ([01]),1 ", d)
        assert m, f"wedge missing clockwise arc: {d!r}"
        flags.append(m.group(1))
    assert flags == ["1", "0"]


def test_pie_single_full_slice_renders_full_circle():
    # A lone 100% slice spans 360deg -> start point == end point, so an arc
    # path would be a degenerate zero-area shape. Must emit a full circle.
    svg = expand(
        "canvas 600x600\npie p 300,300 r:200 slices:100,chart-series-1\n", _BRAND
    )
    assert re.search(
        r'<circle cx="300" cy="300" r="200(\.0)?"[^>]*fill="#[0-9A-Fa-f]{6}"', svg
    ), f"100% pie should render a full circle, got: {svg!r}"

