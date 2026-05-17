"""Primitive-AST → python-pptx emitter.

Consumes the post-expansion node list (primitives only) plus a Tokens
bundle, builds a single-slide Presentation, returns it.

Coordinate system: DSL uses design pixels in a 1920×1080 frame, matching
the existing brand-pack convention. We map 1 design-px → 6350 EMU
(same as gs-ramspau's `px()` helper).

Primitives implemented:
  canvas WxH                 — set slide size
  theme <brand>              — no-op here; brand was already picked at load
  text X,Y "label" style:S align:left|right|center maxwidth:W
  rect X,Y WxH fill:role stroke:role stroke-width:N
  line X,Y X2,Y2 stroke:role stroke-width:N
  picture X,Y WxH path:PATH cover:true
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

from .. import textfit
from .parser import DSLNode, parse_xy, parse_wh
from .polish import normalize_text
from .tokens import Tokens


# 1920 design-px → 12,192,000 EMU (PowerPoint widescreen). Hence 6350 EMU/px.
_EMU_PER_PX = 6350           # 914400 EMU/in × (1/144 in/px) — for 1920×1080 slides at 96 DPI
_PX_TO_PT = 0.5              # design-px → typographic pt (2 design-px = 1pt at 1920-wide / 960pt PPT slide)
_STROKE_PX_TO_PT = 0.75      # CSS px → pt for stroke widths (96/72 inverse rounded)
_DEFAULT_PADDING_X = 100     # fallback right/left margin if brand has no slide.padding-x token

# Defense-in-depth: if interpolation somehow left a `{{ … }}` placeholder in
# an `if:` condition, treat it as falsy so the node is suppressed (never
# leaked into the rendered slide as literal text).
_RESIDUAL_PLACEHOLDER = re.compile(r"\{\{[^}]*\}\}")

# Tabular-numeral activation: a run is "numeric" if its content (after polish)
# is purely digits, separators, and numeric signs. Whitespace and Unicode
# minus (U+2212) count as numeric chrome.
_NUMERIC_CONTENT_RE = re.compile(r"^[\d,\.\-−%+\s]+$")

# Glyphs that, when leading a run, hang into the left margin. The bearing
# fraction is approximate (fraction of em — i.e. of font size).
_HANG_SIDE_BEARING_EM: dict[str, float] = {
    "•": 0.45,  # • bullet
    "“": 0.20,  # “ left double quote (en)
    "„": 0.20,  # „ low-9 (de)
    "«": 0.25,  # « left guillemet (fr)
    "—": 0.30,  # — em-dash
    "–": 0.25,  # – en-dash
    "…": 0.15,  # … ellipsis
    "\"":     0.20,  # ASCII straight double (legacy; rare after polish)
    "-":      0.15,  # ASCII hyphen
}


# 3-channel hierarchy stepping for indent levels. Each level beyond 0 steps:
#   size  ×= 0.85   (round to 0.5pt)
#   weight -= 100   (clamped at 300)
#   color  walks ink → graphite → fog (clamped at fog)
_HIERARCHY_COLOR_WALK = ["ink", "graphite", "fog"]


def _step_hierarchy(
    size_px: float, weight: int, color_role: str, *, level: int,
) -> tuple[float, int, str]:
    """Step all three channels for `level` indent levels. level<=0 is a no-op."""
    if level <= 0:
        return size_px, weight, color_role
    new_size = size_px
    new_weight = weight
    new_color = color_role
    for _ in range(level):
        new_size *= 0.85
        new_weight = max(300, new_weight - 100)
        if new_color in _HIERARCHY_COLOR_WALK:
            idx = _HIERARCHY_COLOR_WALK.index(new_color)
            new_color = _HIERARCHY_COLOR_WALK[min(idx + 1, len(_HIERARCHY_COLOR_WALK) - 1)]
    # Round size_pt to nearest 0.5pt. size_px ↔ pt: 2 design-px per pt.
    pt = new_size * _PX_TO_PT
    pt = round(pt * 2) / 2
    new_size = pt / _PX_TO_PT
    return new_size, new_weight, new_color


def _leading_hang_offset_px(text: str, size_pt: float) -> float:
    """Return leftward offset (design-px) for a textbox whose first glyph
    hangs into the margin. Zero if no hang glyph at position 0."""
    if not text:
        return 0.0
    bearing_em = _HANG_SIDE_BEARING_EM.get(text[0], 0.0)
    if bearing_em == 0.0:
        return 0.0
    # 1pt = 2 design-px (the canvas-to-PPT mapping). Em ≈ font size.
    return bearing_em * size_pt / _PX_TO_PT


def _px(n: float) -> Emu:
    return Emu(int(n * _EMU_PER_PX))


@dataclass
class EmitContext:
    tokens: Tokens
    canvas_w: float = 1920.0
    canvas_h: float = 1080.0
    asset_root: Path | None = None        # for resolving picture paths
    # Plugin-level fallback root walked when the per-brand `asset_root` does
    # not contain the requested relative path. Lets shared assets (universal
    # placeholder illustrations, common icons) live once at the plugin root
    # while brands keep the freedom to override per-asset by putting a file
    # at the same relative path under their own `assets/` dir.
    asset_root_fallback: Path | None = None
    # Required-asset accumulator (Review #7). _emit_picture appends an entry
    # for every picture node whose `path` is unset or points at a missing
    # file AND that does not carry `optional:true`. Callers consult this
    # post-build to decide whether to abort.
    missing_assets: list[dict] = field(default_factory=list)


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _align_pp(name: str) -> PP_ALIGN:
    return {
        "left":   PP_ALIGN.LEFT,
        "right":  PP_ALIGN.RIGHT,
        "center": PP_ALIGN.CENTER,
    }.get(name, PP_ALIGN.LEFT)


# ---------------------------------------------------------------------------
# Primitive handlers
# ---------------------------------------------------------------------------

def _emit_text(slide, node: DSLNode, ctx: EmitContext) -> None:
    """text X,Y "label" style:S align:A maxwidth:W maxheight:H color:T autoshrink:true lang:de_DE

    `autoshrink:true` — shrink font from style size down to a 10pt floor until
        the label fits the `maxwidth × maxheight` box. Off by default; preserves
        byte-identical output for layouts that don't opt in.
    `lang:LOCALE` — pyphen locale (e.g. `de_DE`). Inserts U+00AD soft hyphens
        into the label before emission so python-pptx can break long compound
        words at syllable boundaries. Applied BEFORE autoshrink so the shrink
        sees the hyphenated string.
    """
    if not node.pos_args:
        raise ValueError(f"text at line {node.line_no}: expected 'X,Y' positional")
    x, y = parse_xy(node.pos_args[0])
    style_name = node.kw_args.get("style", "body")
    style = ctx.tokens.resolve_style(style_name)
    color_override = node.kw_args.get("color")
    if color_override:
        from dataclasses import replace as _replace
        style = _replace(style, color_hex=ctx.tokens.color(color_override),
                         color_role=color_override)
    # Hierarchy stepping: indent:N steps size/weight/color N times.
    try:
        indent_level = int(node.kw_args.get("indent", "0"))
    except (TypeError, ValueError):
        indent_level = 0
    if indent_level > 0:
        from dataclasses import replace as _replace
        new_size, new_weight, new_color_role = _step_hierarchy(
            style.size_px, style.weight, style.color_role, level=indent_level,
        )
        try:
            new_color_hex = ctx.tokens.color(new_color_role)
        except KeyError:
            new_color_hex = style.color_hex
        style = _replace(
            style,
            size_px=new_size, weight=new_weight,
            color_hex=new_color_hex, color_role=new_color_role,
        )
    align = _align_pp(node.kw_args.get("align", "left"))
    # Default right margin = brand's slide.padding-x token; fall back to a
    # sensible canvas-relative inset if the brand omits it.
    try:
        padding_x = ctx.tokens.slide("padding-x")
    except Exception:
        padding_x = _DEFAULT_PADDING_X
    if not padding_x:
        padding_x = _DEFAULT_PADDING_X
    maxw = float(node.kw_args.get("maxwidth", ctx.canvas_w - x - padding_x))
    # Default height: ~1.5× font size (in design-px) to give room for one line.
    h = float(node.kw_args.get("maxheight", style.size_px * 1.5))

    label_text = node.label or ""
    if label_text:
        label_text = normalize_text(label_text, locale=ctx.tokens.locale)
    lang = node.kw_args.get("lang")
    if lang:
        label_text = textfit.hyphenate(label_text, lang=lang)

    autoshrink = str(node.kw_args.get("autoshrink", "")).lower() == "true"
    if autoshrink and label_text:
        from dataclasses import replace as _replace
        # Use the longest single paragraph as the worst-case for width fit; the
        # height check below works on the joined text.
        face, bold = _resolve_face(style.font_family[0], style.weight)
        max_pt = _px_to_pt(style.size_px)
        fitted_pt = textfit.autoshrink_size(
            label_text,
            font=face,
            max_size_pt=max_pt,
            min_size_pt=10,
            bold=bold,
            width_emu=int(maxw * _EMU_PER_PX),
            height_emu=int(h * _EMU_PER_PX),
            line_height=style.line_height,
        )
        if fitted_pt < max_pt:
            # Convert pt back to design-px (2 design-px per pt).
            style = _replace(style, size_px=fitted_pt * 2.0)

    # Orphan control: per paragraph, if the greedy wrap would orphan one
    # word on the final line, replace its preceding space with NBSP so
    # the pair wraps together. Use the final (post-autoshrink) size.
    if label_text:
        face_for_fit, bold_for_fit = _resolve_face(style.font_family[0], style.weight)
        paragraphs = label_text.split("\n")
        paragraphs = [
            textfit.prevent_orphan(
                p,
                font=face_for_fit,
                size_pt=_px_to_pt(style.size_px),
                bold=bold_for_fit,
                width_emu=int(maxw * _EMU_PER_PX),
            )
            for p in paragraphs
        ]
        label_text = "\n".join(paragraphs)

    # Hanging punctuation: shift the textbox left so the leading glyph
    # hangs into the margin (its body-letter optical edge sits at x).
    first_line = label_text.split("\n", 1)[0] if label_text else ""
    hang_offset_px = _leading_hang_offset_px(first_line, _px_to_pt(style.size_px))
    box = slide.shapes.add_textbox(
        _px(x - hang_offset_px), _px(y), _px(maxw), _px(h)
    )
    # `rotate:N` — rotate the textbox N degrees clockwise around its
    # geometric center. Use -90 for a y-axis label reading bottom-to-top.
    # Bbox semantics: x,y,maxwidth,maxheight describe the *pre-rotation*
    # rect; PPTX rotates around the rect's center on render. To place a
    # vertical label at a chart's left edge, set x to the chart edge minus
    # half the natural width, and y so the rect's vertical center matches
    # the chart's vertical midpoint.
    rotate_str = node.kw_args.get("rotate")
    if rotate_str:
        try:
            box.rotation = float(rotate_str)
        except (TypeError, ValueError):
            pass
    # Tag title text-shapes so downstream verify helpers
    # (extract_titles_from_pptx, extract_slide_title_and_body) can identify
    # them. Feinschliff layouts don't use python-pptx placeholder types, so
    # slide.shapes.title is always None — the name prefix is how we recover
    # the semantic role post-render. Prefix is chosen to NOT collide with the
    # chrome-shape prefixes in lib/verify/chrome.py.
    #
    # The 5 styles tagged here cover every title-role text in the shared
    # layouts catalog:
    #   title, act-title — standard content-slide titles
    #   sub             — used only in agenda.slide.dsl for the slide headline
    #   display-xl      — used only in end.slide.dsl for the closer headline
    #   quote           — used in full-bleed-cover + quote.slide.dsl (both
    #                     are "headline-shaped" usages, not body decoration)
    if style_name in ("title", "act-title", "sub", "display-xl", "quote"):
        box.name = f"feinschliff-title-{style_name}"
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    lines = label_text.split("\n")
    p0 = tf.paragraphs[0]
    p0.alignment = align
    p0.line_spacing = style.line_height
    _style_run(p0.add_run(), lines[0], style, tokens=ctx.tokens)
    for extra in lines[1:]:
        p = tf.add_paragraph()
        p.alignment = align
        p.line_spacing = style.line_height
        # Inter-paragraph gap defaults to a fraction of font-size; zero it so
        # the visual gap matches CSS line-height applied across all lines.
        p.space_before = Pt(0)
        _style_run(p.add_run(), extra, style, tokens=ctx.tokens)


def _is_numeric_run(text: str) -> bool:
    """True if every character in text is a digit, separator, or numeric sign."""
    return bool(text) and bool(_NUMERIC_CONTENT_RE.match(text))


def _tracking_for_size(size_pt: float, curve: dict[int, float]) -> float:
    """Step-function lookup: return curve[max-key ≤ size_pt], or 0.0 if no
    curve key is at or below size_pt. The curve is a brand-level default
    for display-tier tracking; per-style `letter_spacing` overrides it.
    """
    if not curve:
        return 0.0
    sorted_keys = sorted(curve.keys())
    if size_pt < sorted_keys[0]:
        return 0.0
    chosen = sorted_keys[0]
    for k in sorted_keys:
        if k <= size_pt:
            chosen = k
        else:
            break
    return curve[chosen]


def _style_run(run, text: str, style, *, tokens: Tokens | None = None) -> None:
    if style.transform == "upper":
        text = text.upper()
    run.text = text
    f = run.font
    # Tabular-numeral override: when the brand exposes a complete tnum_font
    # face name (e.g. "Inter Tabular") and the run is a pure number, use
    # that face verbatim; bold comes from the style weight so emphasis is
    # preserved. Otherwise resolve face from family + weight as usual.
    if tokens is not None and tokens.tnum_font and _is_numeric_run(text):
        face = tokens.tnum_font
        bold = style.weight >= 600
    else:
        face, bold = _resolve_face(style.font_family[0], style.weight)
    f.name = face
    f.size = Pt(_px_to_pt(style.size_px))
    f.bold = bold
    color = style.color_hex
    if style.opacity < 1.0:
        # python-pptx has no native alpha on text runs; approximate by
        # blending toward white. Canonical .pgmeta opacity 0.7 on ink → ~#4A586F.
        color = _blend_to_white(color, 1.0 - style.opacity)
    f.color.rgb = _hex_to_rgb(color)
    # Tracking: per-style letter_spacing wins; if the style declares none,
    # fall back to the brand-level display_tracking_curve (step function).
    size_pt = _px_to_pt(style.size_px)
    tracking_em = style.letter_spacing
    if tracking_em == 0.0 and tokens is not None:
        tracking_em = _tracking_for_size(size_pt, tokens.display_tracking_curve)
    if tracking_em != 0.0:
        # OOXML `spc` is 100ths of a point. Negative tightens; positive loosens.
        spc = int(tracking_em * size_pt * 100)
        rPr = run._r.get_or_add_rPr()
        rPr.set("spc", str(spc))


# Map design weight → face-name suffix. Noto Sans ships every weight as a
# separate face with the weight encoded in the family name (e.g. "Noto Sans
# Light"). soffice resolves family-by-name, so we pick the right face here.
# Weight 700 is the conventional "bold" face — use regular family + bold flag.
_WEIGHT_SUFFIX = [
    (200, "Thin"),
    (300, "Light"),
    (400, None),        # Regular
    (500, "Medium"),
    (600, "SemiBold"),
    (700, "__bold__"),  # signal: use regular family + bold flag
    (800, "ExtraBold"),
    (1000, "Black"),
]


def _resolve_face(family: str, weight: int) -> tuple[str, bool]:
    for thresh, suffix in _WEIGHT_SUFFIX:
        if weight <= thresh:
            if suffix == "__bold__":
                return family, True
            return (f"{family} {suffix}" if suffix else family), False
    return family, False


def _blend_to_white(hex_color: str, t: float) -> str:
    """Linearly blend `hex_color` toward white by fraction `t` (0..1)."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = round(r + (255 - r) * t)
    g = round(g + (255 - g) * t)
    b = round(b + (255 - b) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


def _px_to_pt(px: float) -> float:
    """Design-px (1920×1080 baseline) → PowerPoint points.

    A standard 16:9 PPT slide is 13.33×7.5in = 960×540pt. The 1920-wide
    design baseline maps 2 design-px per point (960/1920 = 0.5).
    """
    return px * _PX_TO_PT


def _emit_rect(slide, node: DSLNode, ctx: EmitContext) -> None:
    """rect X,Y WxH fill:role stroke:role stroke-width:N"""
    x, y = parse_xy(node.pos_args[0])
    w, h = parse_wh(node.pos_args[1])
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, _px(x), _px(y), _px(w), _px(h))
    shape.shadow.inherit = False
    _strip_theme_style(shape)

    fill_name = node.kw_args.get("fill")
    if fill_name:
        shape.fill.solid()
        shape.fill.fore_color.rgb = _hex_to_rgb(ctx.tokens.color(fill_name))
    else:
        shape.fill.background()

    stroke_name = node.kw_args.get("stroke")
    if stroke_name:
        shape.line.color.rgb = _hex_to_rgb(ctx.tokens.color(stroke_name))
        sw = float(node.kw_args.get("stroke-width", 1))
        shape.line.width = Pt(sw * _STROKE_PX_TO_PT)
    else:
        shape.line.fill.background()


