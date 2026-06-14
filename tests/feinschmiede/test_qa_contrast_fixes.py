"""Regression tests for QA-sweep contrast/palette fixes (feinbild real-world QA).

- chart-series-N resolve to distinct categorical colors (not all->accent).
- swatch_grid label color is overridable (`text:`) for dark backgrounds.
- zone/lane fills + labels adapt to `theme dark` (were hardcoded light).
"""

import json
from pathlib import Path

from feinschmiede.diagrams import excalidraw_expand, svg_expand
from feinschmiede.diagrams.brand_bridge import resolve

# Use the repo's brand pack explicitly — find_brand() would resolve to whatever
# feinschliff plugin copy is installed in ~/.claude/plugins (which shadows the
# repo and may lack these edits).
BRAND = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"


def test_chart_series_are_six_distinct_colors():
    colors = [resolve(f"chart-series-{i}", BRAND) for i in range(1, 7)]
    assert len({c.lower() for c in colors}) == 6, f"chart-series not distinct: {colors}"


def test_swatch_grid_label_color_override():
    dsl = "canvas 400x200\nswatch_grid sg 20,20 cols:2 swatches:primary,A;accent,B"
    base = svg_expand.expand(dsl + "\n", BRAND)
    over = svg_expand.expand(dsl + " text:paper\n", BRAND)
    paper = resolve("paper", BRAND)
    assert f'fill="{paper}"' in over
    assert f'fill="{paper}"' not in base  # default stays ink


def _exc(dsl: str) -> dict:
    return json.loads(excalidraw_expand.expand(dsl, BRAND))


def _kind(doc, kind):
    return [e for e in doc["elements"] if e.get("customData", {}).get("dsl_kind") == kind]


def test_dark_zone_fill_and_label_adapt():
    doc = _exc('canvas 800x400\ntheme dark\nzone z 40,40 700x300 "Area"\n')
    rect = _kind(doc, "zone")[0]
    assert rect["backgroundColor"] == resolve("tertiary", BRAND)
    assert rect["backgroundColor"] != resolve("surface-2", BRAND)
    assert _kind(doc, "zone-label")[0]["strokeColor"] == resolve("off-white", BRAND)


def test_dark_lane_fill_adapts():
    doc = _exc('canvas 800x400\ntheme dark\nlane l 40,40 700x300 "Lane"\n')
    assert _kind(doc, "lane")[0]["backgroundColor"] == resolve("tertiary", BRAND)


def test_light_theme_zone_lane_unchanged():
    z = _exc('canvas 800x400\nzone z 40,40 700x300 "Area"\n')
    assert _kind(z, "zone")[0]["backgroundColor"] == resolve("surface-2", BRAND)
    lane = _exc('canvas 800x400\nlane l 40,40 700x300 "Lane"\n')
    assert _kind(lane, "lane")[0]["backgroundColor"] == resolve("surface", BRAND)
