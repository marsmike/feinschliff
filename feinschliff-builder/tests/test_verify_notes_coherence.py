"""Tests for the notes_coherence verifier — contact sheet + report writer.

Mirrors test coverage already in place for the storyline verifier (the
sibling module). The LLM-judged verdict is exercised separately; here
we only check the deterministic input rendering."""
from __future__ import annotations

from pathlib import Path

from feinschliff_builder.verify.deck.notes_coherence import (
    SlideForCoherence,
    render_contact_sheet,
    slides_from_design_brief,
    write_coherence_report,
)


def _slides():
    return [
        SlideForCoherence(
            index=0, role="hook",
            claim="Polish time has collapsed.",
            notes="Storyline: pain → demo → results. Open with the time-collapse stat.",
        ),
        SlideForCoherence(
            index=1, role="context",
            claim="Five years ago, polish took a week.",
            notes="• Week of writer/designer/reviewer cycles.\n• Cost ~$8k per deck.",
        ),
        SlideForCoherence(
            index=2, role="recommendation",
            claim="Adopt the loop.",
            notes=None,
        ),
    ]


def test_contact_sheet_includes_red_line_and_slides():
    sheet = render_contact_sheet("Pain → demo → results.", _slides())
    assert "## Red line" in sheet
    assert "Pain → demo → results." in sheet
    assert "## Slide 1 — hook — Polish time has collapsed." in sheet
    assert "## Slide 2 — context — Five years ago, polish took a week." in sheet
    assert "## Slide 3 — recommendation — Adopt the loop." in sheet
    assert "Storyline: pain" in sheet


def test_missing_notes_render_as_sentinel():
    sheet = render_contact_sheet("arc", _slides())
    assert "_(no notes)_" in sheet


def test_hook_renders_first_even_if_plan_order_is_different():
    """The hook slide is surfaced first regardless of plan order so the
    reader sees the storyline alongside the red_line."""
    out_of_order = [
        SlideForCoherence(
            index=2, role="hook",
            claim="Hook slide arrived late.", notes="storyline beats here",
        ),
        SlideForCoherence(
            index=0, role="context",
            claim="Came first in the plan.", notes="context",
        ),
    ]
    sheet = render_contact_sheet("arc", out_of_order)
    hook_pos = sheet.index("Hook slide arrived late.")
    context_pos = sheet.index("Came first in the plan.")
    assert hook_pos < context_pos


def test_empty_red_line_renders_sentinel():
    sheet = render_contact_sheet("", _slides())
    assert "_(no red_line)_" in sheet


def test_write_coherence_report_headers(tmp_path: Path):
    out = tmp_path / "notes_coherence_report.md"
    sheet = render_contact_sheet("Pain → demo → results.", _slides())
    write_coherence_report(
        out, red_line="Pain → demo → results.", contact_sheet=sheet,
    )
    text = out.read_text()
    assert text.startswith("# Notes Coherence Report")
    assert "- Verdict: pending" in text
    assert "- Slides: 3" in text
    assert "- Red line: Pain → demo → results." in text


def test_write_coherence_report_appends_suggestions(tmp_path: Path):
    out = tmp_path / "notes_coherence_report.md"
    sheet = render_contact_sheet("arc", _slides())
    write_coherence_report(
        out, red_line="arc", contact_sheet=sheet,
        verdict="dirty", suggestions=["Slide 3: add storyline-tracking notes."],
    )
    text = out.read_text()
    assert "- Verdict: dirty" in text
    assert "## Suggestions" in text
    assert "Slide 3: add storyline-tracking notes." in text


def test_slides_from_design_brief_adapter():
    brief = {
        "red_line": "arc",
        "slides": [
            {"index": 0, "role": "hook", "claim": "C0", "notes": "n0"},
            {"index": 1, "role": "context", "claim": "C1"},  # no notes
        ],
    }
    out = slides_from_design_brief(brief)
    assert [s.index for s in out] == [0, 1]
    assert out[0].notes == "n0"
    assert out[1].notes is None
