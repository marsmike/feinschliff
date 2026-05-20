"""SVG wireframe renderer for Feinschliff DSL layouts.

Renders a post-expansion primitive list as annotated SVG bounding boxes.
Produces a deterministic, git-diffable SVG that can be stored as a baseline
and compared against future renders to catch DSL regressions without burning
a full PPTX round-trip.

Color legend:
  text    → amber  (#f59e0b) filled semi-transparent + slot label
  picture → blue   (#3b82f6) filled semi-transparent + diagonal X
  rect    → gray   (#6b7280) outline only (structural backgrounds)
  shape   → gray   (#9ca3af) dashed generic bbox
  line / polyline → graphite (#374151) as-drawn

Overlay mode: pass ``background_png_b64`` to embed a rasterized PPTX slide
behind the wireframe boxes. The overlay makes deviations between DSL intent
and actual rendering immediately visible — text overflows, image crops, and
element misalignment all show up as mismatches between the amber/blue boxes
and the underlying pixels.

Usage::

    from feinschliff.dsl.parser import parse_file
    from feinschliff.dsl.expander import interpolate_nodes, expand_compounds, load_compounds_for_brand
    from feinschliff.dsl.tokens import load_tokens
    from feinschliff_builder.decompile.wireframe import render_wireframe

    nodes, cds = parse_file(layout_path)
    tokens = load_tokens(brand_dir)
    compounds = load_compounds_for_brand(brand_dir, std_dir=..., brands_dir=...)
    for cd in cds:
        compounds[cd.name] = cd
    interp = interpolate_nodes(nodes, ctx)
    primitives, _ = expand_compounds(interp, compounds)
    svg = render_wireframe(primitives, tokens)
    Path("layout.svg").write_text(svg)
"""
from __future__ import annotations

import html
import re
import sys
from collections.abc import Sequence

from feinschliff.dsl.parser import DSLNode, parse_xy, parse_wh
from feinschliff.dsl.tokens import Tokens


# Pattern for detecting unexpanded Jinja placeholders in `if:` guards.
# Mirrors lib/dsl/pptx_emit.py::_RESIDUAL_PLACEHOLDER so both renderers
# treat the same nodes as conditionally suppressed.
_RESIDUAL_PLACEHOLDER = re.compile(r"\{\{[^}]*\}\}")

# Design canvas at which all DSL coordinates are expressed.
_CANVAS_W = 1920.0
_CANVAS_H = 1080.0

# Display size: half-scale so the SVG renders reasonably in browsers.
_DISPLAY_W = 960
_DISPLAY_H = 540

# Colours (hex or rgba for SVG attributes).
_COL_TEXT_FILL = "rgba(245,158,11,0.18)"    # amber semi-transparent
_COL_TEXT_STROKE = "#f59e0b"                 # amber
_COL_TEXT_LABEL = "#92400e"                  # dark amber
_COL_PIC_FILL = "rgba(59,130,246,0.15)"      # blue semi-transparent
_COL_PIC_STROKE = "#3b82f6"                  # blue
_COL_PIC_LABEL = "#1e3a8a"                   # dark blue
_COL_RECT_FILL = "none"
_COL_RECT_STROKE = "#9ca3af"                 # light gray
_COL_SHAPE_STROKE = "#6b7280"                # medium gray for generic shapes
_COL_LINE = "#374151"                        # graphite
_COL_BG = "#f9fafb"                          # near-white canvas background

# Slot extraction: {{ slot_name }}, {{ cells[0].heading }}, etc.
_SLOT_RE = re.compile(r"\{\{([^{}]+)\}\}")

# Base64 sanity check (no XML-significant characters). PNG payloads only.
_B64_RE = re.compile(r"^[A-Za-z0-9+/]+=*$")

# Default single-line height when maxheight is absent and style cannot be resolved.
_DEFAULT_HEIGHT_PX = 40.0


def _warn(msg: str) -> None:
    """Emit a wireframe parse warning to stderr."""
    print(f"svg_wireframe: {msg}", file=sys.stderr)


