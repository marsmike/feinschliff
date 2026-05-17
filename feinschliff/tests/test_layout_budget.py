"""Tests for lib/layout_budget — the two-pass deck planner that
re-ranks `pick_layout` candidates with a usage-budget bonus.

The point of the module is to surface under-used layouts in long decks
without overriding strong affinity matches. Tests pin both halves of
that contract.
"""
from __future__ import annotations

import pytest

from lib.layout_budget import (
    _MAX_BUDGET_BONUS,
    _SINGLETON_LAYOUTS,
    _budget_bonus,
    plan_deck_layouts,
)


# --- _budget_bonus -----------------------------------------------------


def test_budget_bonus_starts_at_max_for_unused():
    assert _budget_bonus("vertical-bullets", 0) == _MAX_BUDGET_BONUS


def test_budget_bonus_diminishes_with_usage():
    """Usage 0→1.5, 1→0.75, 2→0.50, 3→0.375 — monotonic decrease."""
    prev = float("inf")
    for n in range(6):
        b = _budget_bonus("vertical-bullets", n)
        assert b < prev, f"bonus should decrease at usage={n}: {prev} → {b}"
        prev = b


def test_budget_bonus_inert_for_singletons():
    for lid in _SINGLETON_LAYOUTS:
        for n in range(5):
            assert _budget_bonus(lid, n) == 0.0, (
                f"singleton {lid!r} should never receive a budget bonus"
            )


# --- plan_deck_layouts: shape + ordering -------------------------------


def test_plan_returns_one_assignment_per_slide():
    signals = [
        {"role": "content-columns", "concept_count": 3},
        {"role": "data-comparison", "concept_count": 4, "comparison": True},
        {"role": "data-timeline", "concept_count": 5},
    ]
    out = plan_deck_layouts(signals)
    assert len(out) == len(signals)
    for entry in out:
        assert {"layout", "base_score", "budget_bonus", "rationale"} <= set(entry)


def test_plan_preserves_input_order():
    """Title goes first, closer goes last — assignments line up by index."""
    signals = [
        {"role": "title-primary", "concept_count": 1},
        {"role": "content-columns", "concept_count": 3},
        {"role": "closer", "concept_count": 3},
    ]
    out = plan_deck_layouts(signals)
    assert out[0]["layout"] in {"title-orange", "title-ink", "action-title"}
    # The closer slide must resolve to a closer-role layout.
    closer_layouts = {"key-takeaways", "end", "next-steps"}
    assert out[-1]["layout"] in closer_layouts


def test_plan_falls_back_to_text_picture_when_no_candidates():
    """A slide with no usable signals still gets an assignment."""
    # role=None, no other signals → pick_layout returns no positive
    # candidates → fallback path fires.
    out = plan_deck_layouts([{}])
    assert out[0]["layout"] == "text-picture"
    assert "fallback:no-candidates" in out[0]["rationale"]


# --- The main contract: deck-wide variance -----------------------------


def test_six_identical_content_columns_slides_use_more_than_three_layouts():
    """The baseline picker rotates exactly 3 layouts for this shape
    (executive-summary / horizontal-bullets / pyramid). The budget
    planner must cover ≥ 5 of the 8 eligible content-columns layouts
    over a 6-slide run."""
    signals = [{"role": "content-columns", "concept_count": 3}] * 6
    out = plan_deck_layouts(signals)
    distinct = {a["layout"] for a in out}
    assert len(distinct) >= 5, (
        f"expected ≥5 distinct layouts across 6 identical content-columns "
        f"slides, got {len(distinct)}: {[a['layout'] for a in out]}"
    )


def test_three_data_comparison_slides_use_three_distinct_layouts():
    """data-comparison has 10 eligible members. Three slides with the
    natural variation a real deck carries (one tabular comparison, two
    charted at different sizes) must yield three different picks.

    A perfectly-identical-signal trio would correctly converge onto the
    same top-two layouts — that's the picker behaving, not a bug. The
    bonus only flips ties and near-ties; it cannot (and should not)
    leap over a +2 data-band mismatch."""
    signals = [
        # Tabular comparison: 2x2-matrix / scorecard territory.
        {"role": "data-comparison", "concept_count": 4,
         "data_quantity": 10, "comparison": True},
        # Charted comparison, wider spread: bar/stacked/svg territory.
        {"role": "data-comparison", "concept_count": 5,
         "data_quantity": 30, "comparison": True},
        # Charted comparison, mid-size: graphical / line territory.
        {"role": "data-comparison", "concept_count": 4,
         "data_quantity": 28, "comparison": True},
    ]
    out = plan_deck_layouts(signals)
    chosen = [a["layout"] for a in out]
    assert len(set(chosen)) == 3, (
        f"three varied data-comparison slides should pick three distinct "
        f"layouts, got {chosen}"
    )


