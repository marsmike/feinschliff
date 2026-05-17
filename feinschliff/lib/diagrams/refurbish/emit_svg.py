"""ExtractedDiagram → SVG DSL string."""
from __future__ import annotations

from .ir import ExtractedDiagram


_BAR_COLORS = ["primary", "secondary", "success", "tertiary"]


def emit(ir: ExtractedDiagram, canvas_w: int, canvas_h: int) -> str:
    lines: list[str] = [f"canvas {canvas_w}x{canvas_h}"]
    lines.append(f"rect bg 0,0 {canvas_w}x{canvas_h} paper")
    for i, n in enumerate(ir.nodes):
        color = _BAR_COLORS[i % len(_BAR_COLORS)]
        label = n.label.replace('"', '\\"')
        if n.type == "bar":
            lines.append(
                f'bar {n.id} {n.x},{n.y} {n.w}x{n.h} {color} value:"{label}"'
            )
        else:
            lines.append(
                f'rect {n.id} {n.x},{n.y} {n.w}x{n.h} {color}'
            )
            if label:
                lines.append(
                    f'text {n.id}_l {n.x + n.w//2},{n.y + n.h//2} body "{label}"'
                )
    return "\n".join(lines) + "\n"
