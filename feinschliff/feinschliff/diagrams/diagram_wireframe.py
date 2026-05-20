"""Translate diagram DSL into a primitive list compatible with lib/dsl/svg_wireframe.

The slide-level wireframe expects nodes with {kind, bbox, label} so it can
render amber/blue boxes. We re-parse the diagram DSL into that shape so a
diagram's *internal* primitives can be overlaid alongside the slide bboxes.

For the diagram-overflow validator, every primitive declared in the body
needs a bbox here — the validator only checks what we emit.

When the body is authored in a virtual viewport (canvas > 1720 px), the
font sizes the *renderer* produces are scaled up so they survive
PowerPoint's downscale on insert. The wireframe parser must apply the
same scale so the text-size validator compares against what was actually
rendered, not the raw DSL default. Pass `canvas_w` from the diagram
block's `virtual:WxH` (when set) or its slot width (legacy).
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from ._dsl_common import canvas_scale as _canvas_scale
from .text_metrics import SVG_TEXT_SIZES as _SVG_TEXT_SIZES, EXCALIDRAW_TEXT_SIZES as _EXCALIDRAW_TEXT_SIZES


@dataclass
class Primitive:
    id: str
    kind: str  # "rect" | "text" | "line"
    x: int
    y: int
    w: int
    h: int
    label: str | None = None
    role: str | None = None
    font_size: float | None = None


def primitives_from_svg_dsl(dsl: str, brand_dir: Path, *, canvas_w: int | None = None) -> list[Primitive]:
    scale = _canvas_scale(canvas_w)
    prims: list[Primitive] = []
    for raw in dsl.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        head, *_ = line.split(maxsplit=1)
        if head == "canvas":
            continue
        elif head == "rect":
            parts = shlex.split(line)
            _, _id, xy, wh, _color = parts[:5]
            x, y = [int(p) for p in xy.split(",")]
            w, h = [int(p) for p in wh.split("x")]
            prims.append(Primitive(id=_id, kind="rect", x=x, y=y, w=w, h=h))
        elif head == "bar":
            parts = shlex.split(line)
            _, _id, xy, wh, _color = parts[:5]
            x, y = [int(p) for p in xy.split(",")]
            w, h = [int(p) for p in wh.split("x")]
            prims.append(Primitive(id=_id, kind="rect", x=x, y=y, w=w, h=h))
        elif head == "text":
            parts = shlex.split(line)
            _, _id, xy, level, content = parts[:5]
            x, y = [int(p) for p in xy.split(",")]
            base_size = _SVG_TEXT_SIZES.get(level, 14)
            size = base_size * scale
            prims.append(Primitive(
                id=_id, kind="text",
                x=x, y=int(y - size), w=len(content) * 8, h=int(size + 4),
                label=content, role=level, font_size=float(size),
            ))
        elif head == "axis":
            parts = shlex.split(line)
            _, _id, orient, xy, length, _labels = parts[:6]
            x, y = [int(p) for p in xy.split(",")]
            L = int(length)
            if orient == "horizontal":
                prims.append(Primitive(id=_id, kind="line", x=x, y=y, w=L, h=1))
            else:
                prims.append(Primitive(id=_id, kind="line", x=x, y=y - L, w=1, h=L))
        elif head in ("stacked_bar", "label_box"):
            # Both take `<id> <x>,<y> <w>x<h> …` upfront — bbox is straightforward.
            parts = shlex.split(line)
            _, _id, xy, wh = parts[:4]
            x, y = [int(p) for p in xy.split(",")]
            w, h = [int(p) for p in wh.split("x")]
            prims.append(Primitive(id=_id, kind="rect", x=x, y=y, w=w, h=h))
        elif head in ("polyline", "polygon", "area"):
            # bbox = hull of all <x>,<y> point tokens.
            pts = _collect_xy_tokens(line)
            if not pts:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x, y, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
            prims.append(Primitive(id=_id_from_line(line), kind="rect",
                                   x=int(x), y=int(y), w=int(max(w, 1)), h=int(max(h, 1))))
        elif head == "callout":
            # bbox covers the bubble + anchor point (so the validator catches
            # callouts whose tail points outside the canvas).
            anchor = _kv_xy(line, "anchor")
            at = _kv_xy(line, "at")
            wh = _first_wh_token(line)
            if at and wh and anchor:
                bx, by = at
                bw, bh = wh
                ax, ay = anchor
                xs = [bx, bx + bw, ax]
                ys = [by, by + bh, ay]
                prims.append(Primitive(
                    id=_id_from_line(line), kind="rect",
                    x=int(min(xs)), y=int(min(ys)),
                    w=int(max(xs) - min(xs)), h=int(max(ys) - min(ys)),
                ))
        elif head == "brace":
            # bbox covers from + to + a small slack for the curl depth.
            fr = _kv_xy(line, "from")
            to = _kv_xy(line, "to")
            depth_str = _kv_value(line, "depth")
            if fr and to:
                depth = float(depth_str) if depth_str else 12
                xs = [fr[0], to[0]]
                ys = [fr[1], to[1]]
                pad = int(depth * 2)
                prims.append(Primitive(
                    id=_id_from_line(line), kind="rect",
                    x=int(min(xs)) - pad, y=int(min(ys)) - pad,
                    w=int(max(xs) - min(xs)) + 2 * pad,
                    h=int(max(ys) - min(ys)) + 2 * pad,
                ))
        elif head == "swatch_grid":
            parts = shlex.split(line)
            _, _id, xy = parts[:3]
            x, y = [int(p) for p in xy.split(",")]
            cols = int(_kv_value(line, "cols") or "3")
            cell_w = int(_kv_value(line, "cell_w") or "160")
            cell_h = int(_kv_value(line, "cell_h") or "24")
            swatches_raw = _kv_value(line, "swatches") or ""
            n = max(1, len([s for s in swatches_raw.split(";") if s.strip()]))
            rows = (n + cols - 1) // cols
            prims.append(Primitive(
                id=_id, kind="rect", x=x, y=y, w=cols * cell_w, h=rows * cell_h,
            ))
        # path / group / endgroup / circle / line / legend: covered above or
        # too freeform to bbox-bound cheaply. The full SVG renderer still
        # produces them; they just don't participate in overflow checks.
    return prims


def primitives_from_excalidraw_dsl(dsl: str, brand_dir: Path, *, canvas_w: int | None = None) -> list[Primitive]:
    scale = _canvas_scale(canvas_w)
    prims: list[Primitive] = []
    nodes: dict[str, Primitive] = {}
    for raw in dsl.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        head = line.split()[0]
        if head in ("box", "ellipse"):
            parts = shlex.split(line)
            _, _id, xy, wh, label = parts[:5]
            x, y = [int(p) for p in xy.split(",")]
            w, h = [int(p) for p in wh.split("x")]
            p = Primitive(id=_id, kind="rect", x=x, y=y, w=w, h=h, label=label)
            prims.append(p)
            nodes[_id] = p
            if label:
                # Box label font size = 16 * canvas_scale, mirroring
                # `excalidraw_expand._emit_box`'s `int(round(16 * scale))`.
                prims.append(Primitive(
                    id=f"{_id}.label", kind="text",
                    x=x + 10, y=y + h // 2 - 10, w=w - 20, h=int(20 * scale),
                    label=label, role="body", font_size=16.0 * scale,
                ))
        elif head in ("zone", "lane"):
            # zone/lane carry their own bbox; treat as rect for overflow.
            parts = shlex.split(line)
            _, _id, xy, wh = parts[:4]
            x, y = [int(p) for p in xy.split(",")]
            w, h = [int(p) for p in wh.split("x")]
            prims.append(Primitive(id=_id, kind="rect", x=x, y=y, w=w, h=h))
        elif head == "arrow":
            # Strip optional ports from endpoint specs ("a:right" -> "a").
            m = re.match(r"arrow\s+(\S+?)(?::\w+)?\s*->\s*(\S+?)(?::\w+)?(\s|$)", line)
            if not m:
                continue
            src = nodes.get(m.group(1))
            dst = nodes.get(m.group(2))
            if src and dst:
                sx, sy = src.x + src.w // 2, src.y + src.h // 2
                dx, dy = dst.x + dst.w // 2, dst.y + dst.h // 2
                prims.append(Primitive(
                    id=f"{m.group(1)}->{m.group(2)}", kind="line",
                    x=min(sx, dx), y=min(sy, dy),
                    w=max(abs(dx - sx), 1), h=max(abs(dy - sy), 1),
                ))
        elif head == "text":
            parts = shlex.split(line)
            _, _id, xy, content = parts[:4]
            x, y = [int(p) for p in xy.split(",")]
            base_size = 14
            for p in parts[4:]:
                if p.startswith("size:"):
                    base_size = _EXCALIDRAW_TEXT_SIZES.get(p.split(":", 1)[1], 14)
            size = base_size * scale
            prims.append(Primitive(
                id=_id, kind="text", x=x, y=int(y - size), w=len(content) * 8, h=int(size + 4),
                label=content, role=("title" if base_size >= 20 else "body"), font_size=float(size),
            ))
    return prims


# ---------------------------------------------------------------------------
# Helpers — parsing for the extended SVG primitives.
# ---------------------------------------------------------------------------

_XY_TOKEN = re.compile(r"^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$")


def _collect_xy_tokens(line: str) -> list[tuple[float, float]]:
    """Return every standalone <x>,<y> token in the line as a (float, float)."""
    out: list[tuple[float, float]] = []
    for tok in shlex.split(line):
        if _XY_TOKEN.match(tok):
            x, y = tok.split(",")
            out.append((float(x), float(y)))
    return out


def _kv_value(line: str, key: str) -> str | None:
    """Return the value for `key:value` token (None if missing)."""
    for tok in shlex.split(line):
        if tok.startswith(f"{key}:"):
            return tok.split(":", 1)[1]
    return None


def _kv_xy(line: str, key: str) -> tuple[float, float] | None:
    val = _kv_value(line, key)
    if not val or "," not in val:
        return None
    x, y = val.split(",", 1)
    return float(x), float(y)


def _first_wh_token(line: str) -> tuple[float, float] | None:
    """First `<w>x<h>` numeric token (skipping `key:value` tokens)."""
    for tok in shlex.split(line):
        if ":" in tok:
            continue
        if "x" in tok and "," not in tok:
            try:
                w, h = tok.split("x")
                return float(w), float(h)
            except ValueError:
                continue
    return None


def _id_from_line(line: str) -> str:
    """Second token in a `<head> <id> ...` line."""
    parts = shlex.split(line)
    return parts[1] if len(parts) >= 2 else "?"
