"""Shim — re-exports from feinschliff.verify.deck.defects.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.defects import *  # noqa: F401,F403
from feinschliff.verify.deck.defects import DeckDefect, format_deck_defects

__all__ = ["DeckDefect", "format_deck_defects"]
