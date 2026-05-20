"""ExtractedDiagram → excalidraw DSL string."""
from __future__ import annotations

from .ir import ExtractedDiagram


def emit(ir: ExtractedDiagram, canvas_w: int, canvas_h: int) -> str:
    lines: list[str] = [f"canvas {canvas_w}x{canvas_h}"]
    for n in ir.nodes:
        primitive = "box" if n.type == "rect" else "ellipse"
        label = n.label.replace('"', '\\"')
        lines.append(
            f'{primitive} {n.id} {n.x},{n.y} {n.w}x{n.h} "{label}"'
        )
    for e in ir.edges:
        lines.append(f"arrow {e.from_id} -> {e.to_id}")
    return "\n".join(lines) + "\n"
