"""Tests for lib/diagrams/excalidraw_expand.py."""
from __future__ import annotations

import json
from pathlib import Path


from feinschmiede.diagrams.excalidraw_expand import expand


def _brand_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "feinschliff" / "brands" / "feinschliff"


def test_empty_canvas_emits_valid_excalidraw():
    j = json.loads(expand("canvas 800x600", brand_dir=_brand_dir()))
    assert j["type"] == "excalidraw"
    assert j["elements"] == []
    assert j["appState"]["viewBackgroundColor"]


def test_box_node():
    dsl = """
canvas 800x600
box api 100,100 200x80 "API"
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    types = [e["type"] for e in j["elements"]]
    assert "rectangle" in types
    assert "text" in types  # label bound to rectangle


def test_arrow():
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    types = [e["type"] for e in j["elements"]]
    assert types.count("rectangle") == 2
    assert "arrow" in types


def _find_arrow(elements):
    return next(e for e in elements if e["type"] == "arrow")


def _absolute_waypoints(arrow):
    x, y = arrow["x"], arrow["y"]
    return [(x + px, y + py) for px, py in arrow["points"]]


def test_arrow_horizontal_neighbor_is_straight_right():
    """a@(100,100,100x60) → b@(400,100,100x60): straight, exits right of a, enters left of b."""
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    arrow = _find_arrow(j["elements"])
    pts = _absolute_waypoints(arrow)
    assert pts == [(200.0, 130.0), (400.0, 130.0)], pts


def test_arrow_horizontal_neighbor_reverse_is_straight_left():
    """dst left of src: exit src LEFT, enter dst RIGHT."""
    dsl = """
canvas 800x600
box a 400,100 100x60 "A"
box b 100,100 100x60 "B"
arrow a -> b
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_find_arrow(j["elements"]))
    assert pts == [(400.0, 130.0), (200.0, 130.0)], pts


def test_arrow_vertical_stacked_goes_down():
    """Same column, dst below: exit bottom of src, enter top of dst."""
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 100,300 100x60 "B"
arrow a -> b
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_find_arrow(j["elements"]))
    assert pts == [(150.0, 160.0), (150.0, 300.0)], pts


def test_arrow_vertical_stacked_goes_up():
    """dst above src: exit top of src, enter bottom of dst."""
    dsl = """
canvas 800x600
box a 100,300 100x60 "A"
box b 100,100 100x60 "B"
arrow a -> b
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_find_arrow(j["elements"]))
    assert pts == [(150.0, 300.0), (150.0, 160.0)], pts


def test_arrow_diagonal_is_straight_edge_to_edge():
    """Diagonal arrow: single straight segment from src-border to dst-border
    along the center-to-center ray. Matches the upstream Excalidraw plugin's
    `make_arrow` (and matches what excalidraw.com renders).
    """
    dsl = """
canvas 1200x600
box a 60,80 180x80 "A"
box b 540,260 180x80 "B"
arrow a -> b
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_find_arrow(j["elements"]))
    assert len(pts) == 2, f"expected 2-point straight line, got {pts}"
    # Ray center-to-center goes right-and-down; hits a's right edge first
    # (|dx|=480 vs |dy|=180), then mirror on b's left edge.
    assert pts[0] == (240.0, 153.75), pts
    assert pts[1] == (540.0, 266.25), pts


def test_arrow_label_emits_text_element_at_midpoint():
    """`arrow X -> Y label:"text"` emits the arrow plus a text element
    centered on the routed polyline's midpoint."""
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 400,100 100x60 "B"
arrow a -> b label:"calls"
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    arrows = [e for e in j["elements"] if e["type"] == "arrow"]
    assert len(arrows) == 1
    label_texts = [e for e in j["elements"] if e["type"] == "text" and e.get("text") == "calls"]
    assert len(label_texts) == 1, f"expected 1 'calls' label, got {label_texts}"


def test_diamond_primitive_emits_diamond_type():
    dsl = """
canvas 800x600
diamond d 100,100 200x120 "Decision?" fill:warning
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    shape = next(e for e in j["elements"] if e["type"] == "diamond")
    assert shape["width"] == 200 and shape["height"] == 120


def test_dot_primitive_is_12px_filled_ellipse():
    dsl = """
canvas 400x300
dot marker 150,80 fill:accent
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    dot = j["elements"][0]
    assert dot["type"] == "ellipse"
    assert dot["width"] == 12 and dot["height"] == 12
    assert dot["x"] == 144 and dot["y"] == 74


def test_line_primitive_with_dashed_flag():
    dsl = """
canvas 800x600
line divider 100,200 700,200 dashed
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    line_el = j["elements"][0]
    assert line_el["type"] == "line"
    assert line_el["strokeStyle"] == "dashed"
    assert line_el["points"] == [[0, 0], [600, 0]]


def test_theme_dark_sets_dark_background():
    dsl = """
canvas 800x600
theme dark
box a 100,100 200x80 "Hi"
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    # ink (dark) becomes the canvas background under theme dark
    assert j["appState"]["viewBackgroundColor"].lower() != "#faf8f3"  # not paper


def test_inactive_color_renders_dashed_stroke():
    dsl = """
canvas 800x600
box stale 100,100 200x80 "Deprecated" fill:inactive
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    shape = next(e for e in j["elements"] if e["type"] == "rectangle")
    assert shape["strokeStyle"] == "dashed"


def test_group_assigns_shared_group_id():
    dsl = """
canvas 800x600
box a 100,100 100x60 "A"
box b 300,100 100x60 "B"
group a b
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    rects = [e for e in j["elements"] if e["type"] == "rectangle"]
    assert len(rects) == 2
    gid_a = rects[0].get("groupIds", [])
    gid_b = rects[1].get("groupIds", [])
    assert gid_a and gid_a == gid_b, f"group ids should match: {gid_a} vs {gid_b}"


def test_box_label_backslash_n_becomes_real_newline():
    """DSL `\\n` in a box label should ship as a real newline in the JSON,
    not the literal two-character escape sequence."""
    dsl = """
canvas 800x600
box a 100,100 200x80 "First line\\nSecond line"
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    text = next(e for e in j["elements"] if e["type"] == "text")
    assert text["text"] == "First line\nSecond line", repr(text["text"])


def test_arrow_diagonal_upward_is_straight_edge_to_edge():
    """src below+right of dst: straight diagonal from a's left/top border to
    b's right/bottom border. Symmetric inverse of the downward case.
    """
    dsl = """
canvas 1200x600
box a 540,260 180x80 "A"
box b 60,80 180x80 "B"
arrow a -> b
"""
    j = json.loads(expand(dsl, brand_dir=_brand_dir()))
    pts = _absolute_waypoints(_find_arrow(j["elements"]))
    assert len(pts) == 2, f"expected 2-point straight line, got {pts}"
    assert pts[0] == (540.0, 266.25), pts
    assert pts[1] == (240.0, 153.75), pts
