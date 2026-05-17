"""Tiny dotted-path walker for JSON tokens. No array indices, no wildcards.

Used by ``lib/diagrams/brand_bridge.py`` to resolve semantic DSL color names
to hex values by walking dotted token paths (e.g. ``color.accent``) in a
brand's ``tokens.json``.
"""
from __future__ import annotations

from typing import Any


def walk(obj: Any, path: str) -> Any:
    """Navigate `obj` by dotted-key `path`. Returns None if any key is missing.
    Rejects numeric segments — keep it simple, search responses don't need them."""
    if not path:
        return obj
    cur = obj
    for seg in path.split("."):
        if seg.isdigit():
            raise ValueError(f"array indices not supported in path {path!r}")
        if not isinstance(cur, dict):
            return None
        if seg not in cur:
            return None
        cur = cur[seg]
    return cur


def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge `overlay` into `base`; overlay wins on conflicts.

    Returns a new dict — neither input is mutated. Used for layering
    brand-extends parents under a child's tokens.json.
    """
    out = dict(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