def _extract_slot_label(label: str | None) -> str | None:
    """Return human-readable slot name from a DSL label string, or None."""
    if not label:
        return None
    matches = _SLOT_RE.findall(label)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0].strip()
    return " + ".join(m.strip() for m in matches)


def _safe(s: str) -> str:
    return html.escape(str(s))


def _is_valid_b64(s: str) -> bool:
    """Conservative base64 well-formedness check (suitable for SVG embedding)."""
    return bool(_B64_RE.fullmatch(s))


def _rect_svg(
    x: float, y: float, w: float, h: float,
    fill: str, stroke: str, stroke_width: float = 2.0,
    rx: float = 0.0,
) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width:.1f}"'
        + (f' rx="{rx:.1f}"' if rx else "") + "/>"
    )


def _label_svg(
    x: float, y: float, text: str, fill: str,
    font_size: float = 18.0,
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="monospace" '
        f'font-size="{font_size:.0f}" fill="{fill}">{_safe(text)}</text>'
    )


def _diagonal_x_svg(
    x: float, y: float, w: float, h: float, stroke: str,
) -> str:
    return (
        f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+w:.1f}" y2="{y+h:.1f}" '
        f'stroke="{stroke}" stroke-width="2"/>'
        f'<line x1="{x+w:.1f}" y1="{y:.1f}" x2="{x:.1f}" y2="{y+h:.1f}" '
        f'stroke="{stroke}" stroke-width="2"/>'
    )


def _default_height(style_name: str, tokens: Tokens | None) -> float:
    """Single-line height estimate from style metadata; falls back to 40px."""
    if tokens is None:
        return _DEFAULT_HEIGHT_PX
    try:
        resolved = tokens.resolve_style(style_name)
        return resolved.size_px * resolved.line_height
    except (KeyError, ValueError, AttributeError):
        return _DEFAULT_HEIGHT_PX


def _render_text_node(node: DSLNode, tokens: Tokens | None) -> list[str]:
    """Render a text primitive as an amber labeled rectangle."""
    if not node.pos_args:
        _warn(f"text node has no pos args; skipping (label={node.label!r})")
        return []
    try:
        x, y = parse_xy(node.pos_args[0])
    except (ValueError, IndexError) as exc:
        _warn(f"text node: bad position {node.pos_args[0]!r}: {exc}")
        return []

    maxwidth_str = node.kw_args.get("maxwidth")
    maxheight_str = node.kw_args.get("maxheight")

    slot_label = _extract_slot_label(node.label)
    display_label = slot_label or (node.label[:40] if node.label else "text")

    parts: list[str] = []

    if maxwidth_str:
        try:
            w = float(maxwidth_str)
        except ValueError:
            _warn(f"text node: bad maxwidth {maxwidth_str!r}; using 400")
            w = 400.0
        if maxheight_str:
            try:
                h = float(maxheight_str)
            except ValueError:
                _warn(f"text node: bad maxheight {maxheight_str!r}; deriving from style")
                h = _default_height(node.kw_args.get("style", "body"), tokens)
        else:
            h = _default_height(node.kw_args.get("style", "body"), tokens)
        parts.append(_rect_svg(x, y, w, h,
                                fill=_COL_TEXT_FILL, stroke=_COL_TEXT_STROKE, rx=4.0))
        # Label inside the box, top-left.
        lx = x + 6
        ly = y + 20
        if ly > y + h:
            ly = y + h / 2
        parts.append(_label_svg(lx, ly, display_label, _COL_TEXT_LABEL))
    else:
        # Unbounded width: draw a small marker cross + label.
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" '
            f'fill="{_COL_TEXT_STROKE}" opacity="0.6"/>'
        )
        parts.append(_label_svg(x + 10, y + 6, display_label, _COL_TEXT_LABEL))

    return parts


