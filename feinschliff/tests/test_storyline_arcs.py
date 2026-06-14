"""Tests for arc-schema YAML loading and validation."""
from __future__ import annotations

from feinschliff.storyline import load_all_arcs, validate_arc


def test_all_9_arcs_load_and_validate() -> None:
    arcs = load_all_arcs()
    assert len(arcs) == 9, f"Expected 9 arc schemas, got {len(arcs)}: {sorted(arcs.keys())}"
    expected_types = {
        "pitch",
        "data-story",
        "proposal",
        "status-update",
        "training",
        "company-intro",
        "retrospective",
        "all-hands",
        "board-update",
    }
    assert set(arcs.keys()) == expected_types
    for deck_type, schema_dict in arcs.items():
        errors = validate_arc(schema_dict)
        assert errors == [], f"Arc '{deck_type}' failed validation: {errors}"


def test_arc_schema_rejects_unknown_position() -> None:
    bad_arc = {
        "deck_type": "test",
        "source": "Test source",
        "acts": [
            {
                "name": "intro",
                "desc": "An introduction.",
                "position": "front",  # not a valid position value
            }
        ],
    }
    errors = validate_arc(bad_arc)
    assert errors, "Expected validation errors for unknown position 'front'"
    assert any("front" in e or "position" in e for e in errors)


def test_arc_schema_requires_acts_nonempty() -> None:
    bad_arc = {
        "deck_type": "test",
        "source": "Test source",
        "acts": [],  # must have at least 1 item
    }
    errors = validate_arc(bad_arc)
    assert errors, "Expected validation errors for empty acts array"
