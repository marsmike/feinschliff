"""Deck-gate collision prediction: grow each bound slot's rect to its predicted
wrapped height, intersect pairwise + against baked-chrome bboxes. WARN
severity in release 1 (promotable once the false-positive rate is known).
Geometry mirrors the chapter-2 / baked-Steps incidents with synthetic
content.

Geometry validation notes (verified against measure_height_emu):
- tokens dict resolves style:body to size_px=32 (size_pt=16), line_height=1.2
- 30x "wrapping" at DejaVu Sans 16pt in 600px width → ~384px high
- slot a (y=100, height=60): grown bottom = 100+384 = 484, well past b top at y=200
- disjoint case (b at y=700): grown bottom 484 < 700-epsilon → no collision
- unbound pair (y=100, y=110 declared overlap): only "a" bound → no defect
- chrome bbox [80,90,700,100]: slot a grown rect (100,100,600,60) intersects it
"""
import pytest

from feinschliff.content_validator import check_slot_collisions, validate_content
from feinschliff.dsl.parser import parse_lines
from feinschliff.slot_budget import compute_slot_budgets
from feinschmiede.dsl.tokens import Tokens
from feinschmiede.text import measure

RAW = {
    "color": {"ink": "#000000", "paper": "#FFFFFF", "graphite": "#444444"},
    "font-family": {"display": ["DejaVu Sans"], "body": ["DejaVu Sans"]},
    "font-size": {"body": "32px"},
    "font-weight": {"regular": 400},
}


def _budgets(dsl: str):
    tokens = Tokens.from_dict(dict(RAW), brand_name="t")
    nodes, _ = parse_lines(dsl, source="<test>")
    return compute_slot_budgets(nodes, tokens)


def _require_font():
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable")


def test_budget_carries_origin():
    b = _budgets('text 120,340 "{{ t }}" style:body maxwidth:800 maxheight:100')["t"]
    assert (b.x_px, b.y_px) == (120.0, 340.0)


def test_grown_rects_collide():
    """Two stacked slots: the top one's text wraps past its declared box into
    the lower one (chapter-2 class)."""
    _require_font()
    budgets = _budgets(
        'text 100,100 "{{ a }}" style:body maxwidth:600 maxheight:60\n'
        'text 100,200 "{{ b }}" style:body maxwidth:600 maxheight:60'
    )
    long_text = " ".join(["wrapping"] * 30)
    defects = check_slot_collisions(
        {"a": long_text, "b": "Short line"},
        slot_budgets=budgets, chrome_bboxes=None, slide_index=2,
    )
    assert any(d.kind == "slot-collision" for d in defects)
    assert all(d.severity == "warn" for d in defects)
    assert defects[0].slide_index == 2


def test_disjoint_slots_no_defect():
    _require_font()
    budgets = _budgets(
        'text 100,100 "{{ a }}" style:body maxwidth:600 maxheight:60\n'
        'text 100,700 "{{ b }}" style:body maxwidth:600 maxheight:60'
    )
    defects = check_slot_collisions(
        {"a": "Short", "b": "Short"},
        slot_budgets=budgets, chrome_bboxes=None, slide_index=1,
    )
    assert defects == []


def test_chrome_bbox_collision():
    """Slot text over baked chrome (the slide-30 'Step 1…6' class)."""
    _require_font()
    budgets = _budgets('text 100,100 "{{ a }}" style:body maxwidth:600 maxheight:60')
    defects = check_slot_collisions(
        {"a": "Overlapping the baked steps row"},
        slot_budgets=budgets, chrome_bboxes=[[80, 90, 700, 100]], slide_index=1,
    )
    assert any(d.kind == "slot-collision" and "chrome" in d.message for d in defects)


def test_unbound_slots_ignored():
    _require_font()
    budgets = _budgets(
        'text 100,100 "{{ a }}" style:body maxwidth:600 maxheight:60\n'
        'text 100,110 "{{ b }}" style:body maxwidth:600 maxheight:60'
    )
    assert check_slot_collisions(
        {"a": "Bound"}, slot_budgets=budgets, chrome_bboxes=None, slide_index=1,
    ) == []  # b unbound: declared-box overlap is the pack-build lint's job


def test_validate_content_routes_collisions():
    _require_font()
    budgets = _budgets(
        'text 100,100 "{{ a }}" style:body maxwidth:600 maxheight:60\n'
        'text 100,200 "{{ b }}" style:body maxwidth:600 maxheight:60'
    )
    defects = validate_content(
        {"a": " ".join(["wrapping"] * 30), "b": "Short"},
        slide_index=1, slot_budgets=budgets, chrome_bboxes=[],
    )
    assert any(d.kind == "slot-collision" for d in defects)


def test_autoshrink_slot_predicts_fitted_rect():
    """An autoshrink slot that wraps tall at the declared size but fits its
    box after the emitter's shrink must NOT collide with the slot below —
    the predictor models the rescue (final-review C1).

    Arithmetic (DejaVu Sans, body 32px → 16pt, line_height=1.2,
    width=600px, height=80px, EMU_PER_PX=6350):
    - text3 (115 chars) at 16pt → ~153.6px — overflows the 80px declared box.
    - autoshrink_size finds 10pt fits: 48px < 80px → rescue succeeds.
    - Collision predictor must use h_px=max(80, 48)=80px (declared height).
    - Bottom slot at y=220 → top_bottom=100+80=180 < 220 → no collision.
    - Without the fix the predictor would use 153.6px → 253.6 > 220 (false
      positive on every decompiled-pack title+body pair).
    """
    _require_font()
    # top: autoshrink slot, bottom: plain slot below with a 40px gap
    budgets = _budgets(
        'text 100,100 "{{ top }}" style:body maxwidth:600 maxheight:80 autoshrink:true\n'
        'text 100,220 "{{ bot }}" style:body maxwidth:600 maxheight:60'
    )
    # 115-char text wraps to 3 lines at 16pt but autoshrink rescues to 10pt (48px < 80px)
    wrapping_text = "autoshrink rescues this word " * 4
    defects = check_slot_collisions(
        {"top": wrapping_text, "bot": "Short line"},
        slot_budgets=budgets, chrome_bboxes=None, slide_index=1,
    )
    assert defects == [], (
        f"autoshrink rescue should prevent collision but got: {defects}"
    )


def test_autoshrink_floor_overflow_still_collides():
    """Content the 10pt floor cannot contain still grows past the box and
    collides — the predictor doesn't pretend the rescue is magic (final-review C1).

    Arithmetic (same tokens as above, height=80px):
    - text_flood (224 chars) at 10pt floor → ~120px > 80px box — floor fails.
    - Collision predictor must use h_px=max(80, 120)=120px.
    - Bottom slot at y=170 → top_bottom=100+120=220 > 170 → real collision.
    """
    _require_font()
    budgets = _budgets(
        'text 100,100 "{{ top }}" style:body maxwidth:600 maxheight:80 autoshrink:true\n'
        'text 100,170 "{{ bot }}" style:body maxwidth:600 maxheight:60'
    )
    # 224-char text: even at 10pt floor it needs ~120px > 80px box
    flood_text = "overflow " * 25
    defects = check_slot_collisions(
        {"top": flood_text, "bot": "Short line"},
        slot_budgets=budgets, chrome_bboxes=None, slide_index=1,
    )
    assert any(d.kind == "slot-collision" for d in defects), (
        "floor-overflow autoshrink slot should still produce a collision defect"
    )
