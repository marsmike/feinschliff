"""Pure-Python Excalidraw → PNG via `rough` + cairosvg.

For each Excalidraw element, generates sketchy SVG paths using the `rough`
package (a Python port of rough.js — same algorithm Excalidraw itself
uses), composes them into a single SVG, then rasterizes via cairosvg.

No browser, no Node, no Bun, no Docker. Pure Python, cross-platform
(Mac / Linux / Windows). Matches the cairosvg + soffice + pdftoppm
dependency family already used elsewhere in feinschliff.

Known fidelity gaps vs the Playwright (real-Excalidraw) backend:
  - freedraw / image / frame element types are skipped with a warning
  - text wrapping is approximate (no browser measureText)
  - elbowed arrows are rendered straight; only the polyline is honored
"""
from __future__ import annotations

import json
import sys
from html import escape
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

import rough

from .brand_bridge import font_fallback_resolvable, resolve_fonts
from .text_metrics import CHAR_WIDTH_EM as _CHAR_WIDTH_EM, char_width_em_for as _char_width_em_for

if TYPE_CHECKING:
    from .brand_bridge import BrandFonts


def render_excalidraw(src: Path, out: Path, *, style: str = "clean",
                      brand_dir: Path | None = None) -> Path:
    """Render `.excalidraw` JSON at `src` to PNG at `out` via rough + cairosvg.

    Style modes (one code path, one set of opt selectors):
      - "clean"   (default): roughness=0 + disableMultiStroke=True, so each
                  shape gets a single deterministic-stroke path. Visually
                  matches the canonical Excalidraw "no roughness" look the
                  upstream plugin enforces as a hard rule.
      - "sketchy": roughness=1 with multi-stroke — whiteboard / hand-drawn
                  aesthetic.

    When brand_dir is supplied, Normal (fontFamily=2) and Code (fontFamily=3)
    text elements use the brand's typographic faces rather than Excalidraw's
    built-in Helvetica/Cascadia defaults (F3). The .excalidraw JSON stays
    upstream-valid — font enums are never mutated, substitution is render-only.
    """
    fonts: BrandFonts | None = None
    if brand_dir is not None:
        fonts = resolve_fonts(brand_dir)
        body_ok = font_fallback_resolvable(
            brand_dir, fonts.primary_body,
            detail="the rough render keeps Excalidraw's default faces.")
        mono_ok = font_fallback_resolvable(
            brand_dir, fonts.primary_mono,
            detail="the rough render keeps Excalidraw's default code face.")
        if not (body_ok and mono_ok):
            fonts = None  # true fallback: render exactly as today

    data = json.loads(src.read_text(encoding="utf-8"))
    elements = [e for e in data.get("elements", []) if not e.get("isDeleted")]
    if not elements:
        raise ValueError(f"render_rough: no elements in {src}")

    elements_by_id = {e["id"]: e for e in elements if "id" in e}
    app_state = data.get("appState", {})
    bg = app_state.get("viewBackgroundColor") or "#ffffff"
    pad = 40
    mn_x, mn_y, mx_x, mx_y = _bbox(elements, fonts)
    canvas_w = int(mx_x - mn_x + pad * 2)
    canvas_h = int(mx_y - mn_y + pad * 2)
    # Shift everything into positive space.
    tx, ty = pad - mn_x, pad - mn_y

    svg = _compose_svg(elements, elements_by_id, canvas_w, canvas_h, tx, ty, bg, style, fonts)

    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out),
                     output_width=canvas_w * 2)
    return out


