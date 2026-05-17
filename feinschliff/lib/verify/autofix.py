"""Mechanical fix suggestions for content-density defects.

This module does NOT call an LLM. It examines a Defect record and
returns a structured suggestion (which slot, what action, target
character count) that an upstream caller can hand to an LLM in one
shot. The closed-loop "revise then rebuild" cycle is the caller's
job; this is the deterministic ground truth.
"""
from __future__ import annotations

from typing import Any

from lib.defects import Defect, DefectKind


def suggest_fix(d: Defect) -> dict[str, Any] | None:
    if d.kind is DefectKind.SLOT_OVERFLOW:
        slot = d.meta.get("slot")
        budget = d.meta.get("budget_chars")
        over_by = d.meta.get("over_by")
        if slot is None or budget is None or over_by is None:
            return None
        return {
            "slide_index": d.slide_index,
            "slot": slot,
            "action": "shorten",
            "target_chars": budget,
            "instruction": (
                f"Shorten slot '{slot}' by drop ~{over_by} chars to fit "
                f"the {budget}-char budget. Preserve the claim; trim "
                f"qualifiers and filler before facts."
            ),
        }
    if d.kind is DefectKind.TEXT_OVERLAP:
        a, b = d.meta.get("a_id"), d.meta.get("b_id")
        slot = b or a
        return {
            "slide_index": d.slide_index,
            "slot": slot,
            "action": "shorten",
            "target_chars": None,
            "instruction": (
                f"Slot '{slot}' overlaps '{a if slot == b else b}'. "
                f"Shorten '{slot}' until the overlap clears."
            ),
        }
    if d.kind is DefectKind.FILLER_WORD:
        word = d.meta.get("word")
        slot = d.meta.get("slot")
        if word is None or slot is None:
            return None
        return {
            "slide_index": d.slide_index,
            "slot": slot,
            "action": "delete_word",
            "word": word,
            "instruction": f"Remove the filler word '{word}' from slot '{slot}'.",
        }
    return None
