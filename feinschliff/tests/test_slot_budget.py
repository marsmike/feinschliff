"""Unit tests for lib/slot_budget — typographic budget extractor."""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.dsl.parser import DSLNode
from lib.dsl.tokens import load_tokens
from lib.slot_budget import (
    SlotBudget,
    compute_slot_budgets,
    format_budget_hint,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BRANDS_DIR = REPO_ROOT / "brands"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokens():
    return load_tokens(BRANDS_DIR / "feinschliff", brands_dir=BRANDS_DIR)


def _text_node(label: str, style: str = "body", maxwidth: str = "760",
               maxheight: str | None = None) -> DSLNode:
    kw = {"style": style, "maxwidth": maxwidth}
    if maxheight is not None:
        kw["maxheight"] = maxheight
    return DSLNode(kind="text", kw_args=kw, label=label)


# ---------------------------------------------------------------------------
# SlotBudget dataclass
# ---------------------------------------------------------------------------

def test_slot_budget_size_pt():
    """size_pt is half of size_px (design-px → pt)."""
    b = SlotBudget(slot="x", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=0.0, font_family="default", bold=False)
    assert b.size_pt == pytest.approx(13.0)


def test_slot_budget_width_emu():
    """width_emu = width_px * 6350."""
    b = SlotBudget(slot="x", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=0.0, font_family="default", bold=False)
    assert b.width_emu == 760 * 6350


def test_slot_budget_height_emu():
    """height_emu = height_px * 6350."""
    b = SlotBudget(slot="x", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=80.0, font_family="default", bold=False)
    assert b.height_emu == 80 * 6350


def test_slot_budget_unconstrained_max_lines():
    """height_px == 0 → max_lines is 999 (sentinel for unconstrained)."""
    b = SlotBudget(slot="x", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=0.0, font_family="default", bold=False)
    assert b.max_lines == 999


def test_slot_budget_max_lines_constrained():
    """height_px / (size_px * line_height) gives integer floor."""
    # 80px / (26px * 1.4) ≈ 2.197 → floor = 2
    b = SlotBudget(slot="x", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=80.0, font_family="default", bold=False)
    import math
    expected = max(1, math.floor(80.0 / (26.0 * 1.4)))
    assert b.max_lines == expected


def test_slot_budget_max_chars_unconstrained():
    """Unconstrained height → max_chars is 9999 sentinel."""
    b = SlotBudget(slot="x", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=0.0, font_family="default", bold=False)
    assert b.max_chars == 9999


def test_slot_budget_max_chars_constrained():
    """max_chars = chars_per_line * max_lines."""
    b = SlotBudget(slot="x", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=80.0, font_family="default", bold=False)
    assert b.max_chars == b.chars_per_line * b.max_lines


def test_slot_budget_chars_per_line_positive():
    """chars_per_line is always ≥ 1."""
    b = SlotBudget(slot="x", style="body", size_px=1000.0, line_height=1.4,
                   width_px=1.0, height_px=0.0, font_family="default", bold=False)
    assert b.chars_per_line >= 1


# ---------------------------------------------------------------------------
# _extract_single_slot (via compute_slot_budgets)
# ---------------------------------------------------------------------------

def test_compute_skips_non_text_nodes():
    """rect/picture nodes are not parsed for slots."""
    tokens = _tokens()
    nodes = [
        DSLNode(kind="rect", kw_args={"fill": "accent"}, label=None),
        DSLNode(kind="picture", kw_args={"slot": "hero"}, label="hero"),
    ]
    assert compute_slot_budgets(nodes, tokens) == {}


def test_compute_skips_multi_slot_label():
    """Labels with 2+ {{ }} placeholders are ignored — ambiguous width."""
    tokens = _tokens()
    nodes = [_text_node("{{ a }} and {{ b }}", maxwidth="760")]
    assert compute_slot_budgets(nodes, tokens) == {}


def test_compute_skips_zero_slot_label():
    """Labels with no {{ }} are ignored."""
    tokens = _tokens()
    nodes = [_text_node("static text", maxwidth="760")]
    assert compute_slot_budgets(nodes, tokens) == {}


def test_compute_skips_node_without_maxwidth():
    """Nodes without maxwidth have unbounded width — no useful budget."""
    tokens = _tokens()
    node = DSLNode(kind="text", kw_args={"style": "body"}, label="{{ body }}")
    assert compute_slot_budgets([node], tokens) == {}


def test_compute_single_slot():
    """Happy path: one text node with single slot → one budget entry."""
    tokens = _tokens()
    nodes = [_text_node("{{ action_title }}", style="act-title", maxwidth="1200")]
    budgets = compute_slot_budgets(nodes, tokens)
    assert "action_title" in budgets
    b = budgets["action_title"]
    assert b.slot == "action_title"
    assert b.style == "act-title"
    assert b.width_px == 1200.0


def test_compute_normalises_array_indices():
    """cells[0].heading → cells[].heading in normalised key."""
    tokens = _tokens()
    nodes = [_text_node("{{ cells[0].heading }}", maxwidth="300")]
    budgets = compute_slot_budgets(nodes, tokens)
    assert "cells[].heading" in budgets
    assert "cells[0].heading" not in budgets


def test_compute_tightest_budget_wins():
    """When two nodes share a slot, the one with smaller max_chars is kept."""
    tokens = _tokens()
    nodes = [
        _text_node("{{ body }}", style="body", maxwidth="760", maxheight="200"),
        _text_node("{{ body }}", style="body", maxwidth="300", maxheight="80"),
    ]
    budgets = compute_slot_budgets(nodes, tokens)
    assert "body" in budgets
    # The narrower/shorter node should win.
    assert budgets["body"].width_px == 300.0


def test_compute_margin_shrinks_effective_dimensions():
    """margin=0.10 reduces effective width and height by 10%."""
    tokens = _tokens()
    nodes = [_text_node("{{ title }}", style="body", maxwidth="760", maxheight="80")]
    b_no_margin = compute_slot_budgets(nodes, tokens, margin=0.0)
    b_margin = compute_slot_budgets(nodes, tokens, margin=0.10)
    assert b_margin["title"].width_px == pytest.approx(760.0 * 0.90)
    assert b_margin["title"].height_px == pytest.approx(80.0 * 0.90)


def test_compute_height_zero_when_no_maxheight():
    """No maxheight → height_px = 0 (unconstrained)."""
    tokens = _tokens()
    nodes = [_text_node("{{ title }}", style="body", maxwidth="760")]
    budgets = compute_slot_budgets(nodes, tokens)
    assert budgets["title"].height_px == 0.0


def test_compute_real_layout_has_budgets():
    """Smoke test: executive-summary layout parses to ≥1 slot budget."""
    from lib.dsl.parser import parse_file
    layout_path = REPO_ROOT / "layouts" / "executive-summary.slide.dsl"
    if not layout_path.is_file():
        pytest.skip("layout not present")
    nodes, _ = parse_file(layout_path)
    tokens = _tokens()
    budgets = compute_slot_budgets(nodes, tokens)
    assert len(budgets) >= 1


# ---------------------------------------------------------------------------
# format_budget_hint
# ---------------------------------------------------------------------------

def test_format_budget_hint_empty():
    """Empty budget dict → empty string."""
    assert format_budget_hint({}) == ""


def test_format_budget_hint_contains_slot_name():
    """Formatted hint mentions the slot name."""
    b = SlotBudget(slot="action_title", style="act-title", size_px=56.0, line_height=1.1,
                   width_px=1200.0, height_px=120.0, font_family="default", bold=False)
    hint = format_budget_hint({"action_title": b})
    assert "action_title" in hint


def test_format_budget_hint_contains_style():
    """Formatted hint mentions the style name."""
    b = SlotBudget(slot="action_title", style="act-title", size_px=56.0, line_height=1.1,
                   width_px=1200.0, height_px=120.0, font_family="default", bold=False)
    hint = format_budget_hint({"action_title": b})
    assert "act-title" in hint


def test_format_budget_hint_contains_chars_per_line():
    """Formatted hint reports chars/line."""
    b = SlotBudget(slot="body", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=0.0, font_family="default", bold=False)
    hint = format_budget_hint({"body": b})
    assert "chars/line" in hint


def test_format_budget_hint_unconstrained_slot():
    """Unconstrained slot (height_px=0) says 'unconstrained'."""
    b = SlotBudget(slot="body", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=0.0, font_family="default", bold=False)
    hint = format_budget_hint({"body": b})
    assert "unconstrained" in hint


def test_format_budget_hint_rules_appended():
    """Formatting appends the hyphen-compound and chars/line rules."""
    b = SlotBudget(slot="x", style="body", size_px=26.0, line_height=1.4,
                   width_px=760.0, height_px=0.0, font_family="default", bold=False)
    hint = format_budget_hint({"x": b})
    assert "hyphens" in hint.lower() or "hyphen" in hint.lower()


# ---------------------------------------------------------------------------
# slot-overflow defect via validate_content
# ---------------------------------------------------------------------------

from lib.content_validator import validate_content


def test_slot_overflow_not_fired_without_budgets():
    """Without slot_budgets, overflow defect is never emitted."""
    ctx = {"action_title": "x" * 300}
    defects = validate_content(ctx, slide_index=1)
    assert not any(d.kind == "slot-overflow" for d in defects)


def test_slot_overflow_not_fired_for_fitting_text():
    """Short text that fits the box → no slot-overflow defect."""
    tokens = _tokens()
    nodes = [_text_node("{{ action_title }}", style="act-title",
                        maxwidth="1200", maxheight="130")]
    budgets = compute_slot_budgets(nodes, tokens)
    ctx = {"action_title": "Revenue up 12%."}
    defects = validate_content(ctx, slide_index=1, slot_budgets=budgets)
    assert not any(d.kind == "slot-overflow" for d in defects)


def test_slot_overflow_fires_for_overflowing_text():
    """Very long text in a tight box → slot-overflow defect."""
    tokens = _tokens()
    # Very narrow box — even a short sentence won't fit.
    nodes = [_text_node("{{ action_title }}", style="act-title",
                        maxwidth="50", maxheight="30")]
    budgets = compute_slot_budgets(nodes, tokens)
    ctx = {"action_title": "Revenue is up by twelve percent this quarter due to enterprise growth"}
    defects = validate_content(ctx, slide_index=3, slot_budgets=budgets)
    overflow = [d for d in defects if d.kind == "slot-overflow"]
    assert len(overflow) == 1
    assert overflow[0].slot == "action_title"
    assert overflow[0].slide_index == 3


def test_slot_overflow_skips_unconstrained_height():
    """No maxheight (height_px=0) → slot-overflow never fires even for long text."""
    tokens = _tokens()
    nodes = [_text_node("{{ body }}", style="body", maxwidth="200")]
    budgets = compute_slot_budgets(nodes, tokens)
    assert budgets["body"].height_px == 0.0
    ctx = {"body": "x " * 500}
    defects = validate_content(ctx, slide_index=1, slot_budgets=budgets)
    assert not any(d.kind == "slot-overflow" for d in defects)


def test_slot_overflow_skips_empty_value():
    """Empty string → no slot-overflow defect even for tight box."""
    tokens = _tokens()
    nodes = [_text_node("{{ action_title }}", style="act-title",
                        maxwidth="50", maxheight="30")]
    budgets = compute_slot_budgets(nodes, tokens)
    ctx = {"action_title": ""}
    defects = validate_content(ctx, slide_index=1, slot_budgets=budgets)
    assert not any(d.kind == "slot-overflow" for d in defects)


def test_slot_overflow_message_is_helpful():
    """Overflow defect message mentions the constraint details."""
    tokens = _tokens()
    nodes = [_text_node("{{ action_title }}", style="act-title",
                        maxwidth="50", maxheight="30")]
    budgets = compute_slot_budgets(nodes, tokens)
    ctx = {"action_title": "Revenue up twelve percent due to enterprise growth this quarter"}
    defects = validate_content(ctx, slide_index=1, slot_budgets=budgets)
    overflow = [d for d in defects if d.kind == "slot-overflow"]
    assert overflow
    msg = overflow[0].message
    assert "chars/line" in msg
    assert "act-title" in msg


# ---------------------------------------------------------------------------
# _iter_slot_values (indirectly via validate_content w/ budgets)
# ---------------------------------------------------------------------------

def test_iter_slot_values_flat_dict():
    """Flat dict keys map directly to slot paths."""
    tokens = _tokens()
    nodes = [_text_node("{{ title }}", style="body", maxwidth="760", maxheight="80")]
    budgets = compute_slot_budgets(nodes, tokens)
    # Trigger overflow for a known long title.
    long_title = "w " * 200
    defects = validate_content({"title": long_title}, slide_index=1, slot_budgets=budgets)
    overflow = [d for d in defects if d.kind == "slot-overflow" and d.slot == "title"]
    assert len(overflow) == 1


def test_iter_slot_values_nested_dict():
    """Nested dict: budget keyed as cells[].heading, defect reports cells[0].heading."""
    tokens = _tokens()
    nodes = [_text_node("{{ cells[0].heading }}", style="body",
                        maxwidth="50", maxheight="30")]
    budgets = compute_slot_budgets(nodes, tokens)
    ctx = {"cells": [{"heading": "x " * 50}]}
    defects = validate_content(ctx, slide_index=1, slot_budgets=budgets)
    overflow = [d for d in defects if d.kind == "slot-overflow"]
    assert len(overflow) == 1
    # Budget key is normalised, defect carries the raw index for diagnostics.
    assert overflow[0].slot == "cells[0].heading"


def test_iter_slot_values_non_string_leaves_skipped():
    """Integer/bool leaves in ctx don't cause slot-overflow checks."""
    tokens = _tokens()
    nodes = [_text_node("{{ count }}", style="body", maxwidth="50", maxheight="30")]
    budgets = compute_slot_budgets(nodes, tokens)
    ctx = {"count": 42}  # int, not str — should be ignored
    defects = validate_content(ctx, slide_index=1, slot_budgets=budgets)
    assert not any(d.kind == "slot-overflow" for d in defects)
