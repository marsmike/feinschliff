"""Unit tests for lib/layout_picker — covering Phase 3's new signal kwargs.

The picker had no tests before this phase. We pin the existing public
contract (5 legacy kwargs) and assert the three new ones (narrative_act,
time_axis_role, audience_mode) are accepted without crashing and don't
change scoring for existing layouts.
"""
from __future__ import annotations

from feinschliff.layout_picker import pick_layout


def test_pick_layout_accepts_legacy_kwargs():
    """Sanity: the 5 legacy kwargs still work."""
    candidates = pick_layout(
        role="data-quantity", concept_count=3, data_quantity=3,
        comparison=False, narrative_role="evidence", top_k=3,
    )
    assert isinstance(candidates, list)
    assert candidates  # kpi-grid or similar should match


def test_pick_layout_accepts_narrative_act():
    """narrative_act kwarg accepted, doesn't crash."""
    candidates = pick_layout(
        role="data-quantity", concept_count=3,
        narrative_act="complication", top_k=3,
    )
    assert isinstance(candidates, list)


def test_pick_layout_accepts_time_axis_role():
    """time_axis_role kwarg accepted, doesn't crash."""
    candidates = pick_layout(
        role="data-timeline", concept_count=4,
        time_axis_role="strategic", top_k=3,
    )
    assert isinstance(candidates, list)


def test_pick_layout_accepts_audience_mode():
    """audience_mode kwarg accepted, doesn't crash."""
    candidates = pick_layout(
        role="data-quantity", concept_count=3,
        audience_mode="discussion", top_k=3,
    )
    assert isinstance(candidates, list)


def test_pick_layout_new_signals_dont_change_legacy_layout_scoring():
    """Legacy invariant: for layouts that don't declare Phase 4 affinity
    fields (narrative_role / narrative_act / time_axis_role), passing
    those signals doesn't change their individual scores. Phase 4
    layouts can re-shuffle the top-K (that's the point), but a legacy
    layout's own score must be deterministic w.r.t. legacy-only kwargs.
    """
    from feinschliff.layout_picker import _default_profile_table, _PHASE4_LAYOUTS
    _LAYOUTS = _default_profile_table()

    base = pick_layout(role="data-quantity", concept_count=3, top_k=len(_LAYOUTS))
    with_new = pick_layout(
        role="data-quantity", concept_count=3,
        narrative_act="resolution", time_axis_role="strategic",
        top_k=len(_LAYOUTS),
    )
    base_scores = {c["layout"]: c["score"] for c in base}
    new_scores = {c["layout"]: c["score"] for c in with_new}
    for layout_id in base_scores:
        if layout_id in _PHASE4_LAYOUTS:
            continue
        # Legacy layout: score must be unchanged.
        assert layout_id in new_scores, (
            f"legacy {layout_id} dropped out — would be a regression"
        )
        assert base_scores[layout_id] == new_scores[layout_id], (
            f"legacy {layout_id} score changed: "
            f"{base_scores[layout_id]} → {new_scores[layout_id]}"
        )


def test_pick_layout_rejects_unknown_kwarg():
    """Defensive: a typo or future-leaning kwarg surfaces as TypeError,
    not a silent ignore."""
    import pytest
    with pytest.raises(TypeError):
        pick_layout(role="data-quantity", concept_count=3,
                    nonsense_kwarg="x", top_k=3)


def test_pick_layout_rejects_invalid_narrative_act():
    """Typos in narrative_act surface as ValueError, not silent acceptance."""
    import pytest
    with pytest.raises(ValueError, match="narrative_act"):
        pick_layout(role="data-quantity", concept_count=3,
                    narrative_act="complicaiton")


def test_pick_layout_rejects_invalid_time_axis_role():
    """Typos in time_axis_role surface as ValueError."""
    import pytest
    with pytest.raises(ValueError, match="time_axis_role"):
        pick_layout(role="data-quantity", concept_count=3,
                    time_axis_role="stragetic")


def test_pick_layout_rejects_invalid_audience_mode():
    """Typos in audience_mode surface as ValueError."""
    import pytest
    with pytest.raises(ValueError, match="audience_mode"):
        pick_layout(role="data-quantity", concept_count=3,
                    audience_mode="presenter")


