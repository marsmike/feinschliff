"""Expand Excalidraw DSL into Excalidraw JSON using active brand tokens.

DSL grammar (concept diagrams: shapes, arrows, free-floating text, regions):

  canvas  <W>x<H>
  box     <id> <x>,<y> <w>x<h>  "<label>"  [fill:<color>]
  ellipse <id> <x>,<y> <w>x<h>  "<label>"  [fill:<color>]
  diamond <id> <x>,<y> <w>x<h>  "<label>"  [fill:<color>]
  dot     <id> <x>,<y>                     [fill:<color>]
  line    <id> <x1>,<y1> <x2>,<y2>         [dashed]  [fill:<color>]
  zone    <id> <x>,<y> <w>x<h>  "<label>"  [fill:<color>] [stroke:<color>] [dashed]
  lane    <id> <x>,<y> <w>x<h>  "<label>"  orient:vertical|horizontal [fill:<color>]
  arrow   <from>[:<port>] -> <to>[:<port>] [flag ...]
  text    <id> <x>,<y>          "<content>"  [size:<title|body|detail|...>]

Arrow flags (all optional, order-independent):
  via:x1,y1;x2,y2;...        manual waypoints between src and dst borders
  route:straight|elbow       default straight; elbow = 2 computed perp turns
  style:solid|dashed|dotted  Excalidraw strokeStyle. When unset, arrows
                             that cross a non-endpoint box are auto-set
                             to `dotted` (visual cue that the line passes
                             through the boxes layered above it).
  color:<token>              strokeColor; default 'ink'
  weight:primary|secondary|muted   strokeWidth multiplier 2.5/2.0/1.5
  label:"<text>"             arrow label rendered along the polyline
  labelpos:above|below|left|right|mid   default mid = perpendicular auto-
                             offset (above for horizontal-ish arrows, right
                             for vertical-ish). Labels are never placed
                             directly on the arrow line.

Z-order: arrow strokes render BEHIND foreground shapes (boxes/ellipses/
diamonds), so a crossing arrow visually disappears under the box it
crosses rather than overlaying its label. Arrow labels still render on
top of everything so they remain readable.

Endpoint ports:
  <id>:left   exit/enter at center of left edge
  <id>:right  ... right edge
  <id>:top    ... top edge
  <id>:bottom ... bottom edge

All <color> tokens go through brand_bridge.resolve(). `\\n` inside a
quoted label becomes a real newline.

When the canvas is wider than 1920 (the standard slide pixel width),
default sizes (arrow labels, box labels, strokes) scale up by
canvas_w/1920 so they stay legible after PowerPoint's downscale on
insert. Bodies that fit in a single slide (canvas <= 1920) are
unaffected.
"""
from __future__ import annotations

import json
import re
import shlex
import uuid
from itertools import pairwise
from pathlib import Path

from ._dsl_common import (
    canvas_scale as _canvas_scale,
    parse_wh as _parse_wh,
    parse_xy as _parse_xy,
)
from .brand_bridge import label_color_for as _label_color_for, resolve, resolve_brand_dir, strip_brand_directive
from .text_metrics import EXCALIDRAW_TEXT_SIZES as _EXCALIDRAW_TEXT_SIZES


_VALID_PORTS = frozenset({"left", "right", "top", "bottom"})