def _emit_line(slide, node: DSLNode, ctx: EmitContext) -> None:
    """line X,Y X2,Y2 stroke:role stroke-width:N"""
    x1, y1 = parse_xy(node.pos_args[0])
    x2, y2 = parse_xy(node.pos_args[1])
    line = slide.shapes.add_connector(1, _px(x1), _px(y1), _px(x2), _px(y2))
    stroke = node.kw_args.get("stroke", "fog")
    line.line.color.rgb = _hex_to_rgb(ctx.tokens.color(stroke))
    sw = float(node.kw_args.get("stroke-width", 1))
    line.line.width = Pt(sw * _STROKE_PX_TO_PT)
    _strip_theme_style(line)


def _emit_polyline(slide, node: DSLNode, ctx: EmitContext) -> None:
    """polyline X1,Y1 X2,Y2 X3,Y3 ... stroke:role stroke-width:N

    Open multi-segment line via python-pptx's freeform builder. N≥2 points.
    Stroke styled like `line`; no fill (open path).
    """
    pts = [parse_xy(p) for p in node.pos_args]
    if len(pts) < 2:
        raise ValueError(f"polyline: needs ≥2 points, got {len(pts)}")
    x0, y0 = pts[0]
    ff = slide.shapes.build_freeform(_px(x0), _px(y0), scale=1.0)
    ff.add_line_segments(
        [(_px(x), _px(y)) for x, y in pts[1:]],
        close=False,
    )
    poly = ff.convert_to_shape()
    poly.fill.background()
    stroke = node.kw_args.get("stroke", "ink")
    poly.line.color.rgb = _hex_to_rgb(ctx.tokens.color(stroke))
    sw = float(node.kw_args.get("stroke-width", 2))
    poly.line.width = Pt(sw * _STROKE_PX_TO_PT)
    _strip_theme_style(poly)


