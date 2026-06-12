"""Tests for the Tier B Excalidraw DSL extensions: arrow flags, endpoint
ports, zone/lane primitives, canvas scaling."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from feinschmiede.diagrams.excalidraw_expand import expand


def _brand_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"


def _arrow(elements):
    return next(e for e in elements if e["type"] == "arrow")


def _absolute_waypoints(arrow):
    x, y = arrow["x"], arrow["y"]
    return [(x + px, y + py) for px, py in arrow["points"]]


# ============================================================================
# Arrow flags
# ============================================================================

def test_arrow_via_inserts_manual_waypoints():
    dsl = """
canvas 1200x600
box a 100,100 100x60 "A"
box b 900,500 100x60 "B"
arrow a -> b via:500,200;500,400
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_arrow(j["elements"]))
    # src/dst + 2 manual waypoints = 4 points total
    assert len(pts) == 4, pts
    # The two middle points are the manual waypoints (verbatim).
    assert pts[1] == (500.0, 200.0)
    assert pts[2] == (500.0, 400.0)


def test_arrow_route_elbow_inserts_one_perpendicular_bend():
    dsl = """
canvas 1200x600
box a 100,100 100x60 "A"
box b 900,400 100x60 "B"
arrow a -> b route:elbow
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_arrow(j["elements"]))
    assert len(pts) == 3, f"elbow should insert one bend, got {len(pts)} points: {pts}"


def test_arrow_style_dashed_sets_stroke_style():
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b style:dashed
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    arrow = _arrow(j["elements"])
    assert arrow["strokeStyle"] == "dashed"


def test_arrow_color_sets_stroke_color():
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b color:danger
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    arrow = _arrow(j["elements"])
    # `danger` resolves via brand_bridge; just verify it's not the default ink.
    ink = json.loads(expand("canvas 100x100\nbox a 0,0 10x10 \"x\"\n", brand_dir=_brand_dir()))
    ink_color = ink["elements"][0]["strokeColor"]
    assert arrow["strokeColor"] != ink_color


def test_arrow_weight_scales_stroke_width():
    """Use a large canvas so the scale multiplier separates the three
    weight tiers (at scale=1.0, the integer rounding can collapse 2.5
    and 2.0 to the same strokeWidth=2)."""
    dsl_pri = """
canvas 6880x2880
box a 400,400 400x240 "A"
box b 1600,400 400x240 "B"
arrow a -> b weight:primary
"""
    dsl_mut = """
canvas 6880x2880
box a 400,400 400x240 "A"
box b 1600,400 400x240 "B"
arrow a -> b weight:muted
"""
    arrow_pri = _arrow(json.loads(expand(dsl_pri, brand_dir=_brand_dir()))["elements"])
    arrow_mut = _arrow(json.loads(expand(dsl_mut, brand_dir=_brand_dir()))["elements"])
    assert arrow_pri["strokeWidth"] > arrow_mut["strokeWidth"]


def test_arrow_labelpos_above_offsets_label_negative():
    dsl_mid = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b label:"calls" labelpos:mid
"""
    dsl_above = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b label:"calls" labelpos:above
"""
    label_mid = next(e for e in json.loads(expand(dsl_mid, _brand_dir()))["elements"]
                     if e["type"] == "text" and e.get("text") == "calls")
    label_above = next(e for e in json.loads(expand(dsl_above, _brand_dir()))["elements"]
                       if e["type"] == "text" and e.get("text") == "calls")
    assert label_above["y"] < label_mid["y"], (
        f"labelpos:above should sit higher: above={label_above['y']} mid={label_mid['y']}"
    )


def test_arrow_unknown_flag_raises():
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b style:wobbly
"""
    with pytest.raises(ValueError, match="style"):
        expand(dsl, brand_dir=_brand_dir())


# ============================================================================
# Z-order: arrow strokes behind boxes, arrow labels on top.
# ============================================================================

