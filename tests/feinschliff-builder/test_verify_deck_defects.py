"""Unit tests for lib/verify/deck/defects — deck-level defect catalog."""
from __future__ import annotations

from feinschliff_builder.verify.deck.defects import DeckDefect, format_deck_defects


def test_deck_defect_required_fields():
    """DeckDefect carries kind, slide_index, message, suggestion."""
    d = DeckDefect(
        kind="title-story-spine",
        slide_index=None,
        message="titles read as a list of topics, not an argument",
        suggestion="rewrite titles as full-sentence claims",
    )
    assert d.kind == "title-story-spine"
    assert d.slide_index is None
    assert d.message.startswith("titles read")
    assert "claims" in d.suggestion


def test_deck_defect_str_for_deck_level():
    """Deck-level defects (slide_index=None) render without 'slide N'."""
    d = DeckDefect(
        kind="title-story-spine", slide_index=None,
        message="narrative incoherent", suggestion="rewrite as claims",
    )
    assert str(d).startswith("[title-story-spine]")
    assert "slide" not in str(d).lower()


def test_deck_defect_str_for_per_slide():
    """Defects targeting a specific slide include the slide marker."""
    d = DeckDefect(
        kind="title-body-coherence", slide_index=3,
        message="title claims X; body proves Y", suggestion="align title to body",
    )
    assert "slide 3" in str(d)
    assert "[title-body-coherence]" in str(d)


def test_format_deck_defects_empty():
    """Empty defect list emits the clean message."""
    out = format_deck_defects([])
    assert "clean" in out.lower()


def test_format_deck_defects_one():
    """Formatted output mentions kind, message, and suggestion."""
    d = DeckDefect(
        kind="title-story-spine", slide_index=None,
        message="titles are topics, not claims",
        suggestion="rewrite each title as a claim sentence",
    )
    out = format_deck_defects([d])
    assert "title-story-spine" in out
    assert "topics, not claims" in out
    assert "rewrite each title" in out
