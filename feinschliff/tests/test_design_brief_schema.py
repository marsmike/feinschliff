"""Unit tests for the design-brief JSON schema validator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FEINSCHLIFF_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = FEINSCHLIFF_ROOT / "skills/deck/lib/design_brief.schema.json"


@pytest.fixture(scope="module")
def validate_brief():
    """Import the validator from the skill's lib directory."""
    import sys
    sys.path.insert(0, str(FEINSCHLIFF_ROOT / "skills/deck/lib"))
    from design_brief import validate_brief as vb
    return vb


@pytest.fixture
def valid_brief() -> dict:
    """A canonical valid design brief."""
    return {
        "$schema": "feinschliff/design-brief/v1",
        "takeaway": "Polish time collapsed from 3 hrs to 15 min per deck",
        "audience": "exec",
        "audience_notes": "Time-poor, outcomes-driven; will stop after 30s of buildup.",
        "frame": "sparkline",
        "frame_rationale": "Vision pitch oscillating pain and future; PSSR rejected — no discrete search phase.",
        "hook": {
            "technique": "contrast",
            "opener": "Five years ago this took a week. Today it takes 15 minutes.",
        },
        "red_line": "Pain → Solution demo → Results → What this unlocks.",
        "slides": [
            {
                "index": 0,
                "role": "hook",
                "claim": "Polish time has collapsed — here's why that matters.",
                "audience_fit": "Lead with impact; skip architecture for exec.",
            }
        ],
    }


def test_schema_file_exists():
    assert SCHEMA_PATH.exists(), f"Schema missing at {SCHEMA_PATH}"


def test_schema_is_valid_json():
    with SCHEMA_PATH.open() as fp:
        json.load(fp)


def test_valid_brief_passes(validate_brief, valid_brief):
    errors = validate_brief(valid_brief)
    assert errors == [], f"Expected valid brief to pass, got errors: {errors}"


def test_missing_required_field_fails(validate_brief, valid_brief):
    del valid_brief["takeaway"]
    errors = validate_brief(valid_brief)
    assert errors, "Expected validator to reject brief missing 'takeaway'"
    assert any("takeaway" in err for err in errors)


def test_invalid_audience_enum_fails(validate_brief, valid_brief):
    valid_brief["audience"] = "board"  # not in enum
    errors = validate_brief(valid_brief)
    assert errors, "Expected validator to reject unknown audience"


def test_invalid_frame_enum_fails(validate_brief, valid_brief):
    valid_brief["frame"] = "hero-journey"  # not in v1 enum
    errors = validate_brief(valid_brief)
    assert errors


def test_invalid_slide_role_fails(validate_brief, valid_brief):
    valid_brief["slides"][0]["role"] = "intro"  # not in enum
    errors = validate_brief(valid_brief)
    assert errors


def test_empty_slides_fails(validate_brief, valid_brief):
    valid_brief["slides"] = []
    errors = validate_brief(valid_brief)
    assert errors
