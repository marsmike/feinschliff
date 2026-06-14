from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path



@dataclass
class _FakePic:
    """Picture node carrying diagram meta — mimics what expand_diagram_blocks emits.

    NOTE: actual DSLNode uses kw_args. This fake stores everything in kw_args
    to match the validator's read pattern.
    """
    kind: str = "picture"
    kw_args: dict = field(default_factory=dict)


# Task 18: diagram-overflow
def test_diagram_overflow_caught():
    from feinschliff.layout_validator import validate_diagrams
    pic = _FakePic(
        kw_args={
            "id": "chart", "x": 100, "y": 200, "w": 800, "h": 400,
            "_diagram_meta": {
                "kind": "svg",
                "source_dsl": "...",
                "internal_primitives": [
                    {"id": "b1", "kind": "rect", "x": 0, "y": 0, "w": 200, "h": 300},
                    {"id": "overflow", "kind": "rect", "x": 700, "y": 350, "w": 200, "h": 200},
                ],
            },
        },
    )
    defects = validate_diagrams([pic], slide_index=1, slide_w=1920, slide_h=1080)
    overflow = [d for d in defects if d.kind == "diagram-overflow"]
    assert len(overflow) == 1
    assert "overflow" in overflow[0].message


def test_diagram_overflow_clean_fixture_zero_defects():
    from feinschliff.layout_validator import validate_diagrams
    pic = _FakePic(
        kw_args={
            "id": "chart", "x": 100, "y": 200, "w": 800, "h": 400,
            "_diagram_meta": {
                "kind": "svg",
                "source_dsl": "...",
                "internal_primitives": [
                    {"id": "b1", "kind": "rect", "x": 0, "y": 0, "w": 200, "h": 300},
                    {"id": "b2", "kind": "rect", "x": 300, "y": 50, "w": 200, "h": 300},
                ],
            },
        },
    )
    defects = validate_diagrams([pic], slide_index=1, slide_w=1920, slide_h=1080)
    assert defects == []


# Task 19: diagram-color-mismatch
def test_diagram_color_mismatch_caught(tmp_path):
    from feinschliff.layout_validator import validate_diagrams_color
    rendered = tmp_path / "evil.svg"
    rendered.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<rect width="100" height="100" fill="#FF00FF"/></svg>'
    )
    png_path = rendered.with_suffix(".png")
    png_path.write_bytes(b"placeholder")

    pic = _FakePic(
        kw_args={
            "id": "chart", "x": 0, "y": 0, "w": 100, "h": 100,
            "src": str(png_path),
            "_diagram_meta": {"kind": "svg", "source_dsl": "...", "internal_primitives": []},
        },
    )
    brand_dir = Path(__file__).resolve().parent.parent.parent / "feinschliff" / "brands" / "feinschliff"
    defects = validate_diagrams_color([pic], slide_index=1, brand_dir=brand_dir)
    mismatches = [d for d in defects if d.kind == "diagram-color-mismatch"]
    assert len(mismatches) == 1
    assert "#FF00FF" in mismatches[0].message or "#ff00ff" in mismatches[0].message


# Task 20: diagram-text-too-small
def test_diagram_text_too_small_caught():
    from feinschliff.layout_validator import validate_diagrams_text_size
    pic = _FakePic(
        kw_args={
            "id": "chart", "x": 0, "y": 0, "w": 200, "h": 200,
            "_diagram_meta": {
                "kind": "svg",
                "source_dsl": "...",
                "internal_primitives": [
                    {"id": "t1", "kind": "text", "x": 10, "y": 10, "w": 100, "h": 20,
                     "label": "tiny", "role": "body", "font_size": 7.0},
                ],
            },
        },
    )
    defects = validate_diagrams_text_size([pic], slide_index=1, slide_w=1920, slide_h=1080)
    smalls = [d for d in defects if d.kind == "diagram-text-too-small"]
    assert len(smalls) == 1
    assert "t1" in smalls[0].message