def _apply_picture_treatment(pil_image: Image.Image, treatment: str) -> Image.Image:
    """Apply tokens.picture_treatment to a PIL image. Pure function — returns
    a new image. Supported treatments:
      - "none"          — no change
      - "desat(<frac>)" — blend toward grayscale by `frac` (0..1)
      - "duotone"       — reserved for future implementation; raises
    """
    if not treatment or treatment == "none":
        return pil_image
    if treatment.startswith("desat(") and treatment.endswith(")"):
        try:
            frac = float(treatment[len("desat("):-1])
        except ValueError:
            return pil_image
        has_alpha = pil_image.mode in ("RGBA", "LA") or "transparency" in pil_image.info
        rgb = pil_image.convert("RGB")
        gray = rgb.convert("L").convert("RGB")
        blended = Image.blend(rgb, gray, frac)
        if has_alpha:
            alpha = pil_image.convert("RGBA").split()[3]
            r, g, b = blended.split()
            return Image.merge("RGBA", (r, g, b, alpha))
        return blended
    if treatment == "duotone":
        raise NotImplementedError(
            "duotone treatment is reserved for future implementation; "
            "use desat(...) or pre-process the asset"
        )
    return pil_image


def _emit_picture(slide, node: DSLNode, ctx: EmitContext) -> None:
    """picture X,Y WxH path:PATH cover:true

    `path` is the resolved image location — either a literal in the layout
    or interpolated from a `{{ slot }}` placeholder by the expander. If
    `path` is missing, the node is skipped silently. If `path` resolves
    to a non-existent file, a placeholder rect is emitted so the absence
    is visible at review time. `cover:true` center-crops the source image
    to the box aspect ratio (default behaviour is contain).

    Diagram-emitted picture nodes (produced by ``expand_diagram_blocks``)
    store geometry in ``kw_args`` (x, y, w, h as ints) and carry a
    ``_diagram_meta`` sentinel.  Slide-authored nodes use ``pos_args``.
    """
    # Diagram-emitted picture: geometry in kw_args, src in kw_args["src"],
    # sentinel in kw_args["_diagram_meta"].  (Slide-authored picture uses
    # pos_args for position and size.)
    if "_diagram_meta" in node.kw_args:
        x = int(node.kw_args["x"])
        y = int(node.kw_args["y"])
        w = int(node.kw_args["w"])
        h = int(node.kw_args["h"])
        path = node.kw_args.get("src")
        _pos_xy = f"{x},{y}"
        _pos_wh = f"{w}x{h}"
    else:
        x, y = parse_xy(node.pos_args[0])
        w, h = parse_wh(node.pos_args[1])
        path = node.kw_args.get("path")
        _pos_xy = node.pos_args[0]
        _pos_wh = node.pos_args[1]

    optional = str(node.kw_args.get("optional", "false")).lower() == "true"
    if not path:
        # No image bound — emit a placeholder rect so the slot's location is
        # visible in dev renders. Required pictures append to ctx.missing_assets
        # so callers (build / deck build) can decide whether to abort. Mark
        # the picture optional via `optional:true` if a missing slot is OK.
        if not optional:
            ctx.missing_assets.append({
                "kind": "unset",
                "path": None,
                "line_no": node.line_no,
                "source": node.source,
            })
        _emit_rect(slide, DSLNode(
            kind="rect", pos_args=[_pos_xy, _pos_wh],
            kw_args={"fill": "paper-2", "stroke": "fog"},
            label=None, line_no=node.line_no, source=node.source,
        ), ctx)
        return
    p = Path(path)
    if not p.is_absolute() and ctx.asset_root:
        primary = ctx.asset_root / p
        if primary.is_file():
            p = primary
        elif ctx.asset_root_fallback:
            fallback = ctx.asset_root_fallback / p
            p = fallback if fallback.is_file() else primary
        else:
            p = primary
    if not p.is_file():
        if not optional:
            ctx.missing_assets.append({
                "kind": "missing-file",
                "path": str(p),
                "line_no": node.line_no,
                "source": node.source,
            })
        _emit_rect(slide, DSLNode(
            kind="rect", pos_args=[_pos_xy, _pos_wh],
            kw_args={"fill": "paper-2", "stroke": "fog"},
            label=None, line_no=node.line_no, source=node.source,
        ), ctx)
        return

    cover = node.kw_args.get("cover", "false").lower() == "true"
    treatment = ctx.tokens.picture_treatment
    if cover or treatment != "none":
        bytes_io = _prepare_picture_bytes(p, target_aspect=(w / h) if cover else None,
                                          treatment=treatment)
        slide.shapes.add_picture(bytes_io, _px(x), _px(y), width=_px(w), height=_px(h))
    else:
        # Fast path: no crop, no treatment — let python-pptx read the file.
        slide.shapes.add_picture(str(p), _px(x), _px(y), width=_px(w), height=_px(h))


