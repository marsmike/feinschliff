"""Structural lint for per-slide speaker notes.

Covers the deterministic pre-flight that runs alongside `validate_content`
in `feinschliff deck build`. The LLM-judged coherence check is separate
(`lib/verify/deck/notes_coherence.py`).
"""
from __future__ import annotations

from feinschliff_builder.verify.deck.notes_budget import validate_notes


# ── hook slide ────────────────────────────────────────────────────────


def test_hook_missing_notes_is_defect_when_verbosity_set():
    out = validate_notes(
        None, slide_index=1, is_hook=True, verbosity="standard",
    )
    assert len(out) == 1
    assert out[0].kind == "notes-hook-missing"


def test_hook_missing_notes_is_clean_without_verbosity():
    """Legacy plans (no `verbosity:` field) don't opt into notes lint —
    a missing hook-slide notes block is allowed so existing decks
    keep building without authoring notes."""
    assert validate_notes(None, slide_index=1, is_hook=True) == []


def test_hook_blank_notes_is_defect():
    out = validate_notes(
        "   \n  ", slide_index=1, is_hook=True, verbosity="standard",
    )
    assert len(out) == 1
    assert out[0].kind == "notes-hook-missing"


def test_hook_too_short_is_defect():
    out = validate_notes(
        "Storyline.", slide_index=1, is_hook=True, verbosity="standard",
    )
    assert len(out) == 1
    assert out[0].kind == "notes-hook-missing"
    assert "≥60" in out[0].message or "60" in out[0].message


def test_hook_with_storyline_is_clean():
    notes = (
        "Storyline: pain → demo → results.\n"
        "Open with the time-collapse stat. Hand off to the live demo "
        "at 0:45."
    )
    assert validate_notes(
        notes, slide_index=1, is_hook=True, verbosity="standard",
    ) == []


def test_hook_is_exempt_from_word_budget():
    """A hook slide with very long notes shouldn't fire notes-overbudget."""
    notes = " ".join(["word"] * 500)
    out = validate_notes(
        notes, slide_index=1, is_hook=True, verbosity="concise",
    )
    assert out == []


# ── non-hook slides ───────────────────────────────────────────────────


def test_missing_notes_on_non_hook_is_clean():
    """Per-slide notes are optional; structural lint doesn't complain."""
    assert validate_notes(None, slide_index=2, is_hook=False) == []
    assert validate_notes("", slide_index=2, is_hook=False) == []


def test_concise_budget_overrun_is_defect():
    notes = " ".join(["word"] * 50)  # 50 > 40
    out = validate_notes(
        notes, slide_index=2, is_hook=False, verbosity="concise",
    )
    assert len(out) == 1
    assert out[0].kind == "notes-overbudget"
    assert "50 words" in out[0].message
    assert "40" in out[0].message


def test_standard_budget_passes_at_80_words():
    notes = " ".join(["word"] * 80)
    assert validate_notes(
        notes, slide_index=2, is_hook=False, verbosity="standard",
    ) == []


def test_standard_budget_overruns_at_81_words():
    notes = " ".join(["word"] * 81)
    out = validate_notes(
        notes, slide_index=2, is_hook=False, verbosity="standard",
    )
    assert len(out) == 1
    assert out[0].kind == "notes-overbudget"


def test_text_heavy_budget_passes_at_160_words():
    notes = " ".join(["word"] * 160)
    assert validate_notes(
        notes, slide_index=2, is_hook=False, verbosity="text-heavy",
    ) == []


def test_unknown_verbosity_skips_budget_check():
    """Defensive: an unrecognised verbosity value can't enforce a budget,
    so the check is skipped rather than crashing or guessing."""
    notes = " ".join(["word"] * 500)
    assert validate_notes(
        notes, slide_index=2, is_hook=False, verbosity="balanced",
    ) == []


def test_missing_verbosity_skips_budget_check():
    """Plan.yaml without `verbosity:` → no budget enforcement."""
    notes = " ".join(["word"] * 500)
    assert validate_notes(
        notes, slide_index=2, is_hook=False, verbosity=None,
    ) == []