def test_pick_layout_accepts_valid_enum_values():
    """All valid enum values pass validation."""
    for act in ("situation", "complication", "resolution"):
        pick_layout(role="data-quantity", concept_count=3, narrative_act=act)
    for role in ("strategic", "chronological", "tactical"):
        pick_layout(role="data-quantity", concept_count=3, time_axis_role=role)
    for mode in ("presentation", "discussion"):
        pick_layout(role="data-quantity", concept_count=3, audience_mode=mode)


# --- Phase 4 layout routing (PR A wiring) -----------------------------
# Each new layout has a target picker fingerprint. The test asserts the
# matching fingerprint causes that layout to dominate — top candidate by
# score among all 38 entries in `_LAYOUTS`.


def test_recommendation_layout_picked_by_fingerprint():
    """narrative_role=recommendation + narrative_act=resolution +
    concept_count in 2-3 (Pyramid arity) → `recommendation`."""
    candidates = pick_layout(
        role="content-columns", concept_count=3,
        narrative_role="recommendation", narrative_act="resolution",
        top_k=3,
    )
    assert candidates[0]["layout"] == "recommendation", candidates


def test_next_steps_layout_picked_by_fingerprint():
    """narrative_role=close-action + concept_count in 3-7 → `next-steps`."""
    candidates = pick_layout(
        role="closer", concept_count=5,
        narrative_role="close-action", narrative_act="resolution",
        top_k=3,
    )
    assert candidates[0]["layout"] == "next-steps", candidates


def test_risk_register_layout_picked_by_fingerprint():
    """narrative_role=risk + tabular detail (data_quantity high, count 4-8)
    → `risk-register`."""
    candidates = pick_layout(
        role="reference", concept_count=6, data_quantity=18,
        narrative_role="risk",
        top_k=3,
    )
    assert candidates[0]["layout"] == "risk-register", candidates


def test_risk_matrix_layout_picked_by_fingerprint():
    """narrative_role=risk + comparison (2-axis P×I grid) + count 4-10
    → `risk-matrix`."""
    candidates = pick_layout(
        role="data-comparison", concept_count=6, comparison=True,
        narrative_role="risk",
        top_k=3,
    )
    assert candidates[0]["layout"] == "risk-matrix", candidates


def test_roadmap_layout_picked_by_fingerprint():
    """narrative_role=plan + time_axis_role=strategic + comparison
    (parallel-time workstreams) → `roadmap`."""
    candidates = pick_layout(
        role="data-timeline", concept_count=5, comparison=True,
        narrative_role="plan", time_axis_role="strategic",
        top_k=3,
    )
    assert candidates[0]["layout"] == "roadmap", candidates


def test_timeline_layout_picked_by_fingerprint():
    """narrative_role=history + time_axis_role=chronological → `timeline`."""
    candidates = pick_layout(
        role="data-timeline", concept_count=5,
        narrative_role="history", time_axis_role="chronological",
        top_k=3,
    )
    assert candidates[0]["layout"] == "timeline", candidates


# --- Audience mode (sparser/denser) -----------------------------------


def test_audience_mode_influences_scoring():
    """audience_mode=presentation vs =discussion must produce *some*
    measurable score difference for a layout whose ideal_count range
    is wide enough to differentiate (e.g. key-takeaways 2-4 with
    concept_count=2 is the sparser end)."""
    sparser = pick_layout(
        role="closer", concept_count=2,
        audience_mode="presentation", top_k=5,
    )
    denser = pick_layout(
        role="closer", concept_count=2,
        audience_mode="discussion", top_k=5,
    )
    # find key-takeaways in both
    def _score_of(cands, layout_id):
        for c in cands:
            if c["layout"] == layout_id:
                return c["score"]
        return None

    sparser_score = _score_of(sparser, "key-takeaways")
    denser_score = _score_of(denser, "key-takeaways")
    # cc=2 is at the low end of key-takeaways' (2,4) — presentation
    # should bonus it; discussion should not.
    assert sparser_score is not None
    assert denser_score is not None
    assert sparser_score > denser_score, (
        f"presentation should bonus the sparser end of key-takeaways "
        f"(cc=2, range 2-4); got presentation={sparser_score}, "
        f"discussion={denser_score}"
    )