def _prepare_picture_bytes(
    image_path: Path, *, target_aspect: float | None, treatment: str,
) -> io.BytesIO:
    """Load → optional center-crop → optional treatment → JPEG/PNG bytes."""
    with Image.open(image_path) as im:
        im.load()
        if target_aspect is not None:
            sw, sh = im.size
            src_aspect = sw / sh
            if abs(src_aspect - target_aspect) >= 1e-3:
                if src_aspect > target_aspect:
                    new_w = max(1, int(round(sh * target_aspect)))
                    offset = (sw - new_w) // 2
                    im = im.crop((offset, 0, offset + new_w, sh))
                else:
                    new_h = max(1, int(round(sw / target_aspect)))
                    offset = (sh - new_h) // 2
                    im = im.crop((0, offset, sw, offset + new_h))
        if treatment and treatment != "none":
            im = _apply_picture_treatment(im, treatment)
        out = io.BytesIO()
        fmt = (im.format or "PNG").upper()
        if fmt in ("JPG", "JPEG") and im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        # Treated images may have lost the source-format hint; pick by mode.
        if fmt in ("JPG", "JPEG"):
            im.save(out, format="JPEG", quality=92, optimize=True)
        else:
            im.save(out, format="PNG", optimize=True)
        return io.BytesIO(out.getvalue())


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