def expand(dsl: str, brand_dir: Path, canvas_override: tuple[int, int] | None = None) -> str:
    canvas_w, canvas_h = (None, None)
    if canvas_override:
        canvas_w, canvas_h = canvas_override
    # Layering (back to front):
    #   background  — zones / lanes
    #   arrow_strokes — arrow polylines, sit BEHIND foreground so a
    #                   crossing arrow disappears under the box it crosses
    #   foreground  — boxes, ellipses, diamonds, dots, lines, free text,
    #                 box-bound text
    #   arrow_labels — arrow label text, on top of everything so the
    #                  edge-on labels stay readable
    # Arrows are deferred until all nodes are emitted so node lookups
    # succeed regardless of declaration order within the body.
    background: list[dict] = []
    foreground: list[dict] = []
    arrow_strokes: list[dict] = []
    arrow_labels: list[dict] = []
    deferred_arrows: list[str] = []
    nodes: dict[str, dict] = {}
    theme = "light"

    # First pass for canvas (when not overridden) so font scaling knows the
    # target dimensions before any primitive is emitted.
    if canvas_w is None:
        for raw in dsl.splitlines():
            line = raw.strip()
            if line.startswith("canvas"):
                m = re.match(r"canvas\s+(\d+)x(\d+)", line)
                if m:
                    canvas_w, canvas_h = int(m.group(1)), int(m.group(2))
                    break

    scale = _canvas_scale(canvas_w)

    for raw in dsl.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        head = line.split()[0]
        if head == "canvas":
            # Already consumed in first pass (or via override).
            continue
        elif head == "theme":
            parts = line.split(maxsplit=1)
            theme = (parts[1].strip().lower() if len(parts) > 1 else "light")
        elif head in ("box", "ellipse", "diamond"):
            shape, text = _emit_box(line, head, brand_dir, theme, scale=scale)
            foreground.append(shape)
            if text:
                foreground.append(text)
            nodes[shape["customData"]["dsl_id"]] = shape
        elif head == "dot":
            foreground.append(_emit_dot(line, brand_dir))
        elif head == "line":
            foreground.append(_emit_line_node(line, brand_dir, theme))
        elif head == "zone":
            background.extend(_emit_zone(line, brand_dir, theme, scale=scale))
        elif head == "lane":
            background.extend(_emit_lane(line, brand_dir, theme, scale=scale))
        elif head == "group":
            _apply_group(line, nodes, foreground)
        elif head == "arrow":
            deferred_arrows.append(line)
        elif head == "text":
            foreground.append(_emit_text(line, brand_dir, theme, scale=scale))
        else:
            raise ValueError(f"excalidraw_expand: unknown primitive '{head}'")

    for arrow_line in deferred_arrows:
        strokes, labels = _emit_arrow(arrow_line, nodes, brand_dir, theme=theme, scale=scale)
        arrow_strokes.extend(strokes)
        arrow_labels.extend(labels)

    if canvas_w is None:
        raise ValueError("excalidraw_expand: missing canvas")

    # `theme dark` uses brand-stable dark/light tokens (`chapter-slab` is
    # always dark across light + dark brands; `off-white` is always light).
    # The earlier `ink`/`paper` pair inverted in dark brands and rendered
    # invisible boxes — see postmortem-eng debug session.
    bg = resolve("chapter-slab", brand_dir) if theme == "dark" else resolve("paper", brand_dir)
    return json.dumps({
        "type": "excalidraw",
        "version": 2,
        "source": "feinschliff",
        "elements": background + arrow_strokes + foreground + arrow_labels,
        "appState": {
            "viewBackgroundColor": bg,
            "width": canvas_w,
            "height": canvas_h,
        },
        "files": {},
    }, indent=2)


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


# Color aliases — let DSL authors use upstream Excalidraw plugin's semantic
# names while the resolver still maps everything onto brand tokens.
_COLOR_ALIASES = {
    "start":     "accent",
    "end":       "success",
    "warning":   "warning",
    "decision":  "status-pending",
    "ai":        "tertiary",
    "inactive":  "neutral-soft",
    "error":     "danger",
    "code":      "ink",
    "data":      "surface-2",
}


def _resolve_color(name: str, brand_dir: Path) -> str:
    return resolve(_COLOR_ALIASES.get(name, name), brand_dir)


def _emit_box(line: str, kind: str, brand_dir: Path, theme: str = "light", *, scale: float = 1.0) -> tuple[dict, dict | None]:
    parts = shlex.split(line)
    _kind, dsl_id, xy, wh = parts[:4]
    label = ""
    fill_color = "primary"
    for p in parts[4:]:
        if p.startswith("fill:"):
            fill_color = p.split(":", 1)[1]
        elif not label:
            label = p
    label = label.replace("\\n", "\n")
    x, y = _parse_xy(xy)
    w, h = _parse_wh(wh)
    fill_hex = _resolve_color(fill_color, brand_dir)
    shape_id = _new_id()
    excalidraw_kind = {
        "box": "rectangle",
        "ellipse": "ellipse",
        "diamond": "diamond",
    }[kind]
    # Stroke derived from fill luminance — see postmortem above.
    # Theme-based check caused dark-on-dark when fill was also a dark token.
    stroke_color = _label_color_for(fill_hex, brand_dir)
    stroke_width = max(1, int(round(2 * scale)))
    shape = {
        "id": shape_id,
        "type": excalidraw_kind,
        "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke_color,
        "backgroundColor": fill_hex,
        "fillStyle": "solid",
        "strokeWidth": stroke_width,
        "strokeStyle": "dashed" if fill_color == "inactive" else "solid",
        "roughness": 1,
        "roundness": {"type": 3} if kind == "box" else None,
        "customData": {"dsl_id": dsl_id},
    }
    text = None
    if label and label.strip():
        # Always use the per-fill contrast check. Special-casing dark
        # theme to off-white assumed every fill in dark theme would be
        # dark, but `fill:ink` resolves to a light token in dark brands
        # (ink inverts) — so the rule produced white-on-white labels on
        # those boxes. _label_color_for picks off-white / chapter-slab
        # based on the actual fill luminance and works in every theme.
        label_color = _label_color_for(fill_hex, brand_dir)
        text_id = _new_id()
        font_size = int(round(16 * scale))
        text = {
            "id": text_id,
            "type": "text",
            "x": x + 10, "y": y + h // 2 - 10,
            "width": w - 20, "height": int(round(20 * scale)),
            "text": label,
            "fontSize": font_size,
            "fontFamily": 2,
            "textAlign": "center",
            "verticalAlign": "middle",
            "baseline": int(round(18 * scale)),
            "lineHeight": 1.25,
            "strokeColor": label_color,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "containerId": shape_id,
        }
        shape["boundElements"] = [{"id": text_id, "type": "text"}]
    return shape, text


