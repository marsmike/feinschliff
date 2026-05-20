"""Unit tests for lib/verify/deck/non_mece — non-mece-breakdown defect."""
from __future__ import annotations

from feinschliff_builder.verify.deck.defects import DeckDefect
from feinschliff_builder.verify.deck.non_mece import check_non_mece


def test_empty_list_is_clean():
    """No items → nothing to check, no defect."""
    assert check_non_mece([]) == []


def test_items_summing_to_100_are_clean():
    """Exact 100% sum → no defect."""
    items = [{"value": 50}, {"value": 30}, {"value": 20}]
    assert check_non_mece(items) == []


def test_within_tolerance_is_clean():
    """98% sum is within the ±2pp tolerance band → no defect."""
    items = [{"value": 50}, {"value": 30}, {"value": 18}]
    assert check_non_mece(items) == []


def test_undershoot_outside_tolerance_fires():
    """95% sum is outside tolerance → 1 defect that names the total."""
    items = [{"value": 50}, {"value": 30}, {"value": 15}]
    defects = check_non_mece(items, slide_index=4)
    assert len(defects) == 1
    d = defects[0]
    assert isinstance(d, DeckDefect)
    assert d.kind == "non-mece-breakdown"
    assert d.slide_index == 4
    assert "95" in d.message
    assert d.suggestion  # non-empty


def test_overshoot_outside_tolerance_fires():
    """110% sum → 1 defect (overshoot)."""
    items = [{"value": 60}, {"value": 30}, {"value": 20}]
    defects = check_non_mece(items)
    assert len(defects) == 1
    assert defects[0].kind == "non-mece-breakdown"
    assert "110" in defects[0].message


def test_non_numeric_items_are_clean():
    """Strings, or dicts without value/percentage, are LLM territory → []."""
    assert check_non_mece(["Enterprise", "Mid-market", "Customer churn"]) == []
    assert check_non_mece([{"label": "A"}, {"label": "B"}]) == []


def test_mixed_numeric_and_non_numeric_only_counts_numeric():
    """Items without numeric fields are skipped; only numeric ones sum."""
    items = [
        {"label": "Enterprise", "value": 60},
        {"label": "Mid-market", "value": 35},
        "Customer churn",          # bare string — ignored
        {"label": "Other"},         # dict, no value — ignored
    ]
    # Numeric total is 95 → outside tolerance → defect.
    defects = check_non_mece(items)
    assert len(defects) == 1
    assert defects[0].kind == "non-mece-breakdown"
    assert "95" in defects[0].message


def test_percentage_field_also_handled():
    """Items with `percentage` instead of `value` are equally counted."""
    items = [{"percentage": 50}, {"percentage": 30}, {"percentage": 15}]
    defects = check_non_mece(items)
    assert len(defects) == 1
    assert defects[0].kind == "non-mece-breakdown"
    # And the clean case with percentage:
    assert check_non_mece(
        [{"percentage": 50}, {"percentage": 30}, {"percentage": 20}]
    ) == []
