"""Unit tests for lib/verify/deck/storyline — contact sheet + report writer."""
from __future__ import annotations

from pathlib import Path

from lib.verify.deck.storyline import (
    render_contact_sheet,
    write_storyline_report,
)


def test_contact_sheet_minimal():
    """Two titles → numbered list with the heading."""
    md = render_contact_sheet(["Why now", "What changed"])
    assert "# Storyline contact sheet" in md
    assert "1. Why now" in md
    assert "2. What changed" in md


def test_contact_sheet_with_brief_summary():
    """Optional brief summary shows above the numbered list."""
    md = render_contact_sheet(
        ["Why now", "What changed"],
        brief_summary="Q3 update for the exec team — 2-pager.",
    )
    assert "Q3 update for the exec team" in md
    assert md.index("Q3 update") < md.index("1. Why now")


def test_contact_sheet_marks_missing_titles():
    """Blank titles render as '_(no title)_' so the gap is visible."""
    md = render_contact_sheet(["First slide", "", "Third slide"])
    assert "1. First slide" in md
    assert "2. _(no title)_" in md
    assert "3. Third slide" in md


def test_contact_sheet_empty_list():
    """No titles → heading + a note explaining the empty list."""
    md = render_contact_sheet([])
    assert "# Storyline contact sheet" in md
    assert "no titles" in md.lower() or "no slides" in md.lower()


def test_write_storyline_report_minimal(tmp_path: Path):
    """Without verdict/suggestions, writes the contact sheet + a 'pending' header."""
    out = tmp_path / "storyline_report.md"
    write_storyline_report(
        out,
        contact_sheet=render_contact_sheet(["Why now", "What changed"]),
    )
    body = out.read_text()
    assert "Verdict: pending" in body
    assert "1. Why now" in body
    assert "2. What changed" in body


def test_write_storyline_report_with_verdict_and_suggestions(tmp_path: Path):
    """A clean verdict shows in the header; suggestions appear in their own section."""
    out = tmp_path / "storyline_report.md"
    write_storyline_report(
        out,
        contact_sheet=render_contact_sheet(["Why now", "What changed"]),
        verdict="clean",
        suggestions=["Reorder slides 1-2 to lead with the answer."],
    )
    body = out.read_text()
    assert "Verdict: clean" in body
    assert "## Suggestions" in body
    assert "Reorder slides 1-2 to lead with the answer." in body


def test_write_storyline_report_dirty_verdict(tmp_path: Path):
    """Dirty verdict surfaces in the header and the suggestions section is required."""
    out = tmp_path / "storyline_report.md"
    write_storyline_report(
        out,
        contact_sheet=render_contact_sheet(["Topic A", "Topic B"]),
        verdict="dirty",
        suggestions=[
            "Title 1 is a topic noun, not a claim — rewrite as a claim sentence.",
            "Sequence lacks a Complication slide between Situation and Resolution.",
        ],
    )
    body = out.read_text()
    assert "Verdict: dirty" in body
    assert body.count("- ") >= 2  # both suggestions as bullets
