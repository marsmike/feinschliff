"""Tests for the deck_brief JSON schema and loader round-trip."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from feinschliff.intake import load_brief, save_brief, validate_brief

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "feinschliff" / "intake" / "deck_brief.schema.json"

_MINIMAL = {
    "schema_version": 1,
    "goal": "decision",
    "audience": "exec",
    "deck_type": "pitch",
}


def test_schema_file_exists():
    assert _SCHEMA_PATH.exists()
    data = json.loads(_SCHEMA_PATH.read_text())
    assert isinstance(data, dict)


def test_minimal_brief_passes():
    errors = validate_brief(_MINIMAL)
    assert errors == []


def test_missing_required_fails():
    brief = {k: v for k, v in _MINIMAL.items() if k != "goal"}
    errors = validate_brief(brief)
    assert any("goal" in e for e in errors)


def test_invalid_enum_fails():
    brief = {**_MINIMAL, "audience": "C-suite"}
    errors = validate_brief(brief)
    assert errors


def test_extra_top_level_field_fails():
    brief = {**_MINIMAL, "foo": "bar"}
    errors = validate_brief(brief)
    assert errors


def test_constraints_allows_extra():
    brief = {
        **_MINIMAL,
        "constraints": {"time_to_present_min": 15, "future_field": "ok"},
    }
    errors = validate_brief(brief)
    assert errors == []


def test_save_then_load_roundtrip():
    brief = {**_MINIMAL, "length_hint": "short", "tone": "formal"}
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        path = Path(f.name)
    try:
        save_brief(brief, path)
        loaded = load_brief(path)
        assert loaded == brief
    finally:
        path.unlink(missing_ok=True)


def test_save_invalid_raises():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        path = Path(f.name)
    try:
        with pytest.raises(ValueError):
            save_brief({"schema_version": 1, "goal": "bad-value"}, path)
    finally:
        path.unlink(missing_ok=True)