def _emit_dot(line: str, brand_dir: Path) -> dict:
    """Small 12px filled ellipse — useful as a flow marker."""
    parts = shlex.split(line)
    _, _dsl_id, xy = parts[:3]
    x, y = _parse_xy(xy)
    color = "primary"
    for p in parts[3:]:
        if p.startswith("fill:"):
            color = p.split(":", 1)[1]
        elif not p.startswith(("size:", "label:")):
            color = p
    fill_hex = _resolve_color(color, brand_dir)
    return {
        "id": _new_id(),
        "type": "ellipse",
        "x": x - 6, "y": y - 6,
        "width": 12, "height": 12,
        "strokeColor": fill_hex,
        "backgroundColor": fill_hex,
        "fillStyle": "solid",
        "strokeWidth": 1,
        "roughness": 1,
    }


def _emit_line_node(line: str, brand_dir: Path, theme: str = "light") -> dict:
    """Structural line (e.g., section divider). Optional `dashed` flag."""
    parts = shlex.split(line)
    _, _dsl_id, xy1, xy2 = parts[:4]
    x1, y1 = [int(p) for p in xy1.split(",")]
    x2, y2 = [int(p) for p in xy2.split(",")]
    dashed = "dashed" in parts[4:]
    color_token = "neutral-soft"
    for p in parts[4:]:
        if p.startswith("fill:"):
            color_token = p.split(":", 1)[1]
    stroke_hex = _resolve_color(color_token, brand_dir)
    return {
        "id": _new_id(),
        "type": "line",
        "x": x1, "y": y1,
        "width": x2 - x1, "height": y2 - y1,
        "strokeColor": stroke_hex,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 1,
        "points": [[0, 0], [x2 - x1, y2 - y1]],
    }


def _emit_zone(line: str, brand_dir: Path, theme: str = "light", *, scale: float = 1.0) -> list[dict]:
    """A named rectangular region with a small eyebrow label at top-left.

    Zones render BEHIND foreground shapes so they read as "the area this
    set of components lives in" without obscuring detail. Default fill is
    surface-2 with a subtle dashed stroke; both overridable. The label
    sits as a free-floating uppercase eyebrow just inside the top edge.
    """
    parts = shlex.split(line)
    _, dsl_id, xy, wh = parts[:4]
    x, y = _parse_xy(xy)
    w, h = _parse_wh(wh)
    label = ""
    fill_token = "surface-2"
    stroke_token = "neutral-soft"
    dashed = False
    for p in parts[4:]:
        if p.startswith("fill:"):
            fill_token = p.split(":", 1)[1]
        elif p.startswith("stroke:"):
            stroke_token = p.split(":", 1)[1]
        elif p == "dashed":
            dashed = True
        elif not label:
            label = p
    label = label.replace("\\n", "\n")
    fill_hex = _resolve_color(fill_token, brand_dir)
    stroke_hex = _resolve_color(stroke_token, brand_dir)
    rect = {
        "id": _new_id(),
        "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke_hex,
        "backgroundColor": fill_hex,
        "fillStyle": "hachure",
        "strokeWidth": 1,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 1,
        "roundness": {"type": 3},
        "opacity": 35,
        "customData": {"dsl_id": dsl_id, "dsl_kind": "zone"},
    }
    elements = [rect]
    if label:
        font_size = int(round(14 * scale))
        elements.append({
            "id": _new_id(),
            "type": "text",
            "x": x + int(round(16 * scale)),
            "y": y + int(round(8 * scale)),
            "text": label,
            "fontSize": font_size,
            "fontFamily": 2,
            "textAlign": "left",
            "verticalAlign": "top",
            "strokeColor": resolve("neutral-strong", brand_dir),
            "backgroundColor": "transparent",
            "lineHeight": 1.2,
            "customData": {"dsl_id": f"{dsl_id}.label", "dsl_kind": "zone-label"},
        })
    return elements


