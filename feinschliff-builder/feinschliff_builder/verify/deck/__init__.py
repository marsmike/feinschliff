"""Deck-level verify framework.

Sibling of `lib/verify/chrome.py` (the deterministic Layer-1 chrome scanner).
The implementation of deck-level verify helpers has moved to feinschliff core
(`feinschliff.verify.deck`). This package re-exports for backwards compat and
houses builder-only tooling (non_mece, slide_necessity, squint, thumbnails_grid).
"""
from __future__ import annotations

from feinschliff.verify.deck.defects import DeckDefect, format_deck_defects
from feinschliff.verify.deck.narrative_arc import check_narrative_arc
from feinschliff_builder.verify.deck.thumbnails_grid import render_thumbnails_grid_pdf
from feinschliff.verify.deck.title_body import extract_slide_title_and_body

__all__ = [
    "DeckDefect",
    "format_deck_defects",
    "check_narrative_arc",
    "render_thumbnails_grid_pdf",
    "extract_slide_title_and_body",
]