def test_arrow_stroke_renders_before_boxes_in_zorder():
    """Arrow strokes must appear earlier in the elements array than the
    boxes they connect — Excalidraw renders earlier elements behind
    later ones, so this puts the stroke visually behind the boxes."""
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b
"""
    elements = json.loads(expand(dsl, _brand_dir()))["elements"]
    arrow_idx = next(i for i, e in enumerate(elements) if e["type"] == "arrow")
    box_indices = [i for i, e in enumerate(elements)
                   if e["type"] == "rectangle"]
    assert arrow_idx < min(box_indices), (
        f"arrow({arrow_idx}) must render before boxes({box_indices}) so it sits behind them"
    )


def test_arrow_label_renders_on_top_of_boxes():
    """Even though the arrow stroke goes behind boxes, the label text
    must still render on top so it stays readable."""
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b label:"calls"
"""
    elements = json.loads(expand(dsl, _brand_dir()))["elements"]
    label_idx = next(i for i, e in enumerate(elements)
                     if e["type"] == "text" and e.get("text") == "calls")
    last_box_idx = max(i for i, e in enumerate(elements) if e["type"] == "rectangle")
    assert label_idx > last_box_idx, (
        f"arrow label({label_idx}) must render after all boxes({last_box_idx})"
    )


# ============================================================================
# Auto-dotted: arrows that cross a non-endpoint box switch to dotted.
# ============================================================================

def test_arrow_crossing_third_box_auto_dotted():
    """Arrow from a → c whose straight path slices through b should become
    dotted automatically, signaling 'this line passes through the box(es)
    layered above it'."""
    dsl = """
canvas 1200x400
box a 100,150 100x100 "A"
box b 500,150 100x100 "B"
box c 900,150 100x100 "C"
arrow a -> c
"""
    arrow = _arrow(json.loads(expand(dsl, _brand_dir()))["elements"])
    assert arrow["strokeStyle"] == "dotted", (
        f"crossing arrow should auto-dot, got strokeStyle={arrow['strokeStyle']}"
    )


def test_arrow_not_crossing_stays_solid():
    """Arrow that cleanly connects two adjacent boxes (no third box in
    its path) keeps the default solid stroke."""
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b
"""
    arrow = _arrow(json.loads(expand(dsl, _brand_dir()))["elements"])
    assert arrow["strokeStyle"] == "solid"


def test_arrow_explicit_style_wins_over_crossing_autodot():
    """User-specified `style:dashed` must NOT be overridden to dotted by
    the crossing detector — explicit author intent always wins."""
    dsl = """
canvas 1200x400
box a 100,150 100x100 "A"
box b 500,150 100x100 "B"
box c 900,150 100x100 "C"
arrow a -> c style:dashed
"""
    arrow = _arrow(json.loads(expand(dsl, _brand_dir()))["elements"])
    assert arrow["strokeStyle"] == "dashed"


# ============================================================================
# Label placement: never directly on the arrow line.
# ============================================================================

def test_arrow_label_default_offsets_above_horizontal_arrow():
    """Default labelpos (`mid`) on a horizontal arrow puts the label
    fully above the arrow line, never overlapping it."""
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b label:"calls"
"""
    elements = json.loads(expand(dsl, _brand_dir()))["elements"]
    label = next(e for e in elements if e["type"] == "text" and e.get("text") == "calls")
    arrow = _arrow(elements)
    pts = _absolute_waypoints(arrow)
    arrow_y = pts[0][1]  # horizontal arrow → constant y
    label_bottom = label["y"] + label["height"]
    assert label_bottom < arrow_y, (
        f"label bottom ({label_bottom}) must sit above arrow line ({arrow_y})"
    )


def test_arrow_label_default_offsets_right_of_vertical_arrow():
    """Default labelpos on a vertical arrow places the label to the
    right of the arrow line — `above`/`below` would overlap it."""
    dsl = """
canvas 800x600
box a 200,100 100x60 "A"
box b 200,400 100x60 "B"
arrow a -> b label:"down"
"""
    elements = json.loads(expand(dsl, _brand_dir()))["elements"]
    label = next(e for e in elements if e["type"] == "text" and e.get("text") == "down")
    arrow = _arrow(elements)
    pts = _absolute_waypoints(arrow)
    arrow_x = pts[0][0]  # vertical arrow → constant x
    assert label["x"] > arrow_x, (
        f"label x ({label['x']}) must sit right of vertical arrow ({arrow_x})"
    )


