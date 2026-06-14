"""Unit tests for verify/deck/defects — DeckDefect dataclass + formatter."""
from __future__ import annotations

from feinschliff.verify.deck.defects import DeckDefect, format_deck_defects


def test_deck_defect_str_with_slide_index():
    d = DeckDefect(kind="title-story-spine", slide_index=3, message="Gap", suggestion="Fix it")
    assert "slide 3" in str(d)
    assert "[title-story-spine]" in str(d)
    assert "Gap" in str(d)


def test_deck_defect_str_without_slide_index():
    d = DeckDefect(kind="narrative-arc-missing", slide_index=None, message="Missing arc", suggestion="Add it")
    assert "slide" not in str(d)
    assert "[narrative-arc-missing]" in str(d)


def test_format_deck_defects_empty():
    result = format_deck_defects([])
    assert "clean" in result.lower()
    assert "defect" in result.lower()


def test_format_deck_defects_one():
    d = DeckDefect(kind="x", slide_index=1, message="Msg", suggestion="Hint")
    result = format_deck_defects([d])
    assert "1 defect" in result
    assert "Msg" in result
    assert "Hint" in result