def _render_picture_node(node: DSLNode) -> list[str]:
    """Render a picture primitive as a blue box with diagonal X."""
    if len(node.pos_args) < 2:
        _warn(f"picture node needs xy and wh args; skipping (label={node.label!r})")
        return []
    try:
        x, y = parse_xy(node.pos_args[0])
        w, h = parse_wh(node.pos_args[1])
    except (ValueError, IndexError) as exc:
        _warn(f"picture node: bad pos args {node.pos_args!r}: {exc}")
        return []

    slot_label = node.kw_args.get("slot", "image")
    parts = [
        _rect_svg(x, y, w, h, fill=_COL_PIC_FILL, stroke=_COL_PIC_STROKE),
        _diagonal_x_svg(x, y, w, h, stroke=_COL_PIC_STROKE),
        _label_svg(x + 6, y + 20, slot_label, _COL_PIC_LABEL),
    ]
    return parts


def _render_rect_node(node: DSLNode) -> list[str]:
    """Render a rect primitive as a gray outline (structural background)."""
    if len(node.pos_args) < 2:
        _warn("rect node needs xy and wh args; skipping")
        return []
    try:
        x, y = parse_xy(node.pos_args[0])
        w, h = parse_wh(node.pos_args[1])
    except (ValueError, IndexError) as exc:
        _warn(f"rect node: bad pos args {node.pos_args!r}: {exc}")
        return []

    fill_role = node.kw_args.get("fill", "")
    opacity = "0.07" if fill_role else "0"
    return [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="{_COL_RECT_STROKE}" fill-opacity="{opacity}" '
        f'stroke="{_COL_RECT_STROKE}" stroke-width="1.5" stroke-dasharray="6 3"/>'
    ]


def _render_shape_node(node: DSLNode) -> list[str]:
    """Render a generic shape primitive as a gray dashed bounding box."""
    if len(node.pos_args) < 2:
        _warn("shape node needs xy and wh args; skipping")
        return []
    try:
        x, y = parse_xy(node.pos_args[0])
        w, h = parse_wh(node.pos_args[1])
    except (ValueError, IndexError) as exc:
        _warn(f"shape node: bad pos args {node.pos_args!r}: {exc}")
        return []
    shape_kind = node.kw_args.get("kind", node.kw_args.get("type", "shape"))
    return [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'fill="none" stroke="{_COL_SHAPE_STROKE}" stroke-width="1.5" '
        f'stroke-dasharray="8 4"/>',
        _label_svg(x + 6, y + 18, shape_kind, _COL_SHAPE_STROKE, font_size=14.0),
    ]


def _render_line_node(node: DSLNode) -> list[str]:
    """Render a line primitive."""
    if len(node.pos_args) < 2:
        _warn("line node needs two endpoint args; skipping")
        return []
    try:
        x1, y1 = parse_xy(node.pos_args[0])
        x2, y2 = parse_xy(node.pos_args[1])
    except (ValueError, IndexError) as exc:
        _warn(f"line node: bad endpoint {node.pos_args!r}: {exc}")
        return []
    sw_raw = node.kw_args.get("stroke-width", "2")
    try:
        float(sw_raw)
        sw = sw_raw
    except ValueError:
        _warn(f"line node: bad stroke-width {sw_raw!r}; using 2")
        sw = "2"
    return [
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="{_COL_LINE}" stroke-width="{sw}" opacity="0.5"/>'
    ]


def _render_polyline_node(node: DSLNode) -> list[str]:
    """Render a polyline primitive."""
    if len(node.pos_args) < 2:
        _warn("polyline node needs at least two points; skipping")
        return []
    try:
        pts = [parse_xy(p) for p in node.pos_args]
    except (ValueError, IndexError) as exc:
        _warn(f"polyline node: bad point {node.pos_args!r}: {exc}")
        return []
    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return [
        f'<polyline points="{pts_str}" fill="none" '
        f'stroke="{_COL_LINE}" stroke-width="2" opacity="0.5"/>'
    ]