def test_audience_mode_neutral_when_no_concept_count():
    """When concept_count is None, audience_mode has nothing to key
    against — no score effect, no crash."""
    no_mode = pick_layout(role="closer", top_k=5)
    presentation = pick_layout(
        role="closer", audience_mode="presentation", top_k=5,
    )
    # Same layouts, same scores — audience_mode is inert without cc.
    assert [c["layout"] for c in no_mode] == [c["layout"] for c in presentation]
    assert [c["score"] for c in no_mode] == [c["score"] for c in presentation]


# --- layout_history variety penalty ------------------------------------------


def test_layout_history_accepted_without_crash():
    """layout_history kwarg is accepted and does not raise."""
    candidates = pick_layout(
        role="content-columns", concept_count=3,
        layout_history=["bar-chart", "two-column-cards"],
        top_k=3,
    )
    assert isinstance(candidates, list)


def test_layout_history_penalises_last_used_layout():
    """The most-recently-used layout scores lower than without history."""
    baseline = pick_layout(role="content-columns", concept_count=3, top_k=10)
    with_history = pick_layout(
        role="content-columns", concept_count=3,
        layout_history=["two-column-cards"],
        top_k=10,
    )

    def _score_of(cands, layout_id):
        for c in cands:
            if c["layout"] == layout_id:
                return c["score"]
        return None

    base_score = _score_of(baseline, "two-column-cards")
    penalised_score = _score_of(with_history, "two-column-cards")

    # two-column-cards must appear in both result sets to be comparable.
    if base_score is not None and penalised_score is not None:
        assert penalised_score < base_score, (
            f"Expected variety penalty to lower score: "
            f"baseline={base_score}, penalised={penalised_score}"
        )


def test_layout_history_penalises_second_to_last():
    """The second-to-last layout also gets a smaller penalty."""
    baseline = pick_layout(role="content-columns", concept_count=3, top_k=10)
    with_history = pick_layout(
        role="content-columns", concept_count=3,
        layout_history=["two-column-cards", "three-column"],
        top_k=10,
    )

    def _score_of(cands, layout_id):
        for c in cands:
            if c["layout"] == layout_id:
                return c["score"]
        return None

    base_two = _score_of(baseline, "two-column-cards")
    hist_two = _score_of(with_history, "two-column-cards")
    base_three = _score_of(baseline, "three-column")
    hist_three = _score_of(with_history, "three-column")

    # second-to-last (two-column-cards, index -2) gets a smaller penalty
    # than last (three-column, index -1).
    if base_three is not None and hist_three is not None:
        assert hist_three < base_three, "last layout should be penalised"
    if base_two is not None and hist_two is not None:
        assert hist_two < base_two, "second-to-last layout should also be penalised"
    # last layout gets a bigger penalty than second-to-last
    if hist_three is not None and hist_two is not None and base_three is not None and base_two is not None:
        penalty_last = base_three - hist_three
        penalty_prev = base_two - hist_two
        assert penalty_last > penalty_prev, (
            f"last ({penalty_last:.2f}) should exceed second-to-last penalty ({penalty_prev:.2f})"
        )


def test_layout_history_empty_list_is_neutral():
    """An empty history list must not change scoring."""
    no_hist = pick_layout(role="content-columns", concept_count=3, top_k=5)
    empty_hist = pick_layout(
        role="content-columns", concept_count=3,
        layout_history=[],
        top_k=5,
    )
    assert [c["layout"] for c in no_hist] == [c["layout"] for c in empty_hist]
    assert [c["score"] for c in no_hist] == [c["score"] for c in empty_hist]


def test_layout_history_structural_layouts_exempt():
    """Title slides, chapter openers, agenda, and end are never penalised."""
    from feinschliff.layout_picker import _VARIETY_EXEMPT
    for exempt_id in _VARIETY_EXEMPT:
        # Construct a request where the exempt layout would normally score well.
        base = pick_layout(top_k=20)
        with_hist = pick_layout(layout_history=[exempt_id], top_k=20)

        def _score_of(cands, lid):
            for c in cands:
                if c["layout"] == lid:
                    return c["score"]
            return None

        base_score = _score_of(base, exempt_id)
        hist_score = _score_of(with_hist, exempt_id)
        # Score must be unchanged (exempt from penalty).
        if base_score is not None and hist_score is not None:
            assert base_score == hist_score, (
                f"{exempt_id!r} is in _VARIETY_EXEMPT but its score changed: "
                f"{base_score} → {hist_score}"
            )


