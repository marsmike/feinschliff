"""Shim — re-exports from feinschliff.verify.deck.ghost_deck.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.ghost_deck import *  # noqa: F401,F403
from feinschliff.verify.deck.ghost_deck import (
    GhostDeckResult,
    judge_ghost_deck,
    write_ghost_deck_report,
    _judge,  # noqa: F401  private — exposed for backward-compat test patches
)

__all__ = ["GhostDeckResult", "judge_ghost_deck", "write_ghost_deck_report"]
