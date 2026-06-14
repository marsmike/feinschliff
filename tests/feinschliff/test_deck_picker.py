"""Tests for lib.deck.picker — LayoutPicker / LayoutMatch."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from feinschliff.deck.picker import LayoutMatch, LayoutPicker


# ── helpers / fixtures ────────────────────────────────────────────────────────

def _mock_brand(*layout_names: str):
    """Return a BrandPack mock that resolves the given layout names."""
    brand = MagicMock()
    found_map = {}
    for name in layout_names:
        found = MagicMock()
        found.path = Path(f"/fake/layouts/{name}.slide.dsl")
        found_map[name] = found

    def _find_layout(name):
        return found_map.get(name)

    brand.find_layout.side_effect = _find_layout
    # Ranking now reads the brand's full layout universe; use the real
    # discovered toolkit profiles so candidates score, while path
    # resolution still goes through the mocked find_layout above.
    from feinschliff.layout_discovery import discover_layout_paths
    brand.layout_table.return_value = dict(discover_layout_paths())
    return brand


# ── LayoutMatch ───────────────────────────────────────────────────────────────

def test_layout_match_is_frozen():
    m = LayoutMatch(
        layout_name="title-orange",
        layout_path=None,
        score=3.0,
        reason="role",
    )
    with pytest.raises((AttributeError, TypeError)):
        m.score = 99.0  # type: ignore[misc]


def test_layout_match_fields():
    p = Path("/some/layout.dsl")
    m = LayoutMatch(layout_name="agenda", layout_path=p, score=5.0, reason="role, count=3")
    assert m.layout_name == "agenda"
    assert m.layout_path == p
    assert m.score == 5.0
    assert "role" in m.reason


# ── LayoutPicker.candidates ───────────────────────────────────────────────────

def test_candidates_returns_list_of_layout_matches():
    picker = LayoutPicker()
    result = picker.candidates({"role": "content-columns", "concept_count": 3})
    assert isinstance(result, list)
    assert all(isinstance(c, LayoutMatch) for c in result)


def test_candidates_respects_top_k():
    picker = LayoutPicker(top_k=2)
    result = picker.candidates({"role": "content-columns", "concept_count": 3})
    assert len(result) <= 2


def test_candidates_top_k_override():
    picker = LayoutPicker(top_k=3)
    result = picker.candidates({"role": "content-columns", "concept_count": 3}, top_k=1)
    assert len(result) <= 1


def test_candidates_known_role_returns_expected_top():
    """Asking for role=title-primary should rank title layouts first."""
    picker = LayoutPicker(top_k=1)
    result = picker.candidates({"role": "title-primary"})
    assert result
    assert "title" in result[0].layout_name


def test_candidates_data_timeline_role():
    picker = LayoutPicker(top_k=1)
    result = picker.candidates({"role": "data-timeline", "concept_count": 4})
    assert result
    top_name = result[0].layout_name
    assert top_name in (
        "process-flow", "line-chart", "gantt", "roadmap", "timeline", "waterfall"
    )


def test_candidates_empty_signals_no_crash():
    """All-None signals should not raise."""
    picker = LayoutPicker(top_k=3)
    result = picker.candidates({})
    assert isinstance(result, list)


def test_candidates_ordering_by_score():
    picker = LayoutPicker(top_k=3)
    result = picker.candidates({"role": "content-columns", "concept_count": 3})
    if len(result) >= 2:
        assert result[0].score >= result[1].score


def test_candidates_with_brand_resolves_path():
    # Include all possible top-3 picks for content-columns/concept_count=3
    brand = _mock_brand(
        "three-column", "two-column-cards", "horizontal-bullets",
        "vertical-bullets", "pyramid", "executive-summary",
    )
    picker = LayoutPicker(brand=brand, top_k=3)
    result = picker.candidates({"role": "content-columns", "concept_count": 3})
    # At least one candidate should have a resolved path
    assert any(c.layout_path is not None for c in result)


def test_candidates_without_brand_has_none_paths():
    picker = LayoutPicker(brand=None, top_k=3)
    result = picker.candidates({"role": "content-columns", "concept_count": 3})
    assert all(c.layout_path is None for c in result)


# ── LayoutPicker.pick ─────────────────────────────────────────────────────────

def test_pick_returns_single_layout_match():
    picker = LayoutPicker()
    match = picker.pick({"role": "title-primary"})
    assert isinstance(match, LayoutMatch)
    assert "title" in match.layout_name


def test_pick_returns_best_for_data_timeline():
    picker = LayoutPicker()
    match = picker.pick({"role": "data-timeline", "concept_count": 4})
    assert isinstance(match, LayoutMatch)
    assert match.score > 0


def test_pick_raises_for_no_matching_layout():
    """When pick_layout returns empty, pick() must raise ValueError."""
    import feinschliff.deck.picker as _mod
    from unittest.mock import patch as _patch
    with _patch.object(_mod, "pick_layout", return_value=[]):
        with pytest.raises(ValueError, match="no layout matched"):
            LayoutPicker().pick({"role": "nonexistent-role-xyz"})


def test_pick_narrative_act_signal():
    """resolution narrative_act should steer toward resolution-affinity layouts."""
    picker = LayoutPicker(top_k=3)
    result = picker.candidates({
        "role": "closer",
        "narrative_act": "resolution",
        "concept_count": 4,
    })
    assert result
    names = [c.layout_name for c in result]
    assert any(n in ("next-steps", "recommendation", "key-takeaways") for n in names)


def test_pick_variety_penalty():
    """Recently-used layout should score lower than an unpenalised baseline."""
    picker = LayoutPicker(top_k=3)
    base = picker.candidates({"role": "content-columns", "concept_count": 3})
    top_without = base[0].layout_name if base else None

    if top_without:
        biased = picker.candidates({
            "role": "content-columns",
            "concept_count": 3,
            "layout_history": [top_without],
        })
        if biased and biased[0].layout_name == top_without:
            assert biased[0].score <= base[0].score


def test_candidates_reason_is_string():
    picker = LayoutPicker(top_k=3)
    result = picker.candidates({"role": "content-columns", "concept_count": 3})
    for c in result:
        assert isinstance(c.reason, str)
