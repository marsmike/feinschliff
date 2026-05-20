"""Unit tests for lib/verify/deck/slide_necessity — necessity-context helper."""
from __future__ import annotations

import pytest

from lib.verify.deck.slide_necessity import materialize_necessity_context


def test_middle_slide_returns_all_three_titles():
    """A slide in the middle of the deck has both neighbours populated."""
    titles = ["Why now", "What changed", "How we win", "Asks"]
    ctx = materialize_necessity_context(titles, slide_index=2)
    assert ctx == {
        "prev_title": "Why now",
        "current_title": "What changed",
        "next_title": "How we win",
    }


def test_first_slide_prev_is_none():
    """The first slide has no predecessor."""
    titles = ["Why now", "What changed", "How we win"]
    ctx = materialize_necessity_context(titles, slide_index=1)
    assert ctx["prev_title"] is None
    assert ctx["current_title"] == "Why now"
    assert ctx["next_title"] == "What changed"


def test_last_slide_next_is_none():
    """The last slide has no successor."""
    titles = ["Why now", "What changed", "How we win"]
    ctx = materialize_necessity_context(titles, slide_index=3)
    assert ctx["prev_title"] == "What changed"
    assert ctx["current_title"] == "How we win"
    assert ctx["next_title"] is None


def test_slide_index_out_of_range():
    """slide_index outside [1, len] raises IndexError."""
    titles = ["Why now", "What changed"]
    with pytest.raises(IndexError, match="out of range"):
        materialize_necessity_context(titles, slide_index=0)
    with pytest.raises(IndexError, match="out of range"):
        materialize_necessity_context(titles, slide_index=3)
