"""Shim — re-exports from feinschliff.verify.deck.notes_coherence.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.notes_coherence import *  # noqa: F401,F403
from feinschliff.verify.deck.notes_coherence import (
    SlideForCoherence,
    render_contact_sheet,
    write_coherence_report,
    slides_from_design_brief,
)

__all__ = [
    "SlideForCoherence",
    "render_contact_sheet",
    "write_coherence_report",
    "slides_from_design_brief",
]