def _build_wireframe_body(
    primitives: Sequence[DSLNode],
    tokens: Tokens | None,
    *,
    title: str,
    background_png_b64: str | None,
    background_opacity: float,
    canvas_w: float,
    canvas_h: float,
    include_legend: bool,
) -> list[str]:
    """Build the inner SVG elements (background, border, primitives, legend).

    Returned lines are placed between the outer ``<svg ...>`` / ``</svg>`` tags
    by both :func:`render_wireframe` and :func:`render_wireframe_sheet`. This
    factoring keeps the two entry points decoupled from each other's wrapping
    boilerplate.
    """
    lines: list[str] = []
    use_overlay = bool(background_png_b64) and _is_valid_b64(background_png_b64)
    if background_png_b64 and not use_overlay:
        _warn("background_png_b64 contains non-base64 characters; skipping overlay")

    if use_overlay:
        lines.append(
            f'<image href="data:image/png;base64,{background_png_b64}" '
            f'x="0" y="0" width="{canvas_w:.0f}" height="{canvas_h:.0f}" '
            f'opacity="{background_opacity:.2f}"/>'
        )
    else:
        lines.append(
            f'<rect width="{canvas_w:.0f}" height="{canvas_h:.0f}" fill="{_COL_BG}"/>'
        )

    lines.append(
        f'<rect width="{canvas_w:.0f}" height="{canvas_h:.0f}" fill="none" '
        f'stroke="#d1d5db" stroke-width="4"/>'
    )

    if title:
        lines.append(
            f'<text x="16" y="30" font-family="monospace" font-size="22" '
            f'fill="#6b7280" opacity="0.7">{_safe(title)}</text>'
        )

    rect_parts: list[str] = []
    overlay_parts: list[str] = []
    for node in primitives:
        # Mirror pptx_emit's `if:` guard. When a Jinja-conditional
        # primitive's guard is empty / "false" / still contains an
        # unexpanded {{ … }} placeholder (because its content key was
        # not supplied), the primitive is dropped before its position
        # args are parsed. Without this, the wireframe parser barfs on
        # the empty-string coords (",608" etc.) produced by Jinja
        # arithmetic on undefined dotted paths like phases[0].from_event.
        cond = node.kw_args.get("if")
        if cond is not None:
            s = cond.strip()
            if not s or s.lower() == "false" or _RESIDUAL_PLACEHOLDER.search(s):
                continue
        kind = node.kind
        if kind == "rect":
            rect_parts.extend(_render_rect_node(node))
        elif kind == "text":
            overlay_parts.extend(_render_text_node(node, tokens))
        elif kind == "picture":
            if "_diagram_meta" in node.kw_args:
                # Diagram-emitted picture node: geometry is in kw_args (not
                # pos_args), so we can't use _render_picture_node directly.
                # Emit the outer region bbox ourselves, then render an inner
                # layer of diagram primitives at their translated slide coords.
                # Slide-authored picture nodes use pos_args and go through
                # _render_picture_node unchanged below.
                try:
                    rx = float(node.kw_args["x"])
                    ry = float(node.kw_args["y"])
                    rw = float(node.kw_args["w"])
                    rh = float(node.kw_args["h"])
                except (KeyError, TypeError, ValueError) as exc:
                    _warn(f"diagram picture node: bad geometry in kw_args: {exc}")
                    continue
                # Outer region: same styling as a regular picture bbox.
                overlay_parts.append(
                    _rect_svg(rx, ry, rw, rh, fill=_COL_PIC_FILL, stroke=_COL_PIC_STROKE)
                )
                overlay_parts.append(_diagonal_x_svg(rx, ry, rw, rh, stroke=_COL_PIC_STROKE))
                meta = node.kw_args["_diagram_meta"]
                diagram_kind = meta.get("kind", "diagram")
                overlay_parts.append(
                    _label_svg(rx + 6, ry + 20, diagram_kind, _COL_PIC_LABEL)
                )
                # Inner primitives layer: translate each primitive into slide
                # coords (offset by the region's x, y) and draw with muted,
                # dashed styling so they're visually distinct from slide-level
                # wireframe elements.
                _INNER_STROKE = {
                    "rect": "#9ca3af",   # gray
                    "text": "#fbbf24",   # amber-300 (softer than slide amber)
                    "line": "#374151",   # graphite
                }
                for prim_dict in meta.get("internal_primitives", []):
                    try:
                        ix = rx + float(prim_dict["x"])
                        iy = ry + float(prim_dict["y"])
                        iw = float(prim_dict["w"])
                        ih = float(prim_dict["h"])
                        prim_kind = prim_dict.get("kind", "rect")
                    except (KeyError, TypeError, ValueError) as exc:
                        _warn(f"diagram picture: bad internal primitive {prim_dict!r}: {exc}")
                        continue
                    stroke = _INNER_STROKE.get(prim_kind, "#9ca3af")
                    overlay_parts.append(
                        f'<rect x="{ix:.1f}" y="{iy:.1f}" '
                        f'width="{iw:.1f}" height="{ih:.1f}" '
                        f'fill="none" stroke="{stroke}" stroke-width="1.5" '
                        f'stroke-dasharray="5 3"/>'
                    )
            else:
                overlay_parts.extend(_render_picture_node(node))
        elif kind == "shape":
            overlay_parts.extend(_render_shape_node(node))
        elif kind == "line":
            overlay_parts.extend(_render_line_node(node))
        elif kind == "polyline":
            overlay_parts.extend(_render_polyline_node(node))
        # canvas/theme/compound-calls: skip

    lines.extend(rect_parts)
    lines.extend(overlay_parts)

    if include_legend:
        lx, ly = 20.0, canvas_h - 60.0
        lines += [
            f'<rect x="{lx:.0f}" y="{ly:.0f}" width="14" height="14" '
            f'fill="{_COL_TEXT_FILL}" stroke="{_COL_TEXT_STROKE}" stroke-width="1.5"/>',
            f'<text x="{lx+20:.0f}" y="{ly+12:.0f}" font-family="sans-serif" '
            f'font-size="16" fill="{_COL_TEXT_LABEL}">text slot</text>',
            f'<rect x="{lx+130:.0f}" y="{ly:.0f}" width="14" height="14" '
            f'fill="{_COL_PIC_FILL}" stroke="{_COL_PIC_STROKE}" stroke-width="1.5"/>',
            f'<text x="{lx+150:.0f}" y="{ly+12:.0f}" font-family="sans-serif" '
            f'font-size="16" fill="{_COL_PIC_LABEL}">image slot</text>',
            f'<rect x="{lx+270:.0f}" y="{ly:.0f}" width="14" height="14" '
            f'fill="none" stroke="{_COL_RECT_STROKE}" stroke-width="1.5" '
            f'stroke-dasharray="4 2"/>',
            f'<text x="{lx+290:.0f}" y="{ly+12:.0f}" font-family="sans-serif" '
            f'font-size="16" fill="#6b7280">rect</text>',
        ]

    return lines


