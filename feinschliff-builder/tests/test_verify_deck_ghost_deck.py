"""Tests for verify/deck/ghost_deck.py — ghost-deck title-strip check."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


TITLES_GOOD = ["Hook: the world is changing", "Three forces drive this shift", "We must act now"]


# ---------------------------------------------------------------------------
# Unit: judge_ghost_deck — offline mode
# ---------------------------------------------------------------------------

def test_offline_returns_pass():
    from feinschliff_builder.verify.deck.ghost_deck import judge_ghost_deck

    result = judge_ghost_deck(titles=["Hook", "Body", "Ask"], offline=True)
    assert result.verdict == "pass"
    assert result.issues == []
    assert result.titles == ["Hook", "Body", "Ask"]


# ---------------------------------------------------------------------------
# Unit: judge_ghost_deck — online mode (monkeypatched)
# ---------------------------------------------------------------------------

def test_judge_invokes_judge_helper():
    from feinschliff_builder.verify.deck import ghost_deck as gd_mod

    mock_response = {
        "verdict": "warn",
        "issues": [{"slide": 2, "issue": "Gap in logic", "suggested": "Add a bridge slide"}],
    }

    with patch.object(gd_mod, "_judge", return_value=mock_response) as mock:
        result = gd_mod.judge_ghost_deck(TITLES_GOOD, offline=False)

    assert mock.call_count == 1
    assert result.verdict == "warn"
    assert len(result.issues) == 1
    assert result.issues[0]["slide"] == 2
    assert result.titles == TITLES_GOOD


def test_judge_clean_verdict():
    from feinschliff_builder.verify.deck import ghost_deck as gd_mod

    mock_response = {"verdict": "pass", "issues": []}

    with patch.object(gd_mod, "_judge", return_value=mock_response):
        result = gd_mod.judge_ghost_deck(TITLES_GOOD, offline=False)

    assert result.verdict == "pass"
    assert result.issues == []


def test_judge_fail_verdict():
    from feinschliff_builder.verify.deck import ghost_deck as gd_mod

    mock_response = {
        "verdict": "fail",
        "issues": [
            {"slide": 1, "issue": "Topic label — no verb", "suggested": "Add a claim"},
            {"slide": 3, "issue": "No conclusion", "suggested": "End with an ask"},
        ],
    }

    with patch.object(gd_mod, "_judge", return_value=mock_response):
        result = gd_mod.judge_ghost_deck(TITLES_GOOD, offline=False)

    assert result.verdict == "fail"
    assert len(result.issues) == 2


def test_judge_unknown_verdict_defaults_to_warn():
    from feinschliff_builder.verify.deck import ghost_deck as gd_mod

    mock_response = {"verdict": "maybe", "issues": []}

    with patch.object(gd_mod, "_judge", return_value=mock_response):
        result = gd_mod.judge_ghost_deck(TITLES_GOOD, offline=False)

    assert result.verdict == "warn"


# ---------------------------------------------------------------------------
# Unit: judge_ghost_deck — error sentinel
# ---------------------------------------------------------------------------

def test_judge_falls_back_on_error_sentinel():
    from feinschliff_builder.verify.deck import ghost_deck as gd_mod

    error_sentinel = {"status": "fail", "reason": "boom"}

    with patch.object(gd_mod, "_judge", return_value=error_sentinel):
        result = gd_mod.judge_ghost_deck(TITLES_GOOD, offline=False)

    assert result.verdict == "warn"
    assert len(result.issues) == 1
    assert "boom" in result.issues[0]["issue"]
    assert result.issues[0]["slide"] == 0


# ---------------------------------------------------------------------------
# Unit: write_ghost_deck_report
# ---------------------------------------------------------------------------

def test_write_report_includes_titles_and_issues(tmp_path: Path):
    from feinschliff_builder.verify.deck.ghost_deck import GhostDeckResult, write_ghost_deck_report

    result = GhostDeckResult(
        verdict="warn",
        issues=[
            {"slide": 3, "issue": "Logic gap between slide 2 and 3", "suggested": "Add a bridge"},
        ],
        titles=["Hook", "Body", "Ask"],
    )
    report_path = tmp_path / "ghost_deck_report.md"
    write_ghost_deck_report(result, report_path)

    body = report_path.read_text()
    assert "3 titles" in body
    assert "**Verdict:** warn" in body
    assert "1. Hook" in body
    assert "3. Ask" in body
    assert "Slide 3" in body
    assert "Logic gap between slide 2 and 3" in body
    assert "Add a bridge" in body


def test_write_report_pass_shows_no_issues(tmp_path: Path):
    from feinschliff_builder.verify.deck.ghost_deck import GhostDeckResult, write_ghost_deck_report

    result = GhostDeckResult(
        verdict="pass",
        issues=[],
        titles=["Hook", "Body", "Ask"],
    )
    report_path = tmp_path / "report.md"
    write_ghost_deck_report(result, report_path)
    body = report_path.read_text()
    assert "_No issues._" in body
    assert "**Verdict:** pass" in body


def test_write_report_creates_parent_dirs(tmp_path: Path):
    from feinschliff_builder.verify.deck.ghost_deck import GhostDeckResult, write_ghost_deck_report

    result = GhostDeckResult(verdict="pass", issues=[], titles=["A"])
    deep = tmp_path / "a" / "b" / "report.md"
    write_ghost_deck_report(result, deep)
    assert deep.exists()