def _emit_lane(line: str, brand_dir: Path, theme: str = "light", *, scale: float = 1.0) -> list[dict]:
    """A swim-lane region with the label on the leading edge.

    orient:vertical  → label at top, content flows down the lane.
    orient:horizontal → label at left, content flows across the lane.
    Renders behind foreground shapes like zone does.
    """
    parts = shlex.split(line)
    _, dsl_id, xy, wh = parts[:4]
    x, y = _parse_xy(xy)
    w, h = _parse_wh(wh)
    label = ""
    fill_token = "surface"
    orient = "vertical"
    for p in parts[4:]:
        if p.startswith("fill:"):
            fill_token = p.split(":", 1)[1]
        elif p.startswith("orient:"):
            orient = p.split(":", 1)[1]
        elif not label:
            label = p
    label = label.replace("\\n", "\n")
    fill_hex = _resolve_color(fill_token, brand_dir)
    stroke_hex = resolve("neutral-soft", brand_dir)
    rect = {
        "id": _new_id(),
        "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "strokeColor": stroke_hex,
        "backgroundColor": fill_hex,
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 1,
        "roundness": {"type": 3},
        "opacity": 60,
        "customData": {"dsl_id": dsl_id, "dsl_kind": "lane"},
    }
    elements: list[dict] = [rect]
    if label:
        font_size = int(round(16 * scale))
        if orient == "horizontal":
            label_x = x + int(round(16 * scale))
            label_y = y + h // 2 - font_size // 2
        else:
            label_x = x + int(round(16 * scale))
            label_y = y + int(round(12 * scale))
        elements.append({
            "id": _new_id(),
            "type": "text",
            "x": label_x,
            "y": label_y,
            "text": label,
            "fontSize": font_size,
            "fontFamily": 2,
            "textAlign": "left",
            "verticalAlign": "top",
            "strokeColor": resolve("neutral-strong", brand_dir),
            "backgroundColor": "transparent",
            "lineHeight": 1.2,
            "customData": {"dsl_id": f"{dsl_id}.label", "dsl_kind": "lane-label"},
        })
    return elements


def _apply_group(line: str, nodes: dict[str, dict], elements: list[dict]) -> None:
    """`group <id1> <id2> [...]` — assigns the same groupId to listed elements."""
    parts = line.split()[1:]
    group_id = _new_id()
    targets = {nodes[i]["id"] for i in parts if i in nodes}
    for el in elements:
        if el.get("id") in targets:
            el.setdefault("groupIds", []).append(group_id)


def _parse_port_spec(spec: str) -> tuple[str, str | None]:
    """Split an arrow endpoint into (id, port|None).

    Examples:
        "mcu"       -> ("mcu", None)
        "mcu:right" -> ("mcu", "right")
    """
    if ":" not in spec:
        return spec, None
    node_id, port = spec.split(":", 1)
    if port not in _VALID_PORTS:
        raise ValueError(
            f"excalidraw_expand: arrow endpoint '{spec}' uses unknown port "
            f"'{port}'; valid: {sorted(_VALID_PORTS)}"
        )
    return node_id, port


def _port_anchor(node: dict, port: str | None, *, ray_target: tuple[float, float] | None = None) -> tuple[float, float]:
    """Anchor point on a node's border.

    When `port` is set, returns the center of that border. When unset,
    falls back to the center-to-center ray intersection (the existing
    canonical Excalidraw routing — see _border_intersection).
    """
    cx = node["x"] + node["width"] / 2
    cy = node["y"] + node["height"] / 2
    if port == "left":
        return (node["x"], cy)
    if port == "right":
        return (node["x"] + node["width"], cy)
    if port == "top":
        return (cx, node["y"])
    if port == "bottom":
        return (cx, node["y"] + node["height"])
    if ray_target is None:
        return (cx, cy)
    return _border_intersection(node, ray_target)


def _border_intersection(node: dict, target: tuple[float, float]) -> tuple[float, float]:
    """Where does the ray (node_center → target) hit node's border?"""
    cx = node["x"] + node["width"] / 2
    cy = node["y"] + node["height"] / 2
    hw = node["width"] / 2
    hh = node["height"] / 2
    vx, vy = target[0] - cx, target[1] - cy
    if vx == 0 and vy == 0:
        return (cx, cy)
    ts: list[float] = []
    if abs(vx) > 1e-9:
        ts.append(hw / abs(vx))
    if abs(vy) > 1e-9:
        ts.append(hh / abs(vy))
    t = min(ts) if ts else 0.0
    return (cx + vx * t, cy + vy * t)


