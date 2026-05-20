"""IR → target kind (excalidraw | svg) heuristic."""
from __future__ import annotations

from typing import Literal

from .ir import ExtractedDiagram


def select_kind(ir: ExtractedDiagram) -> Literal["excalidraw", "svg"]:
    s = ir.signals
    if s.get("bars") or s.get("axis") or s.get("slices"):
        return "svg"
    if s.get("boxes_and_arrows") or s.get("freeform"):
        return "excalidraw"
    return "excalidraw"  # Ambiguous → more permissive default
