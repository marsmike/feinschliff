"""Deck-level verify framework.

Sibling of `lib/verify/chrome.py` (the deterministic Layer-1 chrome scanner).
This package houses **deterministic helpers** that support deck-level verify
classes — title extraction, contact-sheet rendering, defect catalog, and
the SCR-arc check. The LLM judgment per defect class lives in the /deck
skill's iteration-loop prompt (see
`feinschliff/skills/deck/references/iteration-loop.md`).
"""
from __future__ import annotations

from feinschliff_builder.verify.deck.defects import DeckDefect, format_deck_defects
from feinschliff_builder.verify.deck.narrative_arc import check_narrative_arc
from feinschliff_builder.verify.deck.thumbnails_grid import render_thumbnails_grid_pdf
from feinschliff_builder.verify.deck.title_body import extract_slide_title_and_body

__all__ = [
    "DeckDefect",
    "format_deck_defects",
    "check_narrative_arc",
    "render_thumbnails_grid_pdf",
    "extract_slide_title_and_body",
]
