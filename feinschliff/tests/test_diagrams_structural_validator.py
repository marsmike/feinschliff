"""Tests for `lib.diagrams.structural_validator` — both file well-formedness
and the structural rules salvaged from the old lib/diagram/validator.py.

Replaces the older `test_diagrams_mechanical_checks.py` and pins the
structural-rule behaviour that previously had no test coverage at all."""
from __future__ import annotations

import json
from pathlib import Path

from lib.defects import DefectKind, Severity
from lib.diagrams.structural_validator import (
    validate_diagram_file,
    validate_excalidraw_file,
    validate_excalidraw_structure,
    validate_svg_file,
    validate_svg_structure,
)


# ─── File well-formedness ────────────────────────────────────────────────


def test_svg_valid_passes(tmp_path):
    svg = tmp_path / "x.svg"
    svg.write_text(
        '<?xml version="1.0"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        'width="100" height="100"><rect width="100" height="100"/></svg>'
    )
    assert validate_svg_file(svg) == []


def test_svg_missing_viewbox_warns(tmp_path):
    svg = tmp_path / "x.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"/>'
    )
    defects = validate_svg_file(svg)
    assert any(d.kind == DefectKind.DIAGRAM_INVALID_FILE
               and "viewBox" in d.message for d in defects)


def test_svg_not_svg_is_fatal(tmp_path):
    svg = tmp_path / "x.svg"
    svg.write_text("<html><body>nope</body></html>")
    defects = validate_svg_file(svg)
    assert defects and defects[0].severity == Severity.FATAL


def test_excalidraw_valid_passes(tmp_path):
    j = tmp_path / "x.excalidraw"
    j.write_text(json.dumps({
        "type": "excalidraw",
        "version": 2,
        "elements": [{"type": "rectangle", "x": 0, "y": 0, "width": 10, "height": 10}],
        "appState": {"viewBackgroundColor": "#ffffff"},
    }))
    assert validate_excalidraw_file(j) == []


def test_excalidraw_missing_type_is_fatal(tmp_path):
    j = tmp_path / "x.excalidraw"
    j.write_text(json.dumps({"elements": []}))
    defects = validate_excalidraw_file(j)
    fatals = [d for d in defects if d.severity == Severity.FATAL]
    assert any("type" in d.message for d in fatals)


def test_excalidraw_invalid_json_is_fatal(tmp_path):
    j = tmp_path / "x.excalidraw"
    j.write_text("{ not valid json")
    defects = validate_excalidraw_file(j)
    assert defects[0].severity == Severity.FATAL
    assert "invalid JSON" in defects[0].message


# ─── Structural rules on in-memory Excalidraw docs ────────────────────────


def _doc(*elements) -> dict:
    return {"type": "excalidraw", "elements": list(elements), "appState": {}}


def test_bound_text_overflow_flagged():
    """Text wider than its container -> diagram-overflow defect."""
    doc = _doc(
        {"id": "box1", "type": "rectangle", "x": 0, "y": 0,
         "width": 100, "height": 50},
        {"id": "t1", "type": "text", "x": 5, "y": 10,
         "width": 100, "height": 30, "containerId": "box1",
         "originalText": "a very long line that won't fit in 100 pixels",
         "fontSize": 20},
    )
    defects = validate_excalidraw_structure(doc)
    overflow = [d for d in defects if d.kind == DefectKind.DIAGRAM_OVERFLOW]
    assert overflow, f"expected DIAGRAM_OVERFLOW, got {defects}"


def test_shape_overlap_flagged():
    """Two rects whose bboxes overlap without nesting."""
    doc = _doc(
        {"id": "a", "type": "rectangle", "x": 0, "y": 0,
         "width": 100, "height": 100},
        {"id": "b", "type": "rectangle", "x": 50, "y": 50,
         "width": 100, "height": 100},
    )
    defects = validate_excalidraw_structure(doc)
    overlaps = [d for d in defects if d.kind == DefectKind.DIAGRAM_SHAPE_OVERLAP]
    assert overlaps


def test_shape_nesting_not_flagged():
    """A rect fully containing another is intended nesting, not a defect."""
    doc = _doc(
        {"id": "outer", "type": "rectangle", "x": 0, "y": 0,
         "width": 200, "height": 200},
        {"id": "inner", "type": "rectangle", "x": 20, "y": 20,
         "width": 50, "height": 50},
    )
    defects = validate_excalidraw_structure(doc)
    assert not [d for d in defects if d.kind == DefectKind.DIAGRAM_SHAPE_OVERLAP]


