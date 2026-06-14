"""Shim — re-exports from feinschliff.verify.deck.titles.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.titles import *  # noqa: F401,F403
from feinschliff.verify.deck.titles import (
    extract_titles_from_plan,
    extract_titles_from_pptx,
)

__all__ = ["extract_titles_from_plan", "extract_titles_from_pptx"]