def render_wireframe(
    primitives: Sequence[DSLNode],
    tokens: Tokens | None = None,
    *,
    title: str = "",
    background_png_b64: str | None = None,
    background_opacity: float = 0.55,
    canvas_w: float = _CANVAS_W,
    canvas_h: float = _CANVAS_H,
    display_w: int = _DISPLAY_W,
    display_h: int = _DISPLAY_H,
) -> str:
    """Render *primitives* as an SVG wireframe string.

    Parameters
    ----------
    primitives:
        Post-expansion primitive node list (output of ``expand_compounds``).
    tokens:
        Brand token bundle — used to derive single-line heights for text
        nodes that have no ``maxheight``. Pass ``None`` to use the 40px
        fallback for all unconstrained text boxes.
    title:
        Optional title shown in the SVG for identification.
    background_png_b64:
        Base64-encoded PNG string to embed as a background layer. When
        supplied the wireframe boxes are drawn *on top* of the rasterized
        slide, making deviations between DSL intent and actual PPTX output
        immediately visible. Obtain via
        :func:`feinschliff.io.pptx_to_png.slide_to_b64`. Invalid base64 (anything
        containing characters outside ``A–Za–z0–9+/=``) is rejected with a
        warning to avoid breaking SVG well-formedness.
    background_opacity:
        Opacity of the embedded background PNG (0.0–1.0). Lower values make
        the wireframe boxes more prominent; higher values show more slide
        detail. Default 0.55 balances both.
    canvas_w / canvas_h:
        DSL coordinate space dimensions (design pixels). Default 1920×1080.
    display_w / display_h:
        SVG viewport display size. Default 960×540 (half scale).
    """
    body = _build_wireframe_body(
        primitives, tokens,
        title=title,
        background_png_b64=background_png_b64,
        background_opacity=background_opacity,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        include_legend=True,
    )
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{display_w}" height="{display_h}" '
        f'viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}">',
        *body,
        "</svg>",
    ])


