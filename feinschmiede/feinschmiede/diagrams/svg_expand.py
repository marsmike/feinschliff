"""Expand SVG DSL into full SVG markup using active brand tokens.

DSL grammar (one statement per line, # for comments):

  canvas <W>x<H>

  # Basic primitives (legacy):
  rect   <id> <x>,<y> <w>x<h> <color>           [label:"<text>"]
  circle <id> <cx>,<cy> <r>   <color>           [label:"<text>"]
  line   <id> <x1>,<y1> <x2>,<y2> [<color>] [dashed]
  text   <id> <x>,<y>   <level> "<content>"
  bar    <id> <x>,<y>   <w>x<h> <color>         [value:"<v>"]
  axis   <id> horizontal|vertical <x>,<y> <length> "<labels>"
  legend <id> <x>,<y>   <color>:"<label>" [<color>:"<label>" ...]

  # Extended primitives (deep diagrams):
  group     <id> [transform:translate(dx,dy)]   # opens a <g>; close with endgroup
  endgroup                                       # closes the most recent group

  polyline <id> <x,y> <x,y> ... [stroke:<token>] [stroke-width:<n>] [dashed]
  polygon  <id> <x,y> <x,y> ... [stroke:<token>] [fill:<token>] [stroke-width:<n>]

  path     <id> "<d>"   [stroke:<token>] [fill:<token>] [stroke-width:<n>] [dashed]
            # d is restricted to SVG path commands M L H V C Q T A S Z (+ lowercase)
            # plus digits / whitespace / comma / period / minus. Other content
            # rejected at parse time so the DSL cannot smuggle <script>, style=, etc.

  area     <id> <x,y> <x,y> ... baseline:<y> [fill:<token>] [stroke:<token>]
            # Filled trend chart — polyline closed at the baseline.

  stacked_bar <id> <x,y> <w>x<h> orient:vertical|horizontal \
                  segments:<v1,token1>;<v2,token2>;...
            # Categorical stacked bar; segments sum-normalise to fill (w x h).

  brace    <id> from:<x,y> to:<x,y> side:left|right|top|bottom \
                depth:<n> ["<label>"] [stroke:<token>]
            # Curly bracket annotation. Side = which side the curls face.

  callout  <id> anchor:<x,y> at:<x,y> <w>x<h> "<text>" \
                [tail:auto|none] [fill:<token>]
            # Bubble at (at:); tail points at (anchor:). Tail auto by default.

  swatch_grid <id> <x,y> cols:<n> \
                  swatches:<token1,label1>;<token2,label2>;...
            # Legend / palette grid; each cell = small swatch + label.

  label_box <id> <x,y> <w>x<h> "<text>" [variant:title|subtitle|body|detail] \
                 [fill:<token>] [stroke:<token>]
            # Labeled box; saves the rect+text idiom in two thirds the tokens.

All <color> tokens go through brand_bridge.resolve() — literal hex rejected.
Points lists for polyline/polygon/area are bounded to 2..64 elements.
"""
from __future__ import annotations

import re
import shlex
from pathlib import Path

from ._dsl_common import (
    Canvas as _Canvas,
    canvas_scale as _canvas_scale,
    parse_canvas as _parse_canvas,
    parse_wh as _parse_wh,
    parse_xy as _parse_xy,
    scaled_int as _sz,
)
from .brand_bridge import label_color_for as _label_color_for, resolve, resolve_brand_dir, strip_brand_directive
from .text_metrics import SVG_TEXT_SIZES as _SVG_TEXT_SIZES


# SVG path `d` attribute allowlist. Letters allow the canonical command set
# (move / line / horizontal / vertical / cubic / smooth / quadratic / tangent /
# arc / close) plus their lowercase relative variants. Numerics and structural
# punctuation are also allowed. Anything else (e.g. `<`, `;`, `style=`) trips
# the validator at parse time.
_PATH_D_ALLOWED = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9eE\s,\.\+\-]*$")
_MAX_POLY_POINTS = 64