_SHAPE_KIND = {
    "rect":          MSO_SHAPE.RECTANGLE,
    "rectangle":     MSO_SHAPE.RECTANGLE,
    "oval":          MSO_SHAPE.OVAL,
    "ellipse":       MSO_SHAPE.OVAL,
    "circle":        MSO_SHAPE.OVAL,
    "triangle":      MSO_SHAPE.ISOSCELES_TRIANGLE,
    "triangle-down": MSO_SHAPE.ISOSCELES_TRIANGLE,   # rotated 180 at emit
    "triangle-left": MSO_SHAPE.RIGHT_TRIANGLE,
    "triangle-right":MSO_SHAPE.RIGHT_TRIANGLE,
    "right-triangle":MSO_SHAPE.RIGHT_TRIANGLE,
    "chevron":       MSO_SHAPE.CHEVRON,
    "right-arrow":   MSO_SHAPE.RIGHT_ARROW,
    "left-arrow":    MSO_SHAPE.LEFT_ARROW,
    "diamond":       MSO_SHAPE.DIAMOND,
    "trapezoid":     MSO_SHAPE.TRAPEZOID,
    "pie":           MSO_SHAPE.PIE,          # 270° wedge; rotate to position the missing 90°
    "pie-wedge":     MSO_SHAPE.PIE_WEDGE,    # 90° wedge
    "arc":           MSO_SHAPE.ARC,
    "block-arc":     MSO_SHAPE.BLOCK_ARC,
}