def render_wireframe_sheet(
    slides: list[tuple[list[DSLNode], Tokens | None, str]],
    *,
    columns: int = 4,
    cell_w: float = 480.0,
    cell_h: float = 270.0,
    gap: float = 20.0,
    margin: float = 30.0,
    background_pngs_b64: list[str | None] | None = None,
    canvas_w: float = _CANVAS_W,
    canvas_h: float = _CANVAS_H,
) -> str:
    """Compose multiple wireframes into a single SVG contact sheet.

    Each cell is a nested ``<svg>`` element positioned at its grid coordinate
    and given an explicit ``viewBox`` so primitives scale to the cell. The
    legend is omitted from individual cells (it would shrink to unreadable
    size at half-scale or smaller) and the global sheet header acts as the
    single legend reference.

    Parameters
    ----------
    slides:
        List of ``(primitives, tokens, title)`` triples, one per slide.
        *tokens* may be ``None``; see :func:`render_wireframe`.
    columns:
        How many wireframes per row.
    cell_w / cell_h:
        Display size per wireframe cell (in SVG user units).
    gap:
        Gap between cells.
    margin:
        Outer margin around the grid.
    background_pngs_b64:
        Optional list of per-slide base64 PNG strings for overlay mode.
        Pass ``None`` entries to skip overlay for specific slides. When the
        list is shorter than *slides*, unmatched slides have no overlay.
    canvas_w / canvas_h:
        DSL coordinate space dimensions per cell (design pixels).
    """
    n = len(slides)
    if n == 0:
        return '<svg xmlns="http://www.w3.org/2000/svg"/>'

    rows = (n + columns - 1) // columns
    sheet_w = margin * 2 + columns * cell_w + (columns - 1) * gap
    sheet_h = margin * 2 + rows * cell_h + (rows - 1) * gap + 40  # +40 for header

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{sheet_w:.0f}" height="{sheet_h:.0f}">',
        f'<rect width="{sheet_w:.0f}" height="{sheet_h:.0f}" fill="#f3f4f6"/>',
        f'<text x="{margin:.0f}" y="28" font-family="sans-serif" '
        f'font-size="20" fill="#374151">Wireframe sheet — {n} slide(s)</text>',
    ]

    bg_list = background_pngs_b64 or [None] * n

    for i, (primitives, tokens, title) in enumerate(slides):
        row = i // columns
        col = i % columns
        cx = margin + col * (cell_w + gap)
        cy = margin + 40 + row * (cell_h + gap)
        bg_b64 = bg_list[i] if i < len(bg_list) else None

        body = _build_wireframe_body(
            primitives, tokens,
            title=f"{i+1}. {title}",
            background_png_b64=bg_b64,
            background_opacity=0.55,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            include_legend=False,
        )
        lines.append(
            f'<svg x="{cx:.0f}" y="{cy:.0f}" '
            f'width="{cell_w:.0f}" height="{cell_h:.0f}" '
            f'viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}">'
        )
        lines.extend(body)
        lines.append("</svg>")

    lines.append("</svg>")
    return "\n".join(lines)
