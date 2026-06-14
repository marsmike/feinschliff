"""Tests for the validator updates that handle virtual viewport metadata.

`diagram-overflow` should compare against the virtual canvas (not the slot),
and `diagram-text-too-small` should factor in the downscale PowerPoint
applies on insert.
"""
from __future__ import annotations

from dataclasses import dataclass, field


from feinschliff.layout_validator import validate_diagrams, validate_diagrams_text_size


@dataclass
class FakeNode:
    kind: str
    kw_args: dict = field(default_factory=dict)


def _make_pic(*, slot_w=1720, slot_h=720, virtual_w=6880, virtual_h=2880,
              primitives=None):
    return FakeNode(
        kind="picture",
        kw_args={
            "id": "d",
            "x": 0, "y": 0, "w": slot_w, "h": slot_h,
            "src": "/tmp/fake.png",
            "_diagram_meta": {
                "kind": "excalidraw",
                "source_dsl": "",
                "internal_primitives": primitives or [],
                "virtual_canvas_w": virtual_w,
                "virtual_canvas_h": virtual_h,
                "slot_w": slot_w,
                "slot_h": slot_h,
            },
        },
    )


def test_overflow_uses_virtual_canvas_not_slot():
    """A box at x=4000 in a 6880-virtual / 1720-slot diagram is FINE —
    well within the virtual canvas. The pre-virtual validator would
    have flagged it as overflowing the 1720 slot."""
    pic = _make_pic(primitives=[
        {"id": "b1", "kind": "rect", "x": 4000, "y": 200, "w": 500, "h": 300,
         "label": None, "role": None, "font_size": None},
    ])
    defects = validate_diagrams([pic], slide_index=1, slide_w=1920, slide_h=1080)
    assert defects == [], f"unexpected overflow at virtual scale: {defects}"


def test_overflow_still_fires_when_primitive_escapes_virtual_canvas():
    pic = _make_pic(primitives=[
        {"id": "b1", "kind": "rect", "x": 6500, "y": 200, "w": 500, "h": 300,
         "label": None, "role": None, "font_size": None},
    ])
    defects = validate_diagrams([pic], slide_index=1, slide_w=1920, slide_h=1080)
    assert len(defects) == 1
    assert defects[0].kind == "diagram-overflow"


def test_text_too_small_factors_in_virtual_downscale():
    """A virtual-canvas font of 60px in a 4× downscaled slot becomes
    ~15px effective on slide — well above the 12pt body minimum. The
    pre-virtual validator would have computed 60*0.896=54pt and missed
    the actual rendering scale entirely (false-pass, not false-fail)."""
    pic = _make_pic(primitives=[
        {"id": "t1", "kind": "text", "x": 200, "y": 200, "w": 400, "h": 60,
         "label": "Hi", "role": "body", "font_size": 60.0},
    ])
    defects = validate_diagrams_text_size([pic], slide_index=1, slide_w=1920, slide_h=1080)
    assert defects == [], f"60px in 4× virtual should be ~15pt on slide, got defects: {defects}"


def test_text_too_small_fires_when_virtual_font_genuinely_tiny():
    """A virtual-canvas font of 20px in a 6880-virtual / 1720-slot diagram
    is genuinely too small: 20 * (1720/6880) * (1720/1920) ≈ 4.5pt."""
    pic = _make_pic(primitives=[
        {"id": "t1", "kind": "text", "x": 200, "y": 200, "w": 400, "h": 20,
         "label": "Hi", "role": "body", "font_size": 20.0},
    ])
    defects = validate_diagrams_text_size([pic], slide_index=1, slide_w=1920, slide_h=1080)
    assert len(defects) == 1
    assert defects[0].kind == "diagram-text-too-small"


def test_legacy_no_virtual_field_preserves_old_behavior():
    """Pre-virtual `_diagram_meta` payloads (no virtual_canvas_w field)
    must compute the same on-slide font size as before this change."""
    pic = FakeNode(
        kind="picture",
        kw_args={
            "id": "d",
            "x": 0, "y": 0, "w": 1720, "h": 480,
            "src": "/tmp/fake.png",
            "_diagram_meta": {
                "kind": "excalidraw",
                "source_dsl": "",
                "internal_primitives": [
                    {"id": "t1", "kind": "text", "x": 100, "y": 100, "w": 200, "h": 20,
                     "label": "Hi", "role": "body", "font_size": 14.0},
                ],
            },
        },
    )
    defects = validate_diagrams_text_size([pic], slide_index=1, slide_w=1920, slide_h=1080)
    # 14 * (1720/1920) ≈ 12.5pt body — just above the 12pt minimum, no defect.
    assert defects == []
