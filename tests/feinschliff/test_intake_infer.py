"""Tests for the deck brief heuristic inference."""
from __future__ import annotations

from feinschliff.intake import infer_from_text


def test_infer_pitch_from_investors_text():
    result = infer_from_text("Series A pitch to acme partners")
    assert result.get("deck_type") == "pitch"


def test_infer_status_from_quarterly():
    result = infer_from_text("Q1 2026 update for the leadership team")
    assert result.get("goal") == "status"
    assert result.get("deck_type") == "status-update"
    assert result.get("audience") == "exec"


def test_infer_length_short_from_short_brief():
    short_text = "Quick status update." * 5  # well under 300 chars
    assert len(short_text) <= 300
    result = infer_from_text(short_text)
    assert result.get("length_hint") == "short"


def test_infer_returns_only_confident_fields():
    result = infer_from_text("We need a deck")
    # no strong signal — only length_hint is set
    assert set(result.keys()) <= {"length_hint"}


def test_infer_last_match_wins():
    # "training" fires first, then "pitch" overrides deck_type
    result = infer_from_text("This started as a training but is now a pitch to investors")
    assert result.get("deck_type") == "pitch"