def _route_arrow(src: dict, dst: dict, src_port: str | None = None, dst_port: str | None = None) -> list[tuple[float, float]]:
    """Edge-to-edge route from src to dst.

    When neither endpoint has a port, this matches the canonical
    Excalidraw routing (straight line along the center-to-center ray,
    intersecting each box's border). When ports are specified, the
    anchors are the centers of the named edges.
    """
    s_cx = src["x"] + src["width"] / 2
    s_cy = src["y"] + src["height"] / 2
    d_cx = dst["x"] + dst["width"] / 2
    d_cy = dst["y"] + dst["height"] / 2
    if src_port:
        src_anchor = _port_anchor(src, src_port)
    else:
        src_anchor = _border_intersection(src, (d_cx, d_cy))
    if dst_port:
        dst_anchor = _port_anchor(dst, dst_port)
    else:
        dst_anchor = _border_intersection(dst, (s_cx, s_cy))
    return [src_anchor, dst_anchor]


def _elbow_waypoints(src_anchor: tuple[float, float], dst_anchor: tuple[float, float],
                     src_port: str | None, dst_port: str | None) -> list[tuple[float, float]]:
    """Two perpendicular waypoints between src and dst anchors.

    Strategy: leave source in the direction of its port (if known) or
    horizontally toward dst (if no port), then turn perpendicular to enter
    dst. Simple: one corner point between src and dst, placed at the
    geometric midpoint of the perpendicular projection. No collision
    avoidance — author uses `via:` for tricky routing through obstacles.
    """
    sx, sy = src_anchor
    dx, dy = dst_anchor
    # Pick a corner. If src exits horizontally (left/right port), turn
    # vertical first — i.e. corner sits at (dx, sy). If src exits vertically
    # (top/bottom port), corner sits at (sx, dy). When src has no port, fall
    # back to the larger axis: if |dx-sx| > |dy-sy|, go horizontal first.
    if src_port in ("left", "right"):
        corner = (dx, sy)
    elif src_port in ("top", "bottom"):
        corner = (sx, dy)
    elif dst_port in ("left", "right"):
        corner = (sx, dy)
    elif dst_port in ("top", "bottom"):
        corner = (dx, sy)
    elif abs(dx - sx) > abs(dy - sy):
        corner = (dx, sy)
    else:
        corner = (sx, dy)
    return [corner]


_STROKE_WEIGHT = {"primary": 3.5, "secondary": 2.5, "muted": 1.5}
_STROKE_STYLES = {"solid", "dashed", "dotted"}
_ROUTE_KINDS = {"straight", "elbow"}
_LABEL_POSITIONS = {"above", "below", "left", "right", "mid"}


def _segment_rect_t_range(p1: tuple[float, float], p2: tuple[float, float],
                          rx: float, ry: float, rw: float, rh: float,
                          *, inset: float = 1.0) -> tuple[float, float] | None:
    """Liang-Barsky: (t1, t2) parametric range where segment [p1, p2] lies
    inside the rect (shrunk by `inset` on each side), or None when the
    segment doesn't enter. Inset > 0 keeps grazing endpoints — e.g.,
    arrow endpoints sitting on src/dst borders — from registering as
    crossings.
    """
    x1, y1 = p1
    x2, y2 = p2
    minx = rx + inset
    miny = ry + inset
    maxx = rx + rw - inset
    maxy = ry + rh - inset
    if minx >= maxx or miny >= maxy:
        return None
    dx = x2 - x1
    dy = y2 - y1
    u1, u2 = 0.0, 1.0
    for p, q in ((-dx, x1 - minx), (dx, maxx - x1), (-dy, y1 - miny), (dy, maxy - y1)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            if t > u2:
                return None
            if t > u1:
                u1 = t
        else:
            if t < u1:
                return None
            if t < u2:
                u2 = t
    if u1 < u2:
        return (u1, u2)
    return None


def _arrow_crosses_other_boxes(waypoints: list[tuple[float, float]],
                               src_id: str, dst_id: str,
                               nodes: dict[str, dict]) -> bool:
    """True if any segment of the polyline enters a non-endpoint node."""
    for seg_a, seg_b in pairwise(waypoints):
        for nid, node in nodes.items():
            if nid == src_id or nid == dst_id:
                continue
            if _segment_rect_t_range(seg_a, seg_b,
                                     node["x"], node["y"],
                                     node["width"], node["height"]) is not None:
                return True
    return False


def _subtract_blocked(blocked: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """[0,1] minus the union of `blocked` intervals — returns the clear
    sub-intervals along a segment's parametric range."""
    if not blocked:
        return [(0.0, 1.0)]
    merged: list[list[float]] = []
    for t1, t2 in sorted(blocked):
        if merged and t1 <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], t2)
        else:
            merged.append([t1, t2])
    clear: list[tuple[float, float]] = []
    cursor = 0.0
    for t1, t2 in merged:
        if t1 > cursor:
            clear.append((cursor, t1))
        cursor = max(cursor, t2)
    if cursor < 1.0:
        clear.append((cursor, 1.0))
    return clear


