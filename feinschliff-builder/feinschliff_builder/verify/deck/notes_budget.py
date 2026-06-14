"""Shim — re-exports from feinschliff.verify.deck.notes_budget.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.notes_budget import *  # noqa: F401,F403
from feinschliff.verify.deck.notes_budget import validate_notes

__all__ = ["validate_notes"]