def expand(dsl: str, brand_dir: Path, canvas_override: tuple[int, int] | None = None) -> str:
    """DSL → SVG string. canvas_override allows the slide-embed path to inject WxH."""
    canvas: _Canvas | None = None
    body: list[str] = []
    group_stack: list[str] = []  # ids of open groups, for balanced-close enforcement

    # Pre-scan for canvas width so font scaling is known before any primitive
    # is emitted. Override takes precedence when set.
    if canvas_override:
        canvas_w_for_scale = canvas_override[0]
    else:
        canvas_w_for_scale = None
        for raw in dsl.splitlines():
            s = raw.strip()
            if s.startswith("canvas"):
                m = re.match(r"canvas\s+(\d+)x(\d+)", s)
                if m:
                    canvas_w_for_scale = int(m.group(1))
                    break
    scale = _canvas_scale(canvas_w_for_scale)

    for raw in dsl.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        head, *_ = line.split(maxsplit=1)
        if head == "canvas":
            if canvas_override:
                continue
            canvas = _parse_canvas(line)
        elif head == "rect":
            body.append(_emit_rect(line, brand_dir, scale=scale))
        elif head == "text":
            body.append(_emit_text(line, brand_dir, scale=scale))
        elif head == "bar":
            body.append(_emit_bar(line, brand_dir, scale=scale))
        elif head == "axis":
            body.append(_emit_axis(line, brand_dir, scale=scale))
        elif head == "legend":
            body.append(_emit_legend(line, brand_dir, scale=scale))
        elif head == "circle":
            body.append(_emit_circle(line, brand_dir, scale=scale))
        elif head == "ellipse":
            body.append(_emit_ellipse(line, brand_dir, scale=scale))
        elif head == "line":
            body.append(_emit_line(line, brand_dir, scale=scale))
        elif head == "group":
            group_id = _open_group(line, body)
            group_stack.append(group_id)
        elif head == "endgroup":
            if not group_stack:
                raise ValueError("svg_expand: `endgroup` without matching `group`")
            group_stack.pop()
            body.append("</g>")
        elif head == "polyline":
            body.append(_emit_polyline(line, brand_dir, scale=scale))
        elif head == "polygon":
            body.append(_emit_polygon(line, brand_dir, scale=scale))
        elif head == "path":
            body.append(_emit_path(line, brand_dir, scale=scale))
        elif head == "area":
            body.append(_emit_area(line, brand_dir, scale=scale))
        elif head == "stacked_bar":
            body.append(_emit_stacked_bar(line, brand_dir))
        elif head == "brace":
            body.append(_emit_brace(line, brand_dir, scale=scale))
        elif head == "callout":
            body.append(_emit_callout(line, brand_dir, scale=scale))
        elif head == "swatch_grid":
            body.append(_emit_swatch_grid(line, brand_dir, scale=scale))
        elif head == "label_box":
            body.append(_emit_label_box(line, brand_dir, scale=scale))
        else:
            raise ValueError(f"svg_expand: unknown primitive '{head}'")

    if group_stack:
        raise ValueError(
            f"svg_expand: {len(group_stack)} unclosed group(s): {group_stack}"
        )

    if canvas_override:
        canvas = _Canvas(*canvas_override)
    if canvas is None:
        raise ValueError("svg_expand: missing canvas declaration")

    return _wrap_svg(canvas, body)


