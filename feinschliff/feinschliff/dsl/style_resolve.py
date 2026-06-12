"""Shared per-node text-style resolution.

One place that applies the DSL node-level overrides (`color:`, `weight:`,
`size:`, `indent:`, `italic:`) on top of the node's style bundle. Both the
PPTX emitter (`pptx_emit._emit_text`) and the slot-budget gate
(`slot_budget.compute_slot_budgets`) consume this — the gate previously
resolved only the bundle, so decompiled packs (which override `size:` on
nearly every node) were modeled at the wrong size and overflow shipped
silently.
"""
from __future__ import annotations

from dataclasses import replace as _replace
from typing import TYPE_CHECKING

from feinschmiede.geometry import units

if TYPE_CHECKING:
    from feinschliff.dsl.parser import DSLNode
    from feinschmiede.dsl.tokens import ResolvedStyle, Tokens

HIERARCHY_COLOR_WALK = ("ink", "graphite", "fog")


def step_hierarchy(
    size_px: float, weight: int, color_role: str, *, level: int,
    px_to_pt: float = units.PX_TO_PT_BASELINE,
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
        if new_color in HIERARCHY_COLOR_WALK:
            idx = HIERARCHY_COLOR_WALK.index(new_color)
            new_color = HIERARCHY_COLOR_WALK[min(idx + 1, len(HIERARCHY_COLOR_WALK) - 1)]
    # Round size_pt to nearest 0.5pt. size_px ↔ pt: 2 design-px per pt.
    pt = new_size * px_to_pt
    pt = round(pt * 2) / 2
    new_size = pt / px_to_pt
    return new_size, new_weight, new_color


def resolve_node_style(
    node: "DSLNode", tokens: "Tokens", *,
    px_to_pt: float = units.PX_TO_PT_BASELINE,
) -> "ResolvedStyle":
    """Effective style for a `text` node: bundle + node-level overrides.

    `px_to_pt` is the build's design-px→pt scale (derived from tokens
    `slide.width_emu`); the emitter passes its configured module global, the
    budget gate passes its per-budget derivation — both come from
    `feinschmiede.geometry.units`, so they cannot drift.

    Raises KeyError/ValueError where the inline emitter code did
    (unknown style bundle, unknown color/weight/size token); an unknown color role
    during indent stepping falls back silently to the pre-step color.
    """
    style_name = node.kw_args.get("style", "body")
    style = tokens.resolve_style(style_name)
    color_override = node.kw_args.get("color")
    if color_override:
        style = _replace(style, color_hex=tokens.color(color_override),
                         color_role=color_override)
    # `weight:<token>` overrides the style's default font weight without
    # forcing the author to switch style bundles. Lets a single layout pair
    # display-size with bold (or huge with regular), which the predefined
    # bundles don't express (huge/display are light-only, title-l is
    # bold-only). Token must exist in tokens.json.font-weight.
    weight_override = node.kw_args.get("weight")
    if weight_override:
        style = _replace(style, weight=tokens.font_weight(weight_override))
    # `size:<N>px` or `size:<N>pt` or `size:<token-name>` lets a single text
    # primitive escape its style bundle's fixed size. Critical for matching
    # source decks whose pt sizes fall between the bundle steps (16/26/44/80
    # /120/160 px) — without it, the decompiler has to round to the nearest
    # bundle and a 42pt source title renders at the 44px sub bundle ≈ 33pt,
    # noticeably small. Numeric forms accepted: "32pt", "56px", or bare int
    # treated as px.
    size_override = node.kw_args.get("size")
    if size_override:
        raw = size_override.strip().lower()
        if raw.endswith("pt"):
            # `pt` → design-px uses the SAME conversion the emitter rounds-
            # trip with (Pt(_px_to_pt(size_px)) downstream). Using the CSS
            # convention (pt × 4/3) here bakes a 96-DPI assumption and
            # halves the rendered font when the slide is sized for a
            # different DPI — e.g. 42pt → 56px → 21pt on a 10" slide.
            size_px = float(raw[:-2]) / px_to_pt
        elif raw.endswith("px"):
            size_px = float(raw[:-2])
        else:
            try:
                size_px = float(raw)
            except ValueError:
                size_px = tokens.font_size_px(raw)
        style = _replace(style, size_px=size_px)
    # Hierarchy stepping: indent:N steps size/weight/color N times.
    try:
        indent_level = int(node.kw_args.get("indent", "0"))
    except (TypeError, ValueError):
        indent_level = 0
    if indent_level > 0:
        new_size, new_weight, new_color_role = step_hierarchy(
            style.size_px, style.weight, style.color_role,
            level=indent_level, px_to_pt=px_to_pt,
        )
        try:
            new_color_hex = tokens.color(new_color_role)
        except KeyError:
            new_color_hex = style.color_hex
        style = _replace(
            style,
            size_px=new_size, weight=new_weight,
            color_hex=new_color_hex, color_role=new_color_role,
        )
    if str(node.kw_args.get("italic", "")).lower() == "true":
        style = _replace(style, italic=True)
    return style
