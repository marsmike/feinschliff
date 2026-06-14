"""Shim — re-exports from feinschliff.verify.deck.title_body.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.title_body import *  # noqa: F401,F403
from feinschliff.verify.deck.title_body import extract_slide_title_and_body

__all__ = ["extract_slide_title_and_body"]