def _clear_label_anchor(waypoints: list[tuple[float, float]],
                        src_id: str, dst_id: str,
                        nodes: dict[str, dict]) -> tuple[float, float, float, float]:
    """(mid_x, mid_y, ux, uy) anchored to the midpoint of the longest
    sub-segment that isn't covered by any non-endpoint box.

    For arrows that cross third-party boxes (auto-dotted), the geometric
    midpoint can fall inside a covered region, putting the label on top
    of the box's own label. This walks the polyline, subtracts the
    portions hidden behind other boxes, and picks the centre of the
    longest visible stretch instead. Falls back to the geometric
    midpoint when nothing is clear (shouldn't happen for valid layouts)
    or when no boxes obstruct (most diagrams)."""
    obstructions = [n for nid, n in nodes.items() if nid not in (src_id, dst_id)]
    best: tuple[float, float, float, float, float] | None = None  # (length, x, y, ux, uy)
    for (x1, y1), (x2, y2) in pairwise(waypoints):
        seg_len = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if seg_len == 0:
            continue
        blocked: list[tuple[float, float]] = []
        for n in obstructions:
            t_range = _segment_rect_t_range((x1, y1), (x2, y2),
                                            n["x"], n["y"],
                                            n["width"], n["height"])
            if t_range is not None:
                blocked.append(t_range)
        for t1, t2 in _subtract_blocked(blocked):
            length = (t2 - t1) * seg_len
            if best is None or length > best[0]:
                tm = (t1 + t2) / 2
                best = (length,
                        x1 + tm * (x2 - x1),
                        y1 + tm * (y2 - y1),
                        (x2 - x1) / seg_len,
                        (y2 - y1) / seg_len)
    if best is None:
        (mx, my), (ux, uy) = _midpoint_with_direction(waypoints)
        return (mx, my, ux, uy)
    return (best[1], best[2], best[3], best[4])


