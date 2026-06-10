"""Data-driven chart primitives: bar heights and gantt bar positions scale
to the underlying values (honest geometry, not fixed)."""
import re

from feinschmiede.brand_discovery import find_brand
from feinschmiede.diagrams.svg_expand import expand

_BRAND = find_brand("feinschliff").root


def _rects(svg: str):
    return re.findall(
        r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg
    )


# --- barchart: bar heights scale to values --------------------------------

def test_barchart_bar_heights_scale_to_values():
    svg = expand(
        "canvas 600x400\n"
        "barchart c 50,50 500x300 bars:100,chart-series-1;50,chart-series-2 max:100\n",
        _BRAND,
    )
    rects = _rects(svg)
    assert len(rects) == 2
    heights = [float(r[3]) for r in rects]
    # value 100 -> full 300px; value 50 -> 150px (2:1)
    assert abs(heights[0] - 300.0) < 1.0, heights
    assert abs(heights[1] - 150.0) < 1.0, heights


def test_barchart_bars_sit_on_baseline():
    # bars grow UP from the chart's bottom edge (y + h = 350).
    svg = expand(
        "canvas 600x400\nbarchart c 50,50 500x300 bars:100,chart-series-1 max:100\n",
        _BRAND,
    )
    x, y, w, h = _rects(svg)[0]
    assert abs((float(y) + float(h)) - 350.0) < 1.0  # bottom edge == 50+300


# --- gantt: bar x/width scale to time span --------------------------------

def test_gantt_bar_position_scales_to_time_span():
    # span 2020..2030 over 500px; a bar 2020->2025 starts at x and is half-width.
    svg = expand(
        "canvas 700x400\n"
        "gantt g 100,80 500x200 span:2020,2030 bars:0,2020,2025,chart-series-1\n",
        _BRAND,
    )
    rects = _rects(svg)
    assert len(rects) == 1
    x, y, w, h = (float(v) for v in rects[0])
    assert abs(x - 100.0) < 1.0, x        # starts at chart left (2020 == span lo)
    assert abs(w - 250.0) < 1.0, w        # 5/10 of 500px span