def test_arrow_labelpos_left_offsets_label_left_of_midpoint():
    dsl = """
canvas 800x600
box a 200,100 100x60 "A"
box b 200,400 100x60 "B"
arrow a -> b label:"x" labelpos:left
"""
    elements = json.loads(expand(dsl, _brand_dir()))["elements"]
    label = next(e for e in elements if e["type"] == "text" and e.get("text") == "x")
    arrow = _arrow(elements)
    arrow_x = _absolute_waypoints(arrow)[0][0]
    assert label["x"] + label["width"] < arrow_x


def test_arrow_labelpos_right_offsets_label_right_of_midpoint():
    dsl = """
canvas 800x600
box a 200,100 100x60 "A"
box b 200,400 100x60 "B"
arrow a -> b label:"x" labelpos:right
"""
    elements = json.loads(expand(dsl, _brand_dir()))["elements"]
    label = next(e for e in elements if e["type"] == "text" and e.get("text") == "x")
    arrow = _arrow(elements)
    arrow_x = _absolute_waypoints(arrow)[0][0]
    assert label["x"] > arrow_x


def test_arrow_label_avoids_landing_inside_crossed_box():
    """A → C with B between them: label must NOT sit inside box B (which
    would overlap B's own label). It should anchor to the clear stretch
    on either side of B instead."""
    dsl = """
canvas 1200x400
box a 80,150 160x100 "A"
box b 520,150 160x100 "B"
box c 960,150 160x100 "C"
arrow a -> c label:"X"
"""
    elements = json.loads(expand(dsl, _brand_dir()))["elements"]
    label = next(e for e in elements if e["type"] == "text" and e.get("text") == "X")
    label_cx = label["x"] + label["width"] / 2
    label_cy = label["y"] + label["height"] / 2
    # B occupies x∈[520, 680], y∈[150, 250]. The label center must not
    # fall inside it.
    assert not (520 <= label_cx <= 680 and 150 <= label_cy <= 250), (
        f"label center ({label_cx}, {label_cy}) sits inside box B"
    )


# ============================================================================
# Endpoint ports
# ============================================================================

def test_arrow_port_right_anchors_at_right_edge():
    dsl = """
canvas 1200x600
box a 100,100 100x60 "A"
box b 900,400 100x60 "B"
arrow a:right -> b:left
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_arrow(j["elements"]))
    # a:right → src anchor at (200, 130). b:left → dst anchor at (900, 430).
    assert pts[0] == (200.0, 130.0), pts
    assert pts[-1] == (900.0, 430.0), pts


def test_arrow_port_top_anchors_at_top_edge():
    dsl = """
canvas 800x800
box a 300,400 100x60 "A"
box b 300,100 100x60 "B"
arrow a:top -> b:bottom
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_arrow(j["elements"]))
    assert pts[0] == (350.0, 400.0), pts   # a top center
    assert pts[-1] == (350.0, 160.0), pts  # b bottom center


def test_arrow_invalid_port_raises():
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a:diagonal -> b:left
"""
    with pytest.raises(ValueError, match="port"):
        expand(dsl, brand_dir=_brand_dir())


def test_arrow_port_combined_with_via():
    dsl = """
canvas 1200x800
box a 100,100 100x60 "A"
box b 900,500 100x60 "B"
arrow a:right -> b:top via:500,300
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_arrow(j["elements"]))
    assert pts[0] == (200.0, 130.0), pts        # port anchor
    assert pts[1] == (500.0, 300.0)             # manual waypoint
    assert pts[-1] == (950.0, 500.0), pts       # b top center


# ============================================================================
# Zone + lane primitives
# ============================================================================

