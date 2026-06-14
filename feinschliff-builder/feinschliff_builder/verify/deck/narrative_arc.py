"""Shim — re-exports from feinschliff.verify.deck.narrative_arc.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.narrative_arc import *  # noqa: F401,F403
from feinschliff.verify.deck.narrative_arc import check_narrative_arc

__all__ = ["check_narrative_arc"]