def _bbox(elements: list[dict], fonts: "BrandFonts | None" = None) -> tuple[float, float, float, float]:
    mn_x = mn_y = float("inf")
    mx_x = mx_y = float("-inf")
    # Refined char-width ratio: use the brand face's measured ratio when
    # available, else the 0.62em heuristic (F4).
    char_em = _char_width_em_for(fonts.primary_body if fonts is not None else None)
    for e in elements:
        x, y = e.get("x", 0), e.get("y", 0)
        w, h = e.get("width", 0), e.get("height", 0)
        if e.get("type") in ("arrow", "line") and "points" in e:
            for px, py in e["points"]:
                mn_x, mn_y = min(mn_x, x + px), min(mn_y, y + py)
                mx_x, mx_y = max(mx_x, x + px), max(mx_y, y + py)
        else:
            # Free-floating text elements have no width/height set, so
            # estimate from fontSize × lineHeight × line-count. Without
            # this, text near the bottom of the canvas falls outside the
            # bbox and the rendered SVG clips mid-glyph.
            if e.get("type") == "text" and not (w or h):
                fs = float(e.get("fontSize", 14))
                lh = float(e.get("lineHeight", 1.25))
                lines = max(1, e.get("text", "").count("\n") + 1)
                h = fs * lh * lines
                # char-width estimate: measured brand-face ratio (F4) or
                # 0.62em heuristic (shared with text_metrics.CHAR_WIDTH_EM)
                w = fs * char_em * max((len(line) for line in e.get("text", "").splitlines() or [""]), default=0)
            mn_x, mn_y = min(mn_x, x), min(mn_y, y)
            mx_x, mx_y = max(mx_x, x + abs(w)), max(mx_y, y + abs(h))
    if mn_x == float("inf"):
        return 0.0, 0.0, 800.0, 600.0
    return mn_x, mn_y, mx_x, mx_y


def _compose_svg(elements, by_id, w, h, tx, ty, bg, style: str = "clean",
                 fonts: "BrandFonts | None" = None) -> str:
    g = rough.RoughGenerator()
    body = [f'<rect x="0" y="0" width="{w}" height="{h}" fill="{bg}"/>']

    # First pass: shapes, lines, arrows (back layer).
    for e in elements:
        kind = e.get("type")
        if kind == "rectangle":
            body.append(_emit_rect(g, e, tx, ty, style))
        elif kind == "ellipse":
            body.append(_emit_ellipse(g, e, tx, ty, style))
        elif kind == "diamond":
            body.append(_emit_diamond(g, e, tx, ty, style))
        elif kind == "arrow":
            body.append(_emit_arrow(g, e, tx, ty, style))
        elif kind == "line":
            body.append(_emit_line(g, e, tx, ty, style))
        elif kind == "text":
            continue  # second pass below — text on top
        elif kind in ("freedraw", "image", "frame", "embeddable"):
            raise NotImplementedError(
                f"render_rough: element type '{kind}' not modelled by the rough "
                f"path; falling back to Playwright."
            )
        else:
            # Unknown element types must escalate, not silently skip. The
            # dispatcher in render.py catches NotImplementedError and tries
            # the Playwright fallback, which runs the real Excalidraw web app.
            raise NotImplementedError(
                f"render_rough: unknown excalidraw element type {kind!r}"
            )

    # Second pass: text (top layer, after all shapes).
    for e in elements:
        if e.get("type") == "text":
            body.append(_emit_text(e, by_id, tx, ty, fonts))

    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        f'{"".join(body)}'
        f'</svg>'
    )


def _opts_for(e: dict, style: str = "clean") -> rough.Options:
    bg = e.get("backgroundColor") or "transparent"
    fill = None if bg in ("transparent", "") else bg
    fill_style = e.get("fillStyle") or "solid"
    if style == "clean":
        roughness = 0
        disable_multi = True
    else:
        roughness = e.get("roughness") if e.get("roughness") is not None else 1
        disable_multi = False
    return rough.Options(
        fill=fill,
        fillStyle=fill_style,
        stroke=e.get("strokeColor") or "#000000",
        strokeWidth=e.get("strokeWidth") or 2,
        roughness=roughness,
        disableMultiStroke=disable_multi,
        disableMultiStrokeFill=disable_multi,
        seed=e.get("seed") or 1,
    )


