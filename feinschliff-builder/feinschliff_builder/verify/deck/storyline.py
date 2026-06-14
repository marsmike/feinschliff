"""Shim — re-exports from feinschliff.verify.deck.storyline.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.storyline import *  # noqa: F401,F403
from feinschliff.verify.deck.storyline import (
    Verdict,
    render_contact_sheet,
    write_storyline_report,
    select_arc_schema,
)

__all__ = ["Verdict", "render_contact_sheet", "write_storyline_report", "select_arc_schema"]