def test_three_chapter_openers_alternate_orange_and_ink():
    """Both chapter variants must appear when the deck has multiple
    chapters. (Both are structural and exempt from the picker's
    variety penalty, but the budget bonus reaches them.)"""
    signals = [{"role": "chapter-opener", "concept_count": 1}] * 3
    out = plan_deck_layouts(signals)
    chosen = [a["layout"] for a in out]
    assert {"chapter-orange", "chapter-ink"} <= set(chosen), (
        f"both chapter variants should appear across 3 chapter-openers, "
        f"got {chosen}"
    )


# --- The other half of the contract: don't override strong affinity ---


def test_budget_does_not_override_strong_affinity_match():
    """A slide with a unique, high-affinity fingerprint must still win
    even if the budget bonus is pushing other layouts. A risk-matrix
    slide should still pick `risk-matrix`, not be swept away by an
    under-used scorecard."""
    # First, exhaust a bunch of other data-comparison layouts so the
    # budget would prefer the under-used ones.
    warmup = [{
        "role": "data-comparison", "concept_count": 4,
        "data_quantity": 10, "comparison": True,
    }] * 5
    risk_slide = {
        "role": "data-comparison", "concept_count": 6,
        "comparison": True, "narrative_role": "risk",
    }
    out = plan_deck_layouts(warmup + [risk_slide])
    assert out[-1]["layout"] == "risk-matrix", (
        f"risk fingerprint must dominate budget pressure; got "
        f"{out[-1]['layout']} (warmup: {[a['layout'] for a in out[:-1]]})"
    )


def test_budget_bonus_recorded_in_rationale():
    """When the budget bonus contributes to a pick, the rationale
    string should mention it — useful for debugging plan-skeleton runs."""
    signals = [{"role": "content-columns", "concept_count": 3}] * 4
    out = plan_deck_layouts(signals)
    # By slide #4, at least one prior layout has been used and the
    # winner's rationale should reflect a budget contribution.
    has_budget_rationale = any(
        any("budget-bonus" in r for r in a["rationale"])
        for a in out
    )
    assert has_budget_rationale, (
        f"expected at least one assignment to record a budget bonus; "
        f"rationales: {[a['rationale'] for a in out]}"
    )


def test_first_slide_gets_max_bonus_for_its_winner():
    """The first slide has zero prior usage, so its winning layout
    receives the full +1.5 bonus."""
    out = plan_deck_layouts([
        {"role": "content-columns", "concept_count": 3},
    ])
    assert out[0]["budget_bonus"] == _MAX_BUDGET_BONUS


def test_singleton_layouts_get_no_bonus_in_rationale():
    """A singleton layout (agenda / end / full-bleed-cover) receives no
    budget bonus and emits no budget marker in its rationale.

    Title slides (title-orange / title-ink) deliberately AREN'T
    singletons — they compete with each other and DO get the bonus —
    so we test against `agenda` which is in `_SINGLETON_LAYOUTS`."""
    out = plan_deck_layouts([{"role": "agenda", "concept_count": 5}])
    assert out[0]["layout"] == "agenda"
    assert out[0]["budget_bonus"] == 0.0
    assert not any("budget-bonus" in r for r in out[0]["rationale"])


def test_fallback_does_not_pollute_usage_or_history():
    """When `pick_layout` returns no candidates, the planner falls back
    to `text-picture` but must NOT count that synthetic pick against
    text-picture's deck-wide usage budget. A later slide that genuinely
    qualifies for text-picture should still receive the full +1.5
    unused-layout bonus."""
    out = plan_deck_layouts([
        # No signals — falls back to text-picture.
        {},
        # Genuine text-picture candidate.
        {"role": "content-with-visual", "concept_count": 2},
    ])
    assert out[0]["layout"] == "text-picture"
    assert "fallback:no-candidates" in out[0]["rationale"]
    # The second slide must see text-picture as unused — full bonus.
    assert out[1]["layout"] == "text-picture", (
        f"second slide should pick text-picture on signals, got {out[1]['layout']}"
    )
    assert out[1]["budget_bonus"] == 1.5, (
        f"fallback should not have consumed text-picture's budget; "
        f"got bonus={out[1]['budget_bonus']}"
    )


# --- Regression: budget planner respects role gating -------------------


def test_plan_never_picks_unrelated_role():
    """A title-primary slide must never resolve to a content layout
    just because the content layout is under-used."""
    out = plan_deck_layouts([
        # 6 content slides first to load up content-columns usage…
        *([{"role": "content-columns", "concept_count": 3}] * 6),
        # …then one title slide. It must still pick a title layout.
        {"role": "title-primary", "concept_count": 1},
    ])
    assert out[-1]["layout"] in {"title-orange", "title-ink", "action-title"}, (
        f"title slide picked a non-title layout: {out[-1]['layout']}"
    )
