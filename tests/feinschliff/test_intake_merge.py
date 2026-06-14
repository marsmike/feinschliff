"""Tests for merge_with_answers."""
from __future__ import annotations

import pytest

from feinschliff.intake import merge_with_answers

_VALID_BASE = {
    "schema_version": 1,
    "goal": "status",
    "audience": "exec",
    "deck_type": "status-update",
}


def test_merge_answers_overrides_base():
    answers = {"goal": "decision", "deck_type": "pitch"}
    result = merge_with_answers(_VALID_BASE, answers)
    assert result["goal"] == "decision"
    assert result["deck_type"] == "pitch"


def test_merge_validates_result():
    # answers produces an invalid enum value
    with pytest.raises(ValueError):
        merge_with_answers(_VALID_BASE, {"audience": "not-a-real-audience"})


def test_merge_with_constraints_keeps_known_extras():
    base = {**_VALID_BASE, "constraints": {"time_to_present_min": 10, "no_charts": False}}
    answers = {"constraints": {"time_to_present_min": 20, "future_field": "ok"}}
    result = merge_with_answers(base, answers)
    assert result["constraints"]["time_to_present_min"] == 20
    assert result["constraints"]["no_charts"] is False
    assert result["constraints"]["future_field"] == "ok"