def _drawable_to_svg(g: rough.RoughGenerator, drawable, opts: rough.Options,
                     stroke_style: str = "solid") -> str:
    """Convert a rough.Drawable into one or more SVG <path> elements.

    `stroke_style` (solid|dashed|dotted) is read from the Excalidraw
    element's `strokeStyle` field by the emit helpers and threaded
    through to the outline path here.
    """
    dash_attr = ""
    if stroke_style == "dashed":
        dash_attr = ' stroke-dasharray="8 6"'
    elif stroke_style == "dotted":
        dash_attr = ' stroke-dasharray="2 4"'
    out = []
    for s in drawable.sets:
        d = g.opsToPath(s)
        if s.type == "fillPath":
            fill = opts.fill or "none"
            out.append(f'<path d="{d}" fill="{fill}" stroke="none"/>')
        elif s.type == "fillSketch":
            stroke = opts.fill or opts.stroke
            out.append(
                f'<path d="{d}" fill="none" stroke="{stroke}" '
                f'stroke-width="{max(1, (opts.strokeWidth or 2) - 1)}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )
        else:  # 'path' — the outline
            out.append(
                f'<path d="{d}" fill="none" stroke="{opts.stroke}" '
                f'stroke-width="{opts.strokeWidth}" '
                f'stroke-linecap="round" stroke-linejoin="round"{dash_attr}/>'
            )
    return "".join(out)


def _emit_rect(g, e, tx, ty, style: str = "clean") -> str:
    x = e.get("x", 0) + tx
    y = e.get("y", 0) + ty
    w = e.get("width", 0)
    h = e.get("height", 0)
    opts = _opts_for(e, style)
    drawable = g.rectangle(x, y, w, h, options=opts)
    return _drawable_to_svg(g, drawable, opts, e.get("strokeStyle", "solid"))


def _emit_ellipse(g, e, tx, ty, style: str = "clean") -> str:
    x = e.get("x", 0) + tx
    y = e.get("y", 0) + ty
    w = e.get("width", 0)
    h = e.get("height", 0)
    opts = _opts_for(e, style)
    drawable = g.ellipse(x + w / 2, y + h / 2, w, h, options=opts)
    return _drawable_to_svg(g, drawable, opts, e.get("strokeStyle", "solid"))


def _emit_diamond(g, e, tx, ty, style: str = "clean") -> str:
    """Decision-shape (Excalidraw `diamond`) — 4-point polygon."""
    x = e.get("x", 0) + tx
    y = e.get("y", 0) + ty
    w = e.get("width", 0)
    h = e.get("height", 0)
    pts = [
        [x + w / 2, y],            # top
        [x + w,     y + h / 2],    # right
        [x + w / 2, y + h],        # bottom
        [x,         y + h / 2],    # left
    ]
    opts = _opts_for(e, style)
    drawable = g.polygon(pts, options=opts)
    return _drawable_to_svg(g, drawable, opts, e.get("strokeStyle", "solid"))


def _emit_line(g, e, tx, ty, style: str = "clean") -> str:
    x = e.get("x", 0) + tx
    y = e.get("y", 0) + ty
    points = e.get("points") or [[0, 0], [e.get("width", 0), e.get("height", 0)]]
    if len(points) < 2:
        return ""
    src_opts = _opts_for(e, style)
    # Disable fill on lines.
    opts = rough.Options(
        fill=None,
        stroke=src_opts.stroke,
        strokeWidth=src_opts.strokeWidth,
        roughness=src_opts.roughness,
        disableMultiStroke=src_opts.disableMultiStroke,
        seed=src_opts.seed,
    )
    stroke_style = e.get("strokeStyle", "solid")
    out = []
    for (px1, py1), (px2, py2) in pairwise(points):
        drawable = g.line(x + px1, y + py1, x + px2, y + py2, options=opts)
        out.append(_drawable_to_svg(g, drawable, opts, stroke_style))
    return "".join(out)


def _emit_arrow(g, e, tx, ty, style: str = "clean") -> str:
    """Arrow = polyline + arrowhead on the final segment."""
    body = _emit_line(g, e, tx, ty, style)
    points = e.get("points") or [[0, 0], [e.get("width", 0), e.get("height", 0)]]
    if len(points) < 2:
        return body
    x = e.get("x", 0) + tx
    y = e.get("y", 0) + ty
    # Last segment direction → arrowhead.
    (px1, py1), (px2, py2) = points[-2], points[-1]
    head = _arrowhead(x + px1, y + py1, x + px2, y + py2,
                      e.get("strokeColor") or "#000000",
                      e.get("strokeWidth") or 2)
    return body + head


def _arrowhead(x1: float, y1: float, x2: float, y2: float,
               stroke: str, sw: float) -> str:
    """Draw a small filled-triangle arrowhead pointing from (x1,y1) → (x2,y2)."""
    import math
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    ux, uy = dx / length, dy / length
    head_len = max(10.0, sw * 4)
    head_w = head_len * 0.6
    bx, by = x2 - ux * head_len, y2 - uy * head_len
    # Perpendicular
    perp_x, perp_y = -uy, ux
    p1 = (bx + perp_x * head_w / 2, by + perp_y * head_w / 2)
    p2 = (bx - perp_x * head_w / 2, by - perp_y * head_w / 2)
    pts = f"{x2},{y2} {p1[0]:.2f},{p1[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}"
    return f'<polygon points="{pts}" fill="{stroke}" stroke="{stroke}" stroke-linejoin="round"/>'


def _emit_text(e: dict, by_id: dict, tx: float, ty: float,
               fonts: "BrandFonts | None" = None) -> str:
    text = e.get("text") or ""
    fs = e.get("fontSize") or 16
    fill = e.get("strokeColor") or "#000000"
    font = _font_family_name(e.get("fontFamily"), fonts)
    lines = text.split("\n") if "\n" in text else [text]
    line_h = fs * 1.2

    container_id = e.get("containerId")
    if container_id and container_id in by_id:
        c = by_id[container_id]
        cx = c.get("x", 0) + tx + c.get("width", 0) / 2
        cy_center = c.get("y", 0) + ty + c.get("height", 0) / 2 + fs * 0.35
        top_y = cy_center - line_h * (len(lines) - 1) / 2
        tspans = "".join(
            f'<tspan x="{cx}" y="{top_y + i * line_h}">{escape(ln)}</tspan>'
            for i, ln in enumerate(lines)
        )
        return (
            f'<text font-size="{fs}" fill="{fill}" font-family="{font}" '
            f'text-anchor="middle">{tspans}</text>'
        )

    # Free-floating text (typically arrow labels / annotations). Top-left
    # anchor. Rendered semibold so the typographically-small labels survive
    # the 4–8× downscale into the slide's diagram slot — at the natural
    # 16-px Excalidraw text size with no weight, the canonical Helvetica
    # glyphs anti-alias to a faint stem that disappears against busy
    # backgrounds. Semibold (font-weight=600) restores enough optical
    # density to read clearly post-downscale.
    x = e.get("x", 0) + tx
    y0 = e.get("y", 0) + ty + fs
    tspans = "".join(
        f'<tspan x="{x}" y="{y0 + i * line_h}">{escape(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )
    return (
        f'<text font-size="{fs}" fill="{fill}" font-family="{font}" '
        f'font-weight="600">{tspans}</text>'
    )


def _font_family_name(idx, fonts: "BrandFonts | None" = None) -> str:
    """Map an Excalidraw fontFamily index to a CSS stack. With brand fonts
    resolved (F3), 'Normal' (2) and 'Code' (3) take the brand faces; the
    hand-drawn face (1) stays Excalidraw's own."""
    if fonts is not None:
        if (idx or 2) == 2 and fonts.primary_body is not None:
            return fonts.svg_body
        if idx == 3 and fonts.primary_mono is not None:
            return fonts.svg_mono
    return {
        1: "Virgil, Cascadia, sans-serif",       # Excalidraw "hand-drawn"
        2: "Helvetica, Arial, sans-serif",       # "Normal"
        3: "Cascadia, monospace",                # "Code"
    }.get(idx or 2, "Helvetica, Arial, sans-serif")