def _emit_shape(slide, node: DSLNode, ctx: EmitContext) -> None:
    """shape X,Y WxH kind:NAME fill:role stroke:role stroke-width:N rotate:DEG

    Generic shape emitter — wraps python-pptx MSO_SHAPE so layouts can
    place ovals, triangles, chevrons, etc. Fill / stroke behaviour matches
    `rect`. `rotate` is in degrees clockwise.
    """
    x, y = parse_xy(node.pos_args[0])
    w, h = parse_wh(node.pos_args[1])
    kind = node.kw_args.get("kind", "rect")
    mso_kind = _SHAPE_KIND.get(kind)
    if mso_kind is None:
        raise ValueError(f"shape: unknown kind '{kind}' (known: {sorted(_SHAPE_KIND)})")
    shape = slide.shapes.add_shape(mso_kind, _px(x), _px(y), _px(w), _px(h))
    shape.shadow.inherit = False
    _strip_theme_style(shape)
    rot = node.kw_args.get("rotate")
    if rot is None and kind == "triangle-down":
        rot = "180"
    if rot is None and kind == "triangle-left":
        rot = "270"
    if rot is None and kind == "triangle-right":
        rot = "90"
    if rot is not None:
        shape.rotation = float(rot)

    # Preset-shape adjustment handle (e.g. parallelogram top-edge skew).
    # Maps to <a:gd name="adj" fmla="val …"/>. Range 0..1; python-pptx stores
    # as fraction. Silently no-op for shapes without an adj handle.
    adj1 = node.kw_args.get("adj1")
    if adj1 is not None:
        try:
            shape.adjustments[0] = float(adj1)
        except (IndexError, ValueError):
            pass

    fill_name = node.kw_args.get("fill")
    if fill_name:
        shape.fill.solid()
        shape.fill.fore_color.rgb = _hex_to_rgb(ctx.tokens.color(fill_name))
        opacity = node.kw_args.get("fill-opacity")
        if opacity is not None:
            _set_fill_alpha(shape, float(opacity))
    else:
        shape.fill.background()

    stroke_name = node.kw_args.get("stroke")
    if stroke_name:
        shape.line.color.rgb = _hex_to_rgb(ctx.tokens.color(stroke_name))
        sw = float(node.kw_args.get("stroke-width", 1))
        shape.line.width = Pt(sw * _STROKE_PX_TO_PT)
    else:
        shape.line.fill.background()


