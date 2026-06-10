"""Deterministic eval checks for the /goal loop.

Each check is a string. Named checks take no args; count checks have the form
``<element><op><int>`` (e.g. ``rectangles==5``). Checks read an already-generated
artifact (.excalidraw / .svg) and return a bool. No LLM, no render.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_COUNT_RE = re.compile(
    r"^(rectangles|ellipses|diamonds|arrows|text|lines)\s*(==|>=|<=|>|<)\s*(\d+)$"
)
_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")

# Plural check-token -> excalidraw element `type` string.
_ELEMENT_TYPE = {
    "rectangles": "rectangle",
    "ellipses": "ellipse",
    "diamonds": "diamond",
    "arrows": "arrow",
    "text": "text",
    "lines": "line",
}

_OPS = {
    "==": lambda a, b: a == b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


@dataclass
class CheckContext:
    """Shared state a check may need (the active brand pack dir)."""

    brand_dir: Path


def run_check(name: str, artifact: Path, ctx: CheckContext) -> bool:
    """Run a single named/count check against an artifact. Raises on unknown name."""
    if name == "valid-excalidraw-json" or name == "valid-svg":
        return _valid_diagram(artifact)
    if name == "has-viewBox":
        return "viewBox=" in artifact.read_text()
    if name == "uses-semantic-colors":
        return _uses_semantic_colors(artifact, ctx.brand_dir)
    m = _COUNT_RE.match(name)
    if m:
        return _count_check(artifact, m.group(1), m.group(2), int(m.group(3)))
    raise ValueError(f"unknown check: {name!r}")


def _valid_diagram(artifact: Path) -> bool:
    """True iff the structural validator finds no ERROR-severity defects."""
    from feinschmiede.diagnostics import Severity
    from feinschmiede.diagrams import structural_validator as sv

    try:
        defects = sv.validate_diagram_file(artifact)
    except Exception:
        return False
    return not any(d.severity == Severity.ERROR for d in defects)


def _count_check(artifact: Path, element: str, op: str, n: int) -> bool:
    try:
        doc = json.loads(artifact.read_text())
    except Exception:
        return False
    want = _ELEMENT_TYPE[element]
    count = sum(1 for el in doc.get("elements", []) if el.get("type") == want)
    return _OPS[op](count, n)


def _uses_semantic_colors(artifact: Path, brand_dir: Path) -> bool:
    """True iff every #rrggbb in the artifact resolves to an active brand token."""
    from feinschmiede.diagrams.brand_bridge import (
        SEMANTIC_NAMES,
        BrandBridgeError,
        resolve,
    )

    palette: set[str] = set()
    for sem in SEMANTIC_NAMES:
        try:
            palette.add(resolve(sem, brand_dir).lower())
        except BrandBridgeError:
            pass
    text = artifact.read_text()
    return all(m.group(0).lower() in palette for m in _HEX_RE.finditer(text))