def _midpoint_with_direction(points: list[tuple[float, float]]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return ((mid_x, mid_y), (ux, uy)) — point at half polyline length plus
    unit direction of the segment that contains it."""
    if len(points) < 2:
        return ((0.0, 0.0), (1.0, 0.0))
    segs: list[tuple[float, float, float, float, float]] = []
    total = 0.0
    for (x1, y1), (x2, y2) in pairwise(points):
        L = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        segs.append((x1, y1, x2, y2, L))
        total += L
    half = total / 2
    for x1, y1, x2, y2, L in segs:
        if L > 0 and half <= L:
            t = half / L
            return ((x1 + t * (x2 - x1), y1 + t * (y2 - y1)),
                    ((x2 - x1) / L, (y2 - y1) / L))
        half -= L
    x1, y1, x2, y2, L = segs[-1]
    L = L or 1.0
    return (((x1 + x2) / 2, (y1 + y2) / 2),
            ((x2 - x1) / L, (y2 - y1) / L))


def _label_offset(mid_x: float, mid_y: float, ux: float, uy: float,
                  labelpos: str, label_w: float, label_h: float,
                  scale: float) -> tuple[float, float]:
    """Top-left (x, y) for the label text box.

    `mid` (default) auto-picks a perpendicular offset so the label sits
    beside the line, never on it: above for horizontal-ish arrows, right
    for vertical-ish. Explicit above/below/left/right use a wider gap so
    they're visibly farther from the arrow than the auto default."""
    gap_auto = max(6.0, 6.0 * scale)
    gap_explicit = max(12.0, 12.0 * scale)
    if labelpos == "above":
        return (mid_x - label_w / 2, mid_y - label_h - gap_explicit)
    if labelpos == "below":
        return (mid_x - label_w / 2, mid_y + gap_explicit)
    if labelpos == "left":
        return (mid_x - label_w - gap_explicit, mid_y - label_h / 2)
    if labelpos == "right":
        return (mid_x + gap_explicit, mid_y - label_h / 2)
    # `mid` — auto perpendicular based on arrow direction.
    if abs(ux) >= abs(uy):
        return (mid_x - label_w / 2, mid_y - label_h - gap_auto)
    return (mid_x + gap_auto, mid_y - label_h / 2)


def _emit_arrow(line: str, nodes: dict[str, dict], brand_dir: Path, *, theme: str = "light", scale: float = 1.0) -> tuple[list[dict], list[dict]]:
    """Emit (stroke_elements, label_elements) for an `arrow` DSL line.

    Strokes are kept separate from labels so the caller can layer strokes
    behind foreground shapes while keeping labels on top.

    See module docstring for the full flag grammar. Default behavior
    (no flags, no ports) matches the canonical Excalidraw straight-line
    edge-to-edge routing. When the polyline passes through a non-endpoint
    node and the user didn't pin `style:` explicitly, the stroke is
    auto-set to `dotted` as a visual cue.
    """
    # Strip 'arrow ' prefix, split on '->'.
    if not line.startswith("arrow"):
        raise ValueError(f"excalidraw_expand: not an arrow line: {line!r}")
    rest = line[len("arrow"):].strip()
    if "->" not in rest:
        raise ValueError(f"excalidraw_expand: bad arrow (no '->'): {line!r}")
    left, right = rest.split("->", 1)
    left = left.strip()
    right_parts = shlex.split(right.strip())
    if not right_parts:
        raise ValueError(f"excalidraw_expand: bad arrow (empty rhs): {line!r}")
    src_id, src_port = _parse_port_spec(left)
    dst_id, dst_port = _parse_port_spec(right_parts[0])

    src = nodes.get(src_id)
    dst = nodes.get(dst_id)
    if not src or not dst:
        raise ValueError(f"excalidraw_expand: arrow refs unknown node: {line!r}")

    via_str: str | None = None
    route = "straight"
    style = "solid"
    style_explicit = False
    color_token = "ink"
    color_explicit = False
    weight = "secondary"
    label: str | None = None
    labelpos = "mid"
    for tok in right_parts[1:]:
        if tok.startswith("via:"):
            via_str = tok.split(":", 1)[1]
        elif tok.startswith("route:"):
            route = tok.split(":", 1)[1]
            if route not in _ROUTE_KINDS:
                raise ValueError(
                    f"excalidraw_expand: arrow route '{route}' not in {sorted(_ROUTE_KINDS)} ({line!r})"
                )
        elif tok.startswith("style:"):
            style = tok.split(":", 1)[1]
            style_explicit = True
            if style not in _STROKE_STYLES:
                raise ValueError(
                    f"excalidraw_expand: arrow style '{style}' not in {sorted(_STROKE_STYLES)} ({line!r})"
                )
        elif tok.startswith("color:"):
            color_token = tok.split(":", 1)[1]
            color_explicit = True
        elif tok.startswith("weight:"):
            weight = tok.split(":", 1)[1]
            if weight not in _STROKE_WEIGHT:
                raise ValueError(
                    f"excalidraw_expand: arrow weight '{weight}' not in "
                    f"{sorted(_STROKE_WEIGHT)} ({line!r})"
                )
        elif tok.startswith("label:"):
            label = tok.split(":", 1)[1].strip('"').replace("\\n", "\n")
        elif tok.startswith("labelpos:"):
            labelpos = tok.split(":", 1)[1]
            if labelpos not in _LABEL_POSITIONS:
                raise ValueError(
                    f"excalidraw_expand: arrow labelpos '{labelpos}' not in "
                    f"{sorted(_LABEL_POSITIONS)} ({line!r})"
                )
        else:
            raise ValueError(
                f"excalidraw_expand: unknown arrow flag {tok!r} in: {line!r}"
            )

    # Resolve waypoints.
    if via_str:
        manual_pts = [
            tuple(float(v) for v in pair.split(","))
            for pair in via_str.split(";") if pair.strip()
        ]
        if not manual_pts:
            raise ValueError(f"excalidraw_expand: arrow via:'' is empty in: {line!r}")
        # Anchor src/dst toward the first/last waypoint when no port is given.
        src_anchor = _port_anchor(src, src_port, ray_target=manual_pts[0])
        dst_anchor = _port_anchor(dst, dst_port, ray_target=manual_pts[-1])
        waypoints = [src_anchor, *manual_pts, dst_anchor]
    elif route == "elbow":
        src_anchor = _port_anchor(src, src_port, ray_target=(dst["x"] + dst["width"] / 2,
                                                              dst["y"] + dst["height"] / 2))
        dst_anchor = _port_anchor(dst, dst_port, ray_target=(src["x"] + src["width"] / 2,
                                                              src["y"] + src["height"] / 2))
        bends = _elbow_waypoints(src_anchor, dst_anchor, src_port, dst_port)
        waypoints = [src_anchor, *bends, dst_anchor]
    else:
        waypoints = _route_arrow(src, dst, src_port, dst_port)

    # Auto-promote to dotted when the arrow crosses a third-party box. The
    # arrow strokes render behind foreground in z-order, so the dotted
    # entry/exit on either side of the covered box reads as "this line
    # passes through here" rather than the arrow appearing to dead-end.
    if not style_explicit and _arrow_crosses_other_boxes(waypoints, src_id, dst_id, nodes):
        style = "dotted"

    ox, oy = waypoints[0]
    points = [[wx - ox, wy - oy] for wx, wy in waypoints]
    # The default arrow ink (`ink`) resolves to the dark background color in
    # `theme dark`, making arrows invisible. Flip the unset default to a
    # brand-stable light token so arrows contrast on the dark canvas; explicit
    # `color:` is always honored.
    if not color_explicit and theme == "dark":
        color_token = "off-white"
    stroke_hex = _resolve_color(color_token, brand_dir)
    stroke_w = max(1, int(round(_STROKE_WEIGHT[weight] * scale)))

    arrow = {
        "id": _new_id(),
        "type": "arrow",
        "x": ox, "y": oy,
        "width": points[-1][0],
        "height": points[-1][1],
        "strokeColor": stroke_hex,
        "strokeWidth": stroke_w,
        "strokeStyle": style,
        "points": points,
        "startBinding": {"elementId": src["id"]},
        "endBinding": {"elementId": dst["id"]},
    }
    strokes: list[dict] = [arrow]
    labels: list[dict] = []
    if label:
        mid_x, mid_y, ux, uy = _clear_label_anchor(waypoints, src_id, dst_id, nodes)
        label_font = max(12, int(round(16 * scale)))
        label_w = max(60, int(round(180 * scale)))
        label_h = max(16, int(round(22 * scale)))
        label_x, label_y = _label_offset(mid_x, mid_y, ux, uy, labelpos,
                                         float(label_w), float(label_h), scale)
        labels.append({
            "id": _new_id(),
            "type": "text",
            "x": int(round(label_x)),
            "y": int(round(label_y)),
            "width": label_w, "height": label_h,
            "text": label,
            "fontSize": label_font,
            "strokeColor": resolve("off-white" if theme == "dark" else "neutral-strong", brand_dir),
            "textAlign": "center",
        })
    return strokes, labels


def _emit_text(line: str, brand_dir: Path, theme: str = "light", *, scale: float = 1.0) -> dict:
    """Free-floating text. Supports `size:<level>` and `color:<token>`.

    Two grammars are accepted (the SVG-DSL `text` uses positional level, this
    one originally only used the `size:<level>` modifier — accept both so
    cross-DSL muscle memory doesn't render the literal word "body"):

      text <id> <x>,<y> "<content>" [size:<level>] [color:<token>]    (canonical)
      text <id> <x>,<y> <level>     "<content>"   [color:<token>]    (SVG-style)

    Recognized levels (size in px / role):
      title    28  bold heading
      subtitle 20  section sub-heading
      eyebrow  12  small uppercase tracker
      body     14  default paragraph
      detail   12  annotation / caption
      mono     13  monospace code
    """
    parts = shlex.split(line)
    size_map = _EXCALIDRAW_TEXT_SIZES
    _, _dsl_id, xy = parts[:3]
    rest = parts[3:]
    level = "body"
    if rest and rest[0] in size_map and len(rest) > 1:
        level = rest.pop(0)
    content = rest[0] if rest else ""
    content = content.replace("\\n", "\n")
    x, y = _parse_xy(xy)
    color_token = None
    for p in rest[1:]:
        if p.startswith("size:"):
            level = p.split(":", 1)[1]
        elif p.startswith("color:"):
            color_token = p.split(":", 1)[1]
    base_size = size_map.get(level, 14)
    size = int(round(base_size * scale))
    font_family = 3 if level == "mono" else 2
    if color_token:
        fill = _resolve_color(color_token, brand_dir)
    else:
        fill = resolve("off-white" if theme == "dark" else "ink", brand_dir)
    return {
        "id": _new_id(),
        "type": "text",
        "x": x, "y": y,
        "text": content,
        "fontSize": size,
        "fontFamily": font_family,
        "textAlign": "left",
        "verticalAlign": "top",
        "strokeColor": fill,
        "backgroundColor": "transparent",
        "lineHeight": 1.25,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m feinschmiede.diagrams.excalidraw_expand")
    parser.add_argument("input", type=Path, help="Path to .exc.dsl source")
    parser.add_argument("--brand", help="Brand override (else @brand directive / FEINSCHLIFF_BRAND / 'feinschliff')")
    parser.add_argument("-o", "--out", type=Path, help="Output .excalidraw path (default: <input>.excalidraw)")
    args = parser.parse_args(argv)

    dsl, directive = strip_brand_directive(args.input.read_text())
    brand_dir = resolve_brand_dir(directive=directive, cli_flag=args.brand)

    out = args.out or args.input.with_name(args.input.name.replace(".exc.dsl", ".excalidraw"))
    out.write_text(expand(dsl, brand_dir))
    print(f"excalidraw_expand: wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