# --- four-column-cards role fix -----------------------------------------------


def test_four_column_cards_role_is_content_columns():
    """four-column-cards serves 4-pillar content, not timelines.
    It must be classified as content-columns, not data-timeline."""
    from feinschliff.layout_picker import _default_profile_table
    profile = _default_profile_table()["four-column-cards"]
    assert profile["role"] == "content-columns", (
        f"four-column-cards role should be content-columns, got {profile['role']!r}"
    )


def test_four_column_cards_is_not_comparative():
    """four-column-cards shows 4 parallel items, not head-to-head comparisons.
    comp flag should be False."""
    from feinschliff.layout_picker import _default_profile_table
    profile = _default_profile_table()["four-column-cards"]
    assert profile["comp"] is False, (
        "four-column-cards comp flag should be False"
    )


def test_four_column_cards_picked_for_content_columns_role():
    """With role=content-columns and concept_count=4, four-column-cards
    should be a top candidate."""
    candidates = pick_layout(
        role="content-columns", concept_count=4, top_k=3,
    )
    layout_ids = [c["layout"] for c in candidates]
    assert "four-column-cards" in layout_ids, (
        f"four-column-cards should be a top-3 candidate for role=content-columns, "
        f"count=4; got {layout_ids}"
    )


# --- Slice 1: narrative_act wired to toolkit layouts + diagram_complexity ----


def test_key_takeaways_scores_higher_with_resolution_act():
    """key-takeaways declares narrative_act=resolution. Passing that signal
    must yield a +1 bonus over the same call without it. Uses role=closer
    to match key-takeaways' declared role (so the role bonus is identical
    in both calls and cannot mask the act delta)."""
    from feinschliff.layout_picker import _default_profile_table
    all_layouts = _default_profile_table()
    top_k = len(all_layouts)

    without_act = pick_layout(role="closer", concept_count=3, top_k=top_k)
    with_act    = pick_layout(role="closer", concept_count=3,
                              narrative_act="resolution", top_k=top_k)

    def _score(cands, layout_id):
        for c in cands:
            if c["layout"] == layout_id:
                return c["score"]
        return None

    base  = _score(without_act, "key-takeaways")
    bonus = _score(with_act,    "key-takeaways")
    assert base  is not None, "key-takeaways must appear in full candidate list"
    assert bonus is not None, "key-takeaways must appear in full candidate list"
    assert bonus == base + 1, (
        f"key-takeaways should gain exactly +1 from narrative_act=resolution; "
        f"got base={base}, with_act={bonus}"
    )


def test_signals_from_slide_extracts_diagram_complexity():
    """signals_from_slide must pass diagram_complexity through from the
    content-plan slide dict so the picker can consume it."""
    from feinschliff.deck.orchestrate import signals_from_slide

    signals = signals_from_slide({
        "role": "concept-diagram",
        "diagram_complexity": "deep",
    })
    assert signals["diagram_complexity"] == "deep", (
        f"expected diagram_complexity='deep', got {signals.get('diagram_complexity')!r}"
    )
    # Absent field must not raise — returns None.
    assert signals_from_slide({"role": "concept-diagram"})["diagram_complexity"] is None


def test_plan_deck_layouts_passes_diagram_complexity_to_picker():
    """diagram_complexity in slide signals must flow through plan_deck_layouts
    to pick_layout and influence the winner. A 'deep' signal favours
    excalidraw-diagram-full over the narrower excalidraw-diagram."""
    from feinschliff.layout_budget import plan_deck_layouts

    # Without diagram_complexity the narrow layout can win; with deep it
    # should not — excalidraw-diagram-full (diagram_complexity=deep) should
    # score higher.
    deep_signal = {
        "role": "concept-diagram",
        "concept_count": 12,   # above the narrow layout's 8-node ceiling
        "diagram_complexity": "deep",
    }
    out = plan_deck_layouts([deep_signal])
    assert out[0]["layout"] == "excalidraw-diagram-full", (
        f"diagram_complexity=deep with high concept_count should prefer "
        f"excalidraw-diagram-full; got {out[0]['layout']}"
    )
