"""Unit tests for verify/deck/narrative_arc — narrative-arc-missing defect.

Canonical location: feinschliff/tests/ (implementation in feinschliff core).
"""
from __future__ import annotations

from feinschliff.verify.deck.narrative_arc import check_narrative_arc
from feinschliff.verify.deck.defects import DeckDefect


def test_full_scr_arc_is_clean():
    """Situation + Complication + Resolution → no defect."""
    defects = check_narrative_arc(["situation", "complication", "resolution"])
    assert defects == []


def test_missing_complication_with_s_and_r_fires():
    """Situation + Resolution but no Complication → defect."""
    defects = check_narrative_arc(["situation", "resolution"])
    assert len(defects) == 1
    assert defects[0].kind == "narrative-arc-missing"
    assert defects[0].slide_index is None  # deck-level
    assert "complication" in defects[0].message.lower()
    assert defects[0].suggestion  # non-empty


def test_only_situation_is_clean():
    assert check_narrative_arc(["situation", "situation"]) == []


def test_only_resolution_is_clean():
    assert check_narrative_arc(["resolution", "resolution"]) == []


def test_complication_present_but_no_situation_is_clean():
    assert check_narrative_arc(["complication", "resolution"]) == []


def test_empty_list_is_clean():
    assert check_narrative_arc([]) == []


def test_unknown_values_ignored():
    defects = check_narrative_arc(
        ["context", "situation", "evidence", "resolution"]
    )
    assert len(defects) == 1
    assert defects[0].kind == "narrative-arc-missing"


def test_returns_deck_defect_instances():
    defects = check_narrative_arc(["situation", "resolution"])
    assert all(isinstance(d, DeckDefect) for d in defects)
