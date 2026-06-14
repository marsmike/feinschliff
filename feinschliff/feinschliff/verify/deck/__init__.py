"""Deck-level verify helpers available in feinschliff core.

Deterministic checks (no LLM) and LLM-backed quality gates for the
deck pipeline: defects, narrative arc, titles, storyline, ghost-deck,
claim-evidence, title-lint, notes-budget, notes-coherence, title-body.
"""
from __future__ import annotations

from feinschliff.verify.deck.defects import DeckDefect, format_deck_defects
from feinschliff.verify.deck.narrative_arc import check_narrative_arc
from feinschliff.verify.deck.title_body import extract_slide_title_and_body

__all__ = [
    "DeckDefect",
    "format_deck_defects",
    "check_narrative_arc",
    "extract_slide_title_and_body",
]