# ---------------------------------------------------------------------------
# Chrome sanitation — post-build XML pass (Layer 1 task 10)
# ---------------------------------------------------------------------------

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

# Custom attribute the emitter writes on a <p:sp> when its source DSL used
# `effect:allow` to opt out of sanitation.
_EFFECT_ALLOW_ATTR = "effect-allow"

# Outline clamp: hairline at 0.5pt = 6350 EMU; anything above 1pt (12700 EMU)
# is clamped down to hairline.
_OUTLINE_CLAMP_THRESHOLD_EMU = 12700
_OUTLINE_CLAMP_TARGET_EMU = 6350


def sanitize_chrome(slide_xml) -> None:
    """Walk a slide's <p:spTree> and remove PowerPoint defaults that read
    as "AI-templated": drop-shadow / glow / soft-edge effects, gradient
    fills (replaced with solid), and outlines wider than 1pt.

    Scoped to <p:spTree> so master/layout inheritance is preserved.
    Mutates `slide_xml` in place. Idempotent.
    """
    from lxml import etree

    sptree = slide_xml.find(f".//{{{_NS_P}}}spTree")
    if sptree is None:
        return

    # 1. effectLst — strip unless parent <p:sp> opts in.
    for effect_lst in list(sptree.iter(f"{{{_NS_A}}}effectLst")):
        parent = effect_lst.getparent()
        while parent is not None and not parent.tag.endswith("}sp"):
            parent = parent.getparent()
        if parent is not None and parent.get(_EFFECT_ALLOW_ATTR) == "1":
            continue
        effect_lst.getparent().remove(effect_lst)

    # 2. gradFill → solidFill (with the first stop's color).
    ns = {"a": _NS_A}
    for grad in list(sptree.iter(f"{{{_NS_A}}}gradFill")):
        grad_parent = grad.getparent()
        first_clr = grad.find(".//a:gs[1]/a:srgbClr", ns)
        idx = list(grad_parent).index(grad)
        grad_parent.remove(grad)
        if first_clr is None:
            continue
        color_val = first_clr.get("val") or "808080"
        solid = etree.SubElement(grad_parent, f"{{{_NS_A}}}solidFill")
        clr = etree.SubElement(solid, f"{{{_NS_A}}}srgbClr")
        clr.set("val", color_val)
        grad_parent.remove(solid)
        grad_parent.insert(idx, solid)

    # 3. Clamp outline widths > 1pt down to a 0.5pt hairline.
    for ln in sptree.iter(f"{{{_NS_A}}}ln"):
        w_str = ln.get("w")
        if w_str is None:
            continue
        try:
            w = int(w_str)
        except ValueError:
            continue
        if w > _OUTLINE_CLAMP_THRESHOLD_EMU:
            ln.set("w", str(_OUTLINE_CLAMP_TARGET_EMU))


def _set_fill_alpha(shape, opacity: float) -> None:
    """Set alpha on a solid fill via OOXML. opacity 0..1."""
    from lxml import etree
    nsmap = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    spPr = shape.fill._xPr
    solidFill = spPr.find("a:solidFill", nsmap)
    if solidFill is None:
        return
    srgbClr = solidFill.find("a:srgbClr", nsmap)
    if srgbClr is None:
        return
    alpha = etree.SubElement(srgbClr, "{%s}alpha" % nsmap["a"])
    alpha.set("val", str(int(opacity * 100000)))


def _strip_theme_style(shape) -> None:
    """Drop the `<p:style>` block from a newly-added shape.

    python-pptx's `add_shape` writes a default `<p:style>` element that
    references the theme's effect/fill/line slots (e.g. `<a:effectRef
    idx="2">` points at the second `<a:outerShdw>` entry in
    `theme1.xml`). LibreOffice and PowerPoint both honour that effect
    reference at render time *even though* `shape.shadow.inherit = False`
    writes an explicit `<a:effectLst/>` on the shape's `<p:spPr>`.

    Result before the strip: a subtle drop-shadow under every primitive
    in rendered PNGs. Flat-shape brand packs (the default, feinschliff,
    …) want the source to match the render; removing the `<p:style>`
    block does that.
    """
    nsmap = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
    el = shape._element.find("p:style", nsmap)
    if el is not None:
        shape._element.remove(el)