def _emit_rect(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id, xy, wh, color = parts[:5]
    x, y = _parse_xy(xy)
    w, h = _parse_wh(wh)
    fill = resolve(color, brand_dir)
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>']
    label = _extract_label(parts[5:])
    if label:
        ink = _label_color_for(fill, brand_dir)
        out.append(
            f'<text x="{x + w/2}" y="{y + h/2 + 4}" font-size="{_sz(13, scale)}" '
            f'text-anchor="middle" fill="{ink}" '
            f'font-family="sans-serif">{_escape(label)}</text>'
        )
    return "".join(out)


def _emit_text(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id, xy, level, content = parts[:5]
    x, y = _parse_xy(xy)
    size = _sz(_SVG_TEXT_SIZES.get(level, 14), scale)
    fill = resolve("ink", brand_dir)
    # Optional flags: align:start|middle|end (CSS text-anchor) and
    # color:<token> (override ink default for tonal hierarchy).
    anchor = "start"
    for p in parts[5:]:
        if p.startswith("align:"):
            v = p.split(":", 1)[1]
            anchor = {"left": "start", "center": "middle", "right": "end"}.get(v, v)
        elif p.startswith("color:"):
            fill = resolve(p.split(":", 1)[1], brand_dir)
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-family="sans-serif">{_escape(content)}</text>'
    )


def _emit_bar(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id, xy, wh, color = parts[:5]
    x, y = _parse_xy(xy)
    w, h = _parse_wh(wh)
    fill = resolve(color, brand_dir)
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" rx="2"/>']
    for p in parts[5:]:
        if p.startswith("value:"):
            v = p.split(":", 1)[1].strip('"')
            ink = resolve("ink", brand_dir)
            out.append(
                f'<text x="{x + w//2}" y="{y - 6}" font-size="{_sz(12, scale)}" '
                f'text-anchor="middle" fill="{ink}" '
                f'font-family="sans-serif">{_escape(v)}</text>'
            )
    return "".join(out)


def _emit_axis(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id, orient, xy, length, labels = parts[:6]
    x, y = _parse_xy(xy)
    L = int(length)
    stroke = resolve("neutral", brand_dir)
    label_list = [s.strip() for s in labels.split(",")]
    if orient == "horizontal":
        out = [f'<line x1="{x}" y1="{y}" x2="{x+L}" y2="{y}" stroke="{stroke}" stroke-width="{_sz(1, scale)}"/>']
        if label_list:
            step = L // max(len(label_list), 1)
            offset = _sz(18, scale)
            for i, lab in enumerate(label_list):
                tx = x + step * i + step // 2
                ink = resolve("ink", brand_dir)
                out.append(
                    f'<text x="{tx}" y="{y + offset}" font-size="{_sz(11, scale)}" '
                    f'text-anchor="middle" fill="{ink}" '
                    f'font-family="sans-serif">{_escape(lab)}</text>'
                )
        return "".join(out)
    out = [f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-L}" stroke="{stroke}" stroke-width="{_sz(1, scale)}"/>']
    return "".join(out)


def _emit_legend(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id, xy = parts[:3]
    x, y = _parse_xy(xy)
    out: list[str] = []
    cx = x
    swatch = _sz(12, scale)
    label_inset = _sz(18, scale)
    column_stride = _sz(90, scale)
    label_y_offset = _sz(10, scale)
    for entry in parts[3:]:
        color, label = entry.split(":", 1)
        fill = resolve(color, brand_dir)
        ink = resolve("ink", brand_dir)
        label = label.strip('"')
        out.append(f'<rect x="{cx}" y="{y - label_y_offset}" width="{swatch}" height="{swatch}" fill="{fill}"/>')
        out.append(
            f'<text x="{cx + label_inset}" y="{y}" font-size="{_sz(11, scale)}" fill="{ink}" '
            f'font-family="sans-serif">{_escape(label)}</text>'
        )
        cx += column_stride
    return "".join(out)


def _emit_circle(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id, cxy, r, color = parts[:5]
    cx, cy = _parse_xy(cxy)
    fill = resolve(color, brand_dir)
    out = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>']
    label = _extract_label(parts[5:])
    if label:
        ink = _label_color_for(fill, brand_dir)
        out.append(
            f'<text x="{cx}" y="{cy + 4}" font-size="{_sz(13, scale)}" '
            f'text-anchor="middle" fill="{ink}" '
            f'font-family="sans-serif">{_escape(label)}</text>'
        )
    return "".join(out)


def _emit_ellipse(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    """ellipse <id> <cx>,<cy> <rx>x<ry> <color> [label:"..."]

    Useful for cloud / blob shapes where a circle's 1:1 aspect ratio is
    too rigid. Width/height are RADII (not full extents): an ellipse with
    `200x100` spans 400 wide × 200 tall.
    """
    parts = shlex.split(line)
    _, _id, cxy, rxy, color = parts[:5]
    cx, cy = _parse_xy(cxy)
    rx, ry = _parse_wh(rxy)
    fill = resolve(color, brand_dir)
    out = [f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"/>']
    label = _extract_label(parts[5:])
    if label:
        ink = _label_color_for(fill, brand_dir)
        out.append(
            f'<text x="{cx}" y="{cy + 4}" font-size="{_sz(13, scale)}" '
            f'text-anchor="middle" fill="{ink}" '
            f'font-family="sans-serif">{_escape(label)}</text>'
        )
    return "".join(out)


def _emit_line(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id, xy1, xy2 = parts[:4]
    x1, y1 = _parse_xy(xy1)
    x2, y2 = _parse_xy(xy2)
    color_token = "neutral"
    is_dashed = False
    for tok in parts[4:]:
        if tok == "dashed":
            is_dashed = True
        else:
            color_token = tok
    stroke = resolve(color_token, brand_dir)
    dash = ' stroke-dasharray="4 4"' if is_dashed else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{_sz(2, scale)}"{dash}/>'


# ============================================================================
# Extended primitives — added for deep diagrams (Tier B). See docstring above
# for the full grammar reference.
# ============================================================================

def _open_group(line: str, body: list[str]) -> str:
    """`group <id> [transform:translate(dx,dy)]` → emits the opening `<g>` tag.

    The body holds the partial `<g>` open; `endgroup` emits `</g>`.
    Returns the group id so callers can track balanced open/close.
    """
    parts = shlex.split(line)
    if len(parts) < 2:
        raise ValueError(f"svg_expand: group needs at least an id: {line!r}")
    _, gid = parts[:2]
    transform = ""
    for p in parts[2:]:
        if p.startswith("transform:"):
            t = p.split(":", 1)[1]
            # Allow only translate(...) and rotate(...) — keeps the surface small.
            if not re.match(r"^(translate|rotate)\([^<>'\"]+\)$", t):
                raise ValueError(
                    f"svg_expand: group transform '{t}' must match "
                    f"`translate(dx,dy)` or `rotate(deg[,cx,cy])`"
                )
            transform = f' transform="{t}"'
    body.append(f'<g id="{_escape(gid)}"{transform}>')
    return gid


def _collect_points(tokens: list[str]) -> tuple[list[tuple[float, float]], list[str]]:
    """Split tokens into (points, remaining_attrs).

    A point is any token matching `<float>,<float>`. Attributes (key:value)
    or bare flag tokens come after the points block ends.
    """
    pt_re = re.compile(r"^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$")
    points: list[tuple[float, float]] = []
    i = 0
    while i < len(tokens) and pt_re.match(tokens[i]):
        x, y = tokens[i].split(",")
        points.append((float(x), float(y)))
        i += 1
    if not (2 <= len(points) <= _MAX_POLY_POINTS):
        raise ValueError(
            f"svg_expand: need 2..{_MAX_POLY_POINTS} points, got {len(points)}"
        )
    return points, tokens[i:]


def _attr_dict(tokens: list[str], allowed: set[str]) -> dict[str, str]:
    """Parse `key:value` tokens and bare flag tokens into a dict.

    Bare flags (no `:`) are stored as `flag -> "true"`. Unknown keys
    raise — defensive against typos like `strok:` instead of `stroke:`.
    """
    out: dict[str, str] = {}
    for tok in tokens:
        if ":" in tok:
            k, v = tok.split(":", 1)
            if k not in allowed:
                raise ValueError(
                    f"svg_expand: unknown attribute '{k}'; allowed: {sorted(allowed)}"
                )
            out[k] = v
        else:
            if tok not in allowed:
                raise ValueError(
                    f"svg_expand: unknown flag '{tok}'; allowed: {sorted(allowed)}"
                )
            out[tok] = "true"
    return out


def _is_attr_token(tok: str, allowed: set[str]) -> bool:
    """True if `tok` looks like an attribute candidate.

    Used by primitives that take a free-form label *plus* attributes —
    shlex strips quotes, so we can't tell a label from a bare flag just
    by surface form. The label is then the leftover after filtering
    attribute-looking tokens.

    Any token containing `:` is treated as an attribute candidate so
    `_attr_dict` can validate the key and raise a clear "unknown
    attribute" error for typos. Bare flag tokens must already be in the
    allowed set to count as attributes (otherwise they're treated as
    label text — bare tokens are too ambiguous to validate further).
    """
    if ":" in tok:
        return True
    return tok in allowed


_WH_RE = re.compile(r"^\d+x\d+$")


def _is_wh_token(tok: str) -> bool:
    """True if `tok` is a bare `<w>x<h>` numeric token."""
    return bool(_WH_RE.match(tok))


def _resolve_stroke_width(attrs: dict[str, str], default: float, scale: float) -> str:
    """Return the stroke-width attribute value, honoring the author's
    explicit `stroke-width:` if any, else scaling the default."""
    if "stroke-width" in attrs:
        # Trust the author's explicit value; they've thought about scale.
        return attrs["stroke-width"]
    return str(_sz(default, scale))


def _emit_polyline(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id = parts[:2]
    points, rest = _collect_points(parts[2:])
    attrs = _attr_dict(rest, allowed={"stroke", "stroke-width", "dashed", "fill"})
    stroke = resolve(attrs.get("stroke", "neutral-strong"), brand_dir)
    fill = resolve(attrs["fill"], brand_dir) if "fill" in attrs else "none"
    sw = _resolve_stroke_width(attrs, 2, scale)
    dash = ' stroke-dasharray="6 4"' if attrs.get("dashed") == "true" else ""
    pts = " ".join(f"{x},{y}" for x, y in points)
    return (
        f'<polyline points="{pts}" stroke="{stroke}" fill="{fill}" '
        f'stroke-width="{sw}"{dash}/>'
    )


def _emit_polygon(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id = parts[:2]
    points, rest = _collect_points(parts[2:])
    attrs = _attr_dict(rest, allowed={"stroke", "stroke-width", "fill"})
    stroke = resolve(attrs.get("stroke", "neutral-strong"), brand_dir)
    fill = resolve(attrs.get("fill", "surface-2"), brand_dir)
    sw = _resolve_stroke_width(attrs, 2, scale)
    pts = " ".join(f"{x},{y}" for x, y in points)
    return (
        f'<polygon points="{pts}" stroke="{stroke}" fill="{fill}" '
        f'stroke-width="{sw}"/>'
    )


def _emit_path(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    parts = shlex.split(line)
    _, _id = parts[:2]
    if not parts[2:]:
        raise ValueError(f"svg_expand: path needs a `d` attribute: {line!r}")
    d_raw = parts[2]
    d = d_raw
    if not _PATH_D_ALLOWED.match(d):
        raise ValueError(
            f"svg_expand: path d='{d}' contains characters outside the "
            f"allowed command/numeric set — see _PATH_D_ALLOWED"
        )
    attrs = _attr_dict(parts[3:], allowed={"stroke", "stroke-width", "fill", "dashed"})
    stroke = resolve(attrs.get("stroke", "ink"), brand_dir)
    fill = resolve(attrs["fill"], brand_dir) if "fill" in attrs else "none"
    sw = _resolve_stroke_width(attrs, 2, scale)
    dash = ' stroke-dasharray="6 4"' if attrs.get("dashed") == "true" else ""
    return (
        f'<path d="{d}" stroke="{stroke}" fill="{fill}" '
        f'stroke-width="{sw}"{dash}/>'
    )


def _emit_area(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    """Filled trend chart: polyline closed at baseline.

    `baseline:<y>` is required and sets the closing horizontal line.
    Emitted as a `<polygon>` so it gets one fill and one stroke.
    """
    parts = shlex.split(line)
    _, _id = parts[:2]
    points, rest = _collect_points(parts[2:])
    baseline_val: float | None = None
    other: list[str] = []
    for tok in rest:
        if tok.startswith("baseline:"):
            baseline_val = float(tok.split(":", 1)[1])
        else:
            other.append(tok)
    if baseline_val is None:
        raise ValueError(f"svg_expand: area needs `baseline:<y>`: {line!r}")
    attrs = _attr_dict(other, allowed={"stroke", "stroke-width", "fill"})
    stroke = resolve(attrs.get("stroke", "primary"), brand_dir)
    fill = resolve(attrs.get("fill", "primary"), brand_dir)
    sw = _resolve_stroke_width(attrs, 2, scale)
    # Polygon points: line points + (last x, baseline) + (first x, baseline)
    poly = list(points)
    poly.append((points[-1][0], baseline_val))
    poly.append((points[0][0], baseline_val))
    pts = " ".join(f"{x},{y}" for x, y in poly)
    return (
        f'<polygon points="{pts}" stroke="{stroke}" fill="{fill}" '
        f'stroke-width="{sw}" fill-opacity="0.35"/>'
    )


def _emit_stacked_bar(line: str, brand_dir: Path) -> str:
    """Stacked categorical bar.

    `segments:<v1,token1>;<v2,token2>;...` — segment values sum-normalise to
    fill the (w, h) bbox. `orient:vertical` stacks bottom-to-top;
    `orient:horizontal` stacks left-to-right.
    """
    parts = shlex.split(line)
    _, _id, xy, wh = parts[:4]
    x, y = _parse_xy(xy)
    w, h = _parse_wh(wh)
    attrs = _attr_dict(parts[4:], allowed={"orient", "segments"})
    if "segments" not in attrs:
        raise ValueError(f"svg_expand: stacked_bar needs `segments:`: {line!r}")
    orient = attrs.get("orient", "vertical")
    if orient not in ("vertical", "horizontal"):
        raise ValueError(
            f"svg_expand: stacked_bar orient must be vertical|horizontal, got {orient!r}"
        )
    raw_segs = [s.strip() for s in attrs["segments"].split(";") if s.strip()]
    segs: list[tuple[float, str]] = []
    for s in raw_segs:
        if "," not in s:
            raise ValueError(f"svg_expand: stacked_bar segment '{s}' must be value,token")
        val_str, token = s.split(",", 1)
        segs.append((float(val_str), token))
    total = sum(v for v, _ in segs) or 1.0
    out: list[str] = []
    cursor = 0.0
    for val, token in segs:
        frac = val / total
        fill = resolve(token, brand_dir)
        if orient == "vertical":
            seg_h = h * frac
            seg_y = y + h - cursor - seg_h
            out.append(
                f'<rect x="{x}" y="{seg_y:.1f}" width="{w}" height="{seg_h:.1f}" fill="{fill}"/>'
            )
            cursor += seg_h
        else:
            seg_w = w * frac
            seg_x = x + cursor
            out.append(
                f'<rect x="{seg_x:.1f}" y="{y}" width="{seg_w:.1f}" height="{h}" fill="{fill}"/>'
            )
            cursor += seg_w
    return "".join(out)


def _emit_brace(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    """Curly bracket annotation rendered as an SVG path.

    Two cubic curves anchored at from/to and turning toward the labelled
    side, meeting at the midpoint with a small inverted bump. Optional
    label is centered on the outside of the bracket.
    """
    parts = shlex.split(line)
    _, _id = parts[:2]
    rest = parts[2:]
    allowed_attrs = {"from", "to", "side", "depth", "stroke", "stroke-width"}
    label: str | None = None
    attrs_tokens: list[str] = []
    for tok in rest:
        if _is_attr_token(tok, allowed_attrs):
            attrs_tokens.append(tok)
        elif label is None:
            label = tok
        else:
            label = f"{label} {tok}"
    attrs = _attr_dict(attrs_tokens, allowed=allowed_attrs)
    if not {"from", "to", "side", "depth"}.issubset(attrs):
        raise ValueError(
            f"svg_expand: brace needs from:, to:, side:, depth: — got {sorted(attrs)} ({line!r})"
        )
    fx, fy = _parse_xy(attrs["from"])
    tx, ty = _parse_xy(attrs["to"])
    side = attrs["side"]
    if side not in ("left", "right", "top", "bottom"):
        raise ValueError(f"svg_expand: brace side must be left|right|top|bottom: {side!r}")
    depth = float(attrs["depth"])
    stroke = resolve(attrs.get("stroke", "neutral-strong"), brand_dir)
    sw = _resolve_stroke_width(attrs, 2, scale)

    # Midpoint and curl direction.
    mx, my = (fx + tx) / 2, (fy + ty) / 2
    if side == "left":
        ox, oy = -depth, 0
    elif side == "right":
        ox, oy = depth, 0
    elif side == "top":
        ox, oy = 0, -depth
    else:
        ox, oy = 0, depth
    # Path: from -> curve to mid+outward -> curve to to.
    d = (
        f"M {fx},{fy} "
        f"Q {fx + ox},{fy + oy} {mx + ox},{my + oy} "
        f"Q {tx + ox},{ty + oy} {tx},{ty}"
    )
    out = [
        f'<path d="{d}" stroke="{stroke}" stroke-width="{sw}" fill="none"/>'
    ]
    if label:
        # Label sits on the outside of the bracket tip.
        lx = mx + ox * 1.6
        ly = my + oy * 1.6
        ink = resolve("ink", brand_dir)
        out.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{_sz(13, scale)}" '
            f'text-anchor="middle" fill="{ink}" '
            f'font-family="sans-serif">{_escape(label)}</text>'
        )
    return "".join(out)


def _emit_callout(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    """Bubble at `at:` with a tail pointing at `anchor:`.

    Optional inline text fills the bubble. Use to annotate something on
    a chart without crowding the axes.
    """
    parts = shlex.split(line)
    _, _id = parts[:2]
    allowed_attrs = {"anchor", "at", "tail", "fill", "stroke"}
    bubble_text: str | None = None
    attrs_tokens: list[str] = []
    geom_tokens: list[str] = []
    for tok in parts[2:]:
        if _is_attr_token(tok, allowed_attrs):
            attrs_tokens.append(tok)
        elif _is_wh_token(tok):
            geom_tokens.append(tok)
        elif bubble_text is None:
            bubble_text = tok
        else:
            bubble_text = f"{bubble_text} {tok}"
    attrs = _attr_dict(attrs_tokens, allowed=allowed_attrs)
    if not {"anchor", "at"}.issubset(attrs):
        raise ValueError(
            f"svg_expand: callout needs anchor: and at:: {line!r}"
        )
    ax, ay = _parse_xy(attrs["anchor"])
    bx, by = _parse_xy(attrs["at"])
    if not geom_tokens:
        raise ValueError(f"svg_expand: callout needs `<w>x<h>`: {line!r}")
    bw, bh = _parse_wh(geom_tokens[0])
    fill = resolve(attrs.get("fill", "surface-2"), brand_dir)
    stroke = resolve(attrs.get("stroke", "neutral"), brand_dir)
    tail = attrs.get("tail", "auto")

    bubble_sw = _sz(1.5, scale)
    tail_half = _sz(8, scale)
    out = [
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="{_sz(6, scale)}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{bubble_sw}"/>'
    ]
    if tail != "none":
        # Tail attaches to the nearest edge of the bubble facing the anchor.
        cx, cy = bx + bw / 2, by + bh / 2
        # Pick attachment side by which axis dominates.
        if abs(ax - cx) > abs(ay - cy):
            # Horizontal attachment — left or right edge.
            edge_x = bx if ax < cx else bx + bw
            edge_y = cy
        else:
            edge_x = cx
            edge_y = by if ay < cy else by + bh
        # Tail: a small triangle from the edge midpoint to anchor.
        # Offset perpendicular for a wider base, then point.
        if abs(ax - cx) > abs(ay - cy):
            base1 = (edge_x, edge_y - tail_half)
            base2 = (edge_x, edge_y + tail_half)
        else:
            base1 = (edge_x - tail_half, edge_y)
            base2 = (edge_x + tail_half, edge_y)
        pts = f"{base1[0]},{base1[1]} {base2[0]},{base2[1]} {ax},{ay}"
        out.append(
            f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{bubble_sw}"/>'
        )
    if bubble_text:
        ink = _label_color_for(fill, brand_dir)
        out.append(
            f'<text x="{bx + bw/2}" y="{by + bh/2 + 5}" font-size="{_sz(14, scale)}" '
            f'text-anchor="middle" fill="{ink}" '
            f'font-family="sans-serif">{_escape(bubble_text)}</text>'
        )
    return "".join(out)


def _emit_swatch_grid(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    """Legend / palette mosaic.

    `swatches:<token1,label1>;<token2,label2>;...` — each entry becomes a
    small filled rect + label. Laid out in `cols` columns; row height is
    24px, cell width is 160px (sized for readability at slide scale).
    """
    parts = shlex.split(line)
    _, _id, xy = parts[:3]
    x, y = _parse_xy(xy)
    attrs = _attr_dict(parts[3:], allowed={"cols", "swatches", "cell_w", "cell_h"})
    if "swatches" not in attrs:
        raise ValueError(f"svg_expand: swatch_grid needs `swatches:`: {line!r}")
    cols = int(attrs.get("cols", "3"))
    # cell_w/cell_h default scaled to the virtual canvas so labels don't
    # crowd at 4× scale; explicit overrides bypass the scaling.
    cell_w = int(attrs.get("cell_w", str(_sz(160, scale))))
    cell_h = int(attrs.get("cell_h", str(_sz(24, scale))))
    swatch_dim = _sz(14, scale)
    label_inset = _sz(22, scale)
    label_y_offset = _sz(12, scale)
    raw_swatches = [s.strip() for s in attrs["swatches"].split(";") if s.strip()]
    out: list[str] = []
    ink = resolve("ink", brand_dir)
    for i, s in enumerate(raw_swatches):
        if "," not in s:
            raise ValueError(f"svg_expand: swatch '{s}' must be token,label")
        token, label = s.split(",", 1)
        fill = resolve(token.strip(), brand_dir)
        col = i % cols
        row = i // cols
        cx = x + col * cell_w
        cy = y + row * cell_h
        out.append(
            f'<rect x="{cx}" y="{cy}" width="{swatch_dim}" height="{swatch_dim}" fill="{fill}"/>'
        )
        out.append(
            f'<text x="{cx + label_inset}" y="{cy + label_y_offset}" font-size="{_sz(12, scale)}" fill="{ink}" '
            f'font-family="sans-serif">{_escape(label.strip())}</text>'
        )
    return "".join(out)


def _emit_label_box(line: str, brand_dir: Path, *, scale: float = 1.0) -> str:
    """Labeled box — rect + centered single-line text in one primitive.

    The `variant` controls font size: title=22, subtitle=16, body=14, detail=12.
    Saves two tokens vs. emitting a separate `rect` + `text` pair.
    """
    parts = shlex.split(line)
    _, _id, xy, wh = parts[:4]
    x, y = _parse_xy(xy)
    w, h = _parse_wh(wh)
    allowed_attrs = {"variant", "fill", "stroke"}
    label: str | None = None
    attrs_tokens: list[str] = []
    for tok in parts[4:]:
        if _is_attr_token(tok, allowed_attrs):
            attrs_tokens.append(tok)
        elif label is None:
            label = tok
        else:
            label = f"{label} {tok}"
    attrs = _attr_dict(attrs_tokens, allowed=allowed_attrs)
    variant = attrs.get("variant", "body")
    size = _sz(_SVG_TEXT_SIZES.get(variant, 14), scale)
    fill_token = attrs.get("fill", "surface-2")
    stroke_token = attrs.get("stroke", "neutral")
    fill = resolve(fill_token, brand_dir)
    stroke = resolve(stroke_token, brand_dir)
    ink = _label_color_for(fill, brand_dir)
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{_sz(4, scale)}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{_sz(1.5, scale)}"/>'
    ]
    if label:
        out.append(
            f'<text x="{x + w/2}" y="{y + h/2 + size/3}" font-size="{size}" '
            f'text-anchor="middle" fill="{ink}" '
            f'font-family="sans-serif">{_escape(label)}</text>'
        )
    return "".join(out)


def _extract_label(extra_tokens: list[str]) -> str | None:
    """Pull `label:"<text>"` from a tail of shlex-split tokens."""
    for tok in extra_tokens:
        if tok.startswith("label:"):
            return tok.split(":", 1)[1].strip('"')
    return None


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def _wrap_svg(canvas: _Canvas, body: list[str]) -> str:
    inner = "".join(body)
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {canvas.w} {canvas.h}" '
        f'width="{canvas.w}" height="{canvas.h}">{inner}</svg>'
    )


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m feinschliff.diagrams.svg_expand")
    parser.add_argument("input", type=Path, help="Path to .svg.dsl source")
    parser.add_argument("--brand", help="Brand override (else @brand directive / FEINSCHLIFF_BRAND / 'feinschliff')")
    parser.add_argument("-o", "--out", type=Path, help="Output .svg path (default: <input>.svg)")
    args = parser.parse_args(argv)

    dsl, directive = strip_brand_directive(args.input.read_text())
    brand_dir = resolve_brand_dir(directive=directive, cli_flag=args.brand)

    out = args.out or args.input.with_name(args.input.name.replace(".svg.dsl", ".svg"))
    out.write_text(expand(dsl, brand_dir))
    print(f"svg_expand: wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