def test_free_text_collision_flagged():
    doc = _doc(
        {"id": "t1", "type": "text", "x": 0, "y": 0,
         "width": 100, "height": 30, "originalText": "first"},
        {"id": "t2", "type": "text", "x": 50, "y": 10,
         "width": 100, "height": 30, "originalText": "second"},
    )
    defects = validate_excalidraw_structure(doc)
    cols = [d for d in defects if d.kind == DefectKind.DIAGRAM_TEXT_COLLISION]
    assert cols


def test_arrow_cross_zone_diagonal_is_fatal():
    """A two-point diagonal arrow whose endpoints fall in two different
    zones is rejected — author must port + elbow it (see methodology §5a).
    """
    doc = _doc(
        # Two zones, side-by-side.
        {"id": "z_left", "type": "rectangle", "x": 0, "y": 0,
         "width": 500, "height": 400,
         "customData": {"dsl_id": "z_left", "dsl_kind": "zone"}},
        {"id": "z_right", "type": "rectangle", "x": 600, "y": 0,
         "width": 500, "height": 400,
         "customData": {"dsl_id": "z_right", "dsl_kind": "zone"}},
        # A diagonal arrow from inside z_left to inside z_right.
        {"id": "arr", "type": "arrow", "x": 100, "y": 50,
         "points": [[0, 0], [800, 300]],
         "startBinding": {"elementId": "src"},
         "endBinding": {"elementId": "dst"}},
    )
    defects = validate_excalidraw_structure(doc)
    flagged = [d for d in defects
               if d.kind == DefectKind.DIAGRAM_ARROW_CROSS_ZONE_UNROUTED]
    assert flagged
    assert all(d.severity == Severity.FATAL for d in flagged)


def test_arrow_cross_zone_axis_aligned_allowed():
    """A horizontal arrow that crosses a zone boundary is fine — same-row
    L→R hops don't read as 'von irgendwo nach irgendwo'."""
    doc = _doc(
        {"id": "z_left", "type": "rectangle", "x": 0, "y": 0,
         "width": 500, "height": 400,
         "customData": {"dsl_id": "z_left", "dsl_kind": "zone"}},
        {"id": "z_right", "type": "rectangle", "x": 600, "y": 0,
         "width": 500, "height": 400,
         "customData": {"dsl_id": "z_right", "dsl_kind": "zone"}},
        # Horizontal — dy ≈ 0.
        {"id": "arr", "type": "arrow", "x": 100, "y": 200,
         "points": [[0, 0], [800, 0]]},
    )
    defects = validate_excalidraw_structure(doc)
    assert not [d for d in defects
                if d.kind == DefectKind.DIAGRAM_ARROW_CROSS_ZONE_UNROUTED]


def test_arrow_cross_zone_polyline_allowed():
    """An elbow-routed (>2 points) arrow across zones is fine — author
    used the routing primitives, so the visual result is clean."""
    doc = _doc(
        {"id": "z_left", "type": "rectangle", "x": 0, "y": 0,
         "width": 500, "height": 400,
         "customData": {"dsl_id": "z_left", "dsl_kind": "zone"}},
        {"id": "z_right", "type": "rectangle", "x": 600, "y": 0,
         "width": 500, "height": 400,
         "customData": {"dsl_id": "z_right", "dsl_kind": "zone"}},
        # 3-point polyline — elbow / via.
        {"id": "arr", "type": "arrow", "x": 100, "y": 50,
         "points": [[0, 0], [0, -40], [800, -40]]},
    )
    defects = validate_excalidraw_structure(doc)
    assert not [d for d in defects
                if d.kind == DefectKind.DIAGRAM_ARROW_CROSS_ZONE_UNROUTED]


def test_arrow_within_single_zone_diagonal_allowed():
    """Diagonal arrows inside one zone are not this defect."""
    doc = _doc(
        {"id": "z", "type": "rectangle", "x": 0, "y": 0,
         "width": 1000, "height": 800,
         "customData": {"dsl_id": "z", "dsl_kind": "zone"}},
        {"id": "arr", "type": "arrow", "x": 100, "y": 100,
         "points": [[0, 0], [400, 300]]},
    )
    defects = validate_excalidraw_structure(doc)
    assert not [d for d in defects
                if d.kind == DefectKind.DIAGRAM_ARROW_CROSS_ZONE_UNROUTED]