_EMITTERS = {
    "text":     _emit_text,
    "rect":     _emit_rect,
    "line":     _emit_line,
    "polyline": _emit_polyline,
    "picture":  _emit_picture,
    "shape":    _emit_shape,
}


def _slide_canvas(nodes: list[DSLNode]) -> tuple[float, float]:
    """Read the `canvas WxH` directive if present; otherwise default 1920×1080."""
    for n in nodes:
        if n.kind == "canvas" and n.pos_args:
            return parse_wh(n.pos_args[0])
    return 1920.0, 1080.0


def _append_slide(prs: Presentation, nodes: list[DSLNode], tokens: Tokens, *,
                  asset_root: Path | None,
                  asset_root_fallback: Path | None = None,
                  missing_assets: list[dict] | None = None) -> None:
    """Append one slide built from `nodes` to `prs`, using the tokens for fills."""
    cw, ch = _slide_canvas(nodes)
    slide = prs.slides.add_slide(prs.slide_layouts[6])    # blank
    try:
        bg = slide.background.fill
        bg.solid()
        bg.fore_color.rgb = _hex_to_rgb(tokens.color("paper"))
    except KeyError:
        pass

    ctx = EmitContext(tokens=tokens, canvas_w=cw, canvas_h=ch,
                      asset_root=asset_root, asset_root_fallback=asset_root_fallback)
    for n in nodes:
        cond = n.kw_args.get("if")
        if cond is not None:
            s = cond.strip()
            if not s or s.lower() == "false" or _RESIDUAL_PLACEHOLDER.search(s):
                continue
        if n.kind in ("canvas", "theme"):
            continue
        emit = _EMITTERS.get(n.kind)
        if emit is None:
            import sys
            print(f"WARN: no emitter for primitive '{n.kind}' "
                  f"(line {n.line_no}) — skipping", file=sys.stderr)
            continue
        emit(slide, n, ctx)
    if missing_assets is not None and ctx.missing_assets:
        missing_assets.extend(ctx.missing_assets)


def build_presentation(nodes: list[DSLNode], tokens: Tokens, *,
                       asset_root: Path | None = None,
                       asset_root_fallback: Path | None = None) -> Presentation:
    """Walk primitive nodes, build a Presentation with one filled slide.

    The returned Presentation carries `missing_assets: list[dict]` as an
    attribute — empty when every required picture resolved, populated
    otherwise. Callers can branch on `prs.missing_assets` to abort.

    `asset_root_fallback` is the plugin-level shared assets dir; it is
    walked when the per-brand `asset_root` does not contain the requested
    relative path. Brand-specific files always win over plugin defaults.
    """
    cw, ch = _slide_canvas(nodes)
    prs = Presentation()
    prs.slide_width  = _px(cw)
    prs.slide_height = _px(ch)
    missing: list[dict] = []
    _append_slide(prs, nodes, tokens, asset_root=asset_root,
                  asset_root_fallback=asset_root_fallback,
                  missing_assets=missing)
    for slide in prs.slides:
        sanitize_chrome(slide._element)
    prs.missing_assets = missing
    return prs


def build_multi_slide(
    slides: list[tuple[list[DSLNode], Tokens, Path | None]],
    *,
    asset_root_fallback: Path | None = None,
) -> Presentation:
    """Build a Presentation with N slides. Each slide entry is
    `(nodes, tokens, asset_root)`. The slide deck's canvas comes from
    the first slide's `canvas` directive; remaining slides reuse it.

    `asset_root_fallback` applies to every slide; see
    :func:`build_presentation` for semantics.
    """
    if not slides:
        raise ValueError("build_multi_slide: no slides provided")
    first_nodes, first_tokens, first_asset_root = slides[0]
    cw, ch = _slide_canvas(first_nodes)
    prs = Presentation()
    prs.slide_width  = _px(cw)
    prs.slide_height = _px(ch)
    missing: list[dict] = []
    for slide_idx, (nodes, tokens, asset_root) in enumerate(slides, start=1):
        per_slide: list[dict] = []
        _append_slide(prs, nodes, tokens, asset_root=asset_root,
                      asset_root_fallback=asset_root_fallback,
                      missing_assets=per_slide)
        for entry in per_slide:
            entry.setdefault("slide_index", slide_idx)
            missing.append(entry)
    for slide in prs.slides:
        sanitize_chrome(slide._element)
    prs.missing_assets = missing
    return prs