def test_zone_emits_rect_plus_label():
    dsl = """
canvas 2000x1000
zone z1 100,100 1800x800 "Linux Domain" fill:surface-2
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    rects = [e for e in j["elements"] if e["type"] == "rectangle"]
    labels = [e for e in j["elements"] if e["type"] == "text" and e.get("text") == "Linux Domain"]
    assert len(rects) == 1
    assert len(labels) == 1
    # Zone rect carries dsl_kind marker for downstream tooling.
    assert rects[0]["customData"]["dsl_kind"] == "zone"


def test_zone_renders_behind_subsequent_shapes():
    """Zones declared after a box should still render *before* the box in
    element order — they're a background layer."""
    dsl = """
canvas 2000x1000
box b1 200,200 400x200 "Inside"
zone z1 100,100 1800x800 "Zone"
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    types_in_order = [e.get("customData", {}).get("dsl_kind") for e in j["elements"]]
    # zone should appear before any box element
    zone_idx = types_in_order.index("zone")
    # First box element (no dsl_kind set explicitly, but customData has dsl_id)
    box_idx = next(i for i, e in enumerate(j["elements"])
                   if e["type"] == "rectangle" and e.get("customData", {}).get("dsl_id") == "b1")
    assert zone_idx < box_idx, f"zone({zone_idx}) must render before box({box_idx})"


def test_lane_horizontal_label_at_left_edge():
    dsl = """
canvas 6000x800
lane runtime 100,100 5800x600 "Runtime" orient:horizontal
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    label = next(e for e in j["elements"] if e["type"] == "text" and e.get("text") == "Runtime")
    # Horizontal lane: label sits at left, vertically centered.
    assert label["x"] < 200, label
    assert 300 < label["y"] < 500, label


def test_lane_vertical_label_at_top_edge():
    dsl = """
canvas 800x6000
lane irq 100,100 600x5800 "IRQ path" orient:vertical
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    label = next(e for e in j["elements"] if e["type"] == "text" and e.get("text") == "IRQ path")
    # Vertical lane: label sits at top, slightly inset from left.
    assert label["y"] < 300, label


# ============================================================================
# Canvas scaling — large canvas → larger default sizes for legibility.
# ============================================================================

def test_box_label_font_scales_with_large_canvas():
    """Body authored in 6880x2880 should produce label fonts ~4× the
    1920-canvas default so they survive PowerPoint's downscale."""
    dsl_narrow = """
canvas 1720x480
box a 100,100 400x100 "Label"
"""
    dsl_virtual = """
canvas 6880x2880
box a 400,400 1600x400 "Label"
"""
    text_narrow = next(e for e in json.loads(expand(dsl_narrow, _brand_dir()))["elements"]
                       if e["type"] == "text")
    text_virtual = next(e for e in json.loads(expand(dsl_virtual, _brand_dir()))["elements"]
                        if e["type"] == "text")
    assert text_virtual["fontSize"] > text_narrow["fontSize"] * 2, (
        f"virtual canvas should scale font: narrow={text_narrow['fontSize']} virtual={text_virtual['fontSize']}"
    )


def test_arrow_label_font_scales_with_large_canvas():
    dsl_narrow = """
canvas 1720x480
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b label:"x"
"""
    dsl_virtual = """
canvas 6880x2880
box a 400,400 400x240 "A"
box b 1600,400 400x240 "B"
arrow a -> b label:"x"
"""
    label_narrow = next(e for e in json.loads(expand(dsl_narrow, _brand_dir()))["elements"]
                        if e["type"] == "text" and e.get("text") == "x")
    label_virtual = next(e for e in json.loads(expand(dsl_virtual, _brand_dir()))["elements"]
                         if e["type"] == "text" and e.get("text") == "x")
    assert label_virtual["fontSize"] > label_narrow["fontSize"] * 2


def test_canvas_below_1920_does_not_scale():
    """Legacy bit-for-bit behavior: canvas 800 → no scaling."""
    dsl = """
canvas 800x600
box a 100,100 200x80 "X"
"""
    text = next(e for e in json.loads(expand(dsl, _brand_dir()))["elements"]
                if e["type"] == "text")
    assert text["fontSize"] == 16  # the original hardcoded default