def test_arrow_through_non_endpoint_warns():
    """An arrow crossing a non-endpoint rect produces a WARN (not FATAL)."""
    doc = _doc(
        {"id": "src", "type": "rectangle", "x": 0, "y": 0,
         "width": 50, "height": 50},
        {"id": "dst", "type": "rectangle", "x": 400, "y": 0,
         "width": 50, "height": 50},
        # In the way:
        {"id": "obstacle", "type": "rectangle", "x": 200, "y": 0,
         "width": 50, "height": 50},
        {"id": "arr", "type": "arrow", "x": 50, "y": 25,
         "points": [[0, 0], [350, 0]],
         "startBinding": {"elementId": "src"},
         "endBinding": {"elementId": "dst"}},
    )
    defects = validate_excalidraw_structure(doc)
    crosses = [d for d in defects if d.kind == DefectKind.DIAGRAM_ARROW_CROSSING]
    assert crosses
    assert all(d.severity == Severity.WARN for d in crosses)


# ─── End-to-end dispatch ──────────────────────────────────────────────────


def test_validate_diagram_file_dispatches_by_extension(tmp_path):
    svg = tmp_path / "ok.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" '
        'width="10" height="10"/>'
    )
    assert validate_diagram_file(svg) == []

    exc = tmp_path / "ok.excalidraw"
    exc.write_text(json.dumps({
        "type": "excalidraw", "version": 2, "elements": [], "appState": {}
    }))
    assert validate_diagram_file(exc) == []


def test_validate_diagram_file_runs_structural_after_file_ok(tmp_path):
    """When the .excalidraw file is well-formed, structural rules also run."""
    exc = tmp_path / "overlap.excalidraw"
    exc.write_text(json.dumps({
        "type": "excalidraw", "version": 2, "appState": {},
        "elements": [
            {"id": "a", "type": "rectangle", "x": 0, "y": 0,
             "width": 100, "height": 100},
            {"id": "b", "type": "rectangle", "x": 50, "y": 50,
             "width": 100, "height": 100},
        ],
    }))
    defects = validate_diagram_file(exc)
    assert [d for d in defects if d.kind == DefectKind.DIAGRAM_SHAPE_OVERLAP]


# ─── SVG structural rules ────────────────────────────────────────────────


_SVG_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500" '
    'width="1000" height="500">'
)


def test_svg_structure_in_bounds_is_clean():
    svg = _SVG_HEADER + '<rect x="100" y="100" width="200" height="200"/></svg>'
    assert validate_svg_structure(svg) == []


def test_svg_structure_off_right_edge_flagged():
    svg = _SVG_HEADER + '<rect x="900" y="100" width="200" height="100"/></svg>'
    defects = validate_svg_structure(svg)
    assert defects
    assert defects[0].kind == DefectKind.DIAGRAM_OVERFLOW
    assert "right" in defects[0].meta["sides"]


def test_svg_structure_off_negative_position_flagged():
    svg = _SVG_HEADER + '<rect x="-50" y="-50" width="100" height="100"/></svg>'
    defects = validate_svg_structure(svg)
    assert defects
    assert "left" in defects[0].meta["sides"]
    assert "top" in defects[0].meta["sides"]


def test_svg_structure_circle_off_canvas_flagged():
    """Circles bbox via cx/cy/r — make sure that path works."""
    svg = _SVG_HEADER + '<circle cx="990" cy="250" r="50"/></svg>'
    defects = validate_svg_structure(svg)
    assert defects
    assert defects[0].meta["tag"] == "circle"


def test_svg_structure_no_viewbox_skips_bounds_check():
    """If neither viewBox nor width/height parse, return [] not crash."""
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect x="9999" y="9999" width="1" height="1"/></svg>'
    assert validate_svg_structure(svg) == []


def test_svg_structure_tiny_overhang_within_tolerance():
    """A 2px overshoot is below the 4px stroke-width tolerance — clean."""
    svg = _SVG_HEADER + '<rect x="0" y="0" width="1002" height="500"/></svg>'
    assert validate_svg_structure(svg) == []


def test_validate_diagram_file_runs_svg_structural(tmp_path):
    """Dispatcher runs the SVG structural check after the file check."""
    p = tmp_path / "bad.svg"
    p.write_text(_SVG_HEADER + '<rect x="2000" y="100" width="100" height="100"/></svg>')
    defects = validate_diagram_file(p)
    assert any(d.kind == DefectKind.DIAGRAM_OVERFLOW for d in defects)
