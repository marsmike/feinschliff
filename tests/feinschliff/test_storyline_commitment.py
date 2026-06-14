"""Tests for commitment-document loading, saving, and arc alignment."""
from __future__ import annotations

from feinschliff.storyline import (
    check_arc_alignment,
    load_commitment,
    save_commitment,
    validate_commitment,
)
from feinschliff.storyline.schema import load_arc
from pathlib import Path


_PITCH_COMMITMENT = {
    "deck_type": "pitch",
    "thesis": "B2B prompt engineering has moved from product to ops layer.",
    "key_moves": [
        "Show the shift: prompt work is now a major ops burden.",
        "Raise the stakes: AEs bear unscoped work; quotas suffer.",
        "Name the promised land: a world where prompt ops is automated.",
        "Present features as magic: our platform as the path.",
        "Provide proof: three Fortune-500 customers.",
        "Make the ask: 30-min pilot scoping call.",
    ],
    "evidence_anchors": [
        {
            "claim": "Prompt work is 20% of GTM hours",
            "source": "Internal time-tracking study, Apr 2026",
        }
    ],
    "arc_check": "pass",
}


def test_commitment_round_trip(tmp_path: Path) -> None:
    dest = tmp_path / "commitment.yaml"
    save_commitment(_PITCH_COMMITMENT, dest)
    loaded = load_commitment(dest)
    assert loaded == _PITCH_COMMITMENT


def test_commitment_missing_thesis_fails() -> None:
    bad = {k: v for k, v in _PITCH_COMMITMENT.items() if k != "thesis"}
    errors = validate_commitment(bad)
    assert errors, "Expected errors when 'thesis' is missing"
    assert any("thesis" in e for e in errors)


def test_check_arc_alignment_pass() -> None:
    arcs_dir = Path(__file__).parent.parent.parent / "feinschliff" / "feinschliff" / "storyline" / "arcs"
    pitch_arc = load_arc(arcs_dir / "pitch.yaml")
    errors = check_arc_alignment(_PITCH_COMMITMENT, pitch_arc)
    assert errors == [], f"Expected no alignment errors, got: {errors}"


def test_check_arc_alignment_missing_required_act() -> None:
    arcs_dir = Path(__file__).parent.parent.parent / "feinschliff" / "feinschliff" / "storyline" / "arcs"
    pitch_arc = load_arc(arcs_dir / "pitch.yaml")
    # Remove any key_move that mentions "ask"
    commitment_no_ask = {
        **_PITCH_COMMITMENT,
        "key_moves": [
            km for km in _PITCH_COMMITMENT["key_moves"]
            if "ask" not in km.lower()
        ],
    }
    errors = check_arc_alignment(commitment_no_ask, pitch_arc)
    assert errors, "Expected alignment error for missing 'ask' act"
    assert any("ask" in e for e in errors)
