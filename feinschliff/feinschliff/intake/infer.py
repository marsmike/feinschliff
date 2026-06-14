"""Heuristic inference of a partial deck brief from free-text input."""
from __future__ import annotations

import re


def _match(text: str, *patterns: str) -> bool:
    for pat in patterns:
        if re.search(r"\b" + re.escape(pat) + r"\b", text, re.IGNORECASE):
            return True
    return False


def infer_from_text(brief_text: str) -> dict:
    """Return a partial brief dict based on keyword heuristics. Last match wins per key."""
    result: dict = {}
    t = brief_text

    # deck_type / goal combos — evaluated in order; last match wins
    if _match(t, "status", "update") or re.search(r"\b(Q[1-4]|quarterly|weekly)\b", t, re.IGNORECASE):
        result["goal"] = "status"
        result["deck_type"] = "status-update"
    if _match(t, "training", "workshop", "onboarding"):
        result["deck_type"] = "training"
        result["goal"] = "training"
    if re.search(r"\ball[-\s]hands\b", t, re.IGNORECASE) or _match(t, "all-hands"):
        result["deck_type"] = "all-hands"
    if _match(t, "board", "directors"):
        result["deck_type"] = "board-update"
    if _match(t, "proposal", "RFP"):
        result["deck_type"] = "proposal"
        result["goal"] = "decision"
    if _match(t, "retro", "retrospective", "postmortem"):
        result["deck_type"] = "retrospective"
    if re.search(r"\bcompany intro\b|\babout us\b", t, re.IGNORECASE):
        result["deck_type"] = "company-intro"
    if _match(t, "pitch", "investors", "fundraise"):
        result["deck_type"] = "pitch"
        result["goal"] = "buy-in"

    # audience
    if _match(t, "exec", "executive", "C-suite", "VP") or re.search(r"\bleadership\b", t, re.IGNORECASE):
        result["audience"] = "exec"
    if _match(t, "developer", "engineer", "technical"):
        result["audience"] = "technical"
    if _match(t, "customer", "client meeting"):
        result["audience"] = "external-customer"

    # visual_style
    if _match(t, "KPI", "metrics", "chart", "data"):
        result["visual_style"] = "data-dense"
    if _match(t, "workflow", "process", "flow"):
        result["visual_style"] = "process-flow"

    # length_hint from text length
    if len(brief_text) <= 300:
        result["length_hint"] = "short"
    elif len(brief_text) > 800:
        result["length_hint"] = "long"
    else:
        result["length_hint"] = "standard"

    return result
