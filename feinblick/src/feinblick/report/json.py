"""JSON reporter — the agent-consumable surface.

Named ``json`` to match the reporter registry; imports stdlib ``json`` as
``_json`` so this module never shadows it for callers.
"""
from __future__ import annotations

import json as _json

from feinblick.model import Finding


def render(findings: list[Finding], verdict: str, health: dict, meta: dict) -> str:
    payload = {
        "verdict": verdict,
        "health": health,
        "meta": meta,
        "findings": [f.to_dict() for f in findings],
    }
    return _json.dumps(payload, indent=2, sort_keys=False)
