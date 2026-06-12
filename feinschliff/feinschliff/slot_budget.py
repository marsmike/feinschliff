"""Typographic budget extractor.

Derives per-slot character/line constraints directly from DSL layout nodes
and the active brand's token set. This is the single source of truth that
replaces hand-written `≤180` schema comments with pixel-accurate limits.

Usage::

    from feinschliff.slot_budget import compute_slot_budgets, format_budget_hint
    from feinschliff.dsl.parser import parse_file
    from feinschmiede.dsl.tokens import load_tokens

    nodes, _ = parse_file(layout_path)
    tokens = load_tokens(brand_dir)
    budgets = compute_slot_budgets(nodes, tokens)
    # budgets["action_title"] → SlotBudget(chars_per_line=51, max_lines=2, ...)
    print(format_budget_hint(budgets))

The computed budgets are fed to two consumers:

1. ``content_validator.py`` — ``check_slot_overflow`` uses ``textfit.fits()``
   to catch overflows before the render budget is burned.

2. ``/deck`` generation (Step 2) — ``format_budget_hint()`` produces a table
   that the LLM includes in its slot-filling context so generated text stays
   within the actual pixel envelope, not the looser schema char-count.
"""
from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from collections.abc import Sequence

from feinschliff.dsl.parser import DSLNode, CompoundDef
from feinschliff.dsl.style_resolve import resolve_node_style
from feinschmiede.dsl.tokens import Tokens
from feinschmiede.geometry import units
from feinschliff.textfit import (
    chars_per_line as _cpl,
    has_real_metrics as _has_real_metrics,
    register_font_metrics as _register_font_metrics,
    supported_fonts as _supported_fonts,
)


def register_tokens_font_metrics(tokens) -> None:
    """Register tokens' `font-metrics` width ratios with the textfit table.

    Block shape: ``{"<Family>": {"normal": 0.48, "bold": 0.53}, ...}``;
    ``$``-prefixed keys (descriptions etc.) are skipped. Malformed entries
    are ignored — metrics are a measurement aid, never a build-breaker.
    """
    raw = getattr(tokens, "raw", None)
    block = raw.get("font-metrics") if isinstance(raw, dict) else None
    if not isinstance(block, dict):
        return
    for family, m in block.items():
        if family.startswith("$") or not isinstance(m, dict):
            continue
        try:
            _register_font_metrics(
                family, normal=float(m["normal"]), bold=float(m["bold"])
            )
        except (KeyError, TypeError, ValueError):
            continue


# Design-px → EMU and pt legacy defaults; values come from the shared units
# module so there is no per-file drift.  compute_slot_budgets derives per-budget
# scale from tokens slide.width_emu instead — see SlotBudget.emu_per_px / px_to_pt fields.
_EMU_PER_PX: float = units.EMU_PER_PX_BASELINE
_PX_TO_PT: float = units.PX_TO_PT_BASELINE

# Slot interpolation — matches {{ slot_name }}, {{ cells[0].heading }}, etc.
_SLOT_RE = re.compile(r"\{\{([^{}]+)\}\}")
# Normalise array indices: cells[0].heading → cells[].heading
_IDX_RE = re.compile(r"\[\d+\]")


@dataclass(frozen=True)
class SlotBudget:
    """Typographic budget for one text slot in a layout.

    All pixel values are in *design pixels* (1920×1080 canvas baseline).
    EMU-converted equivalents for ``textfit`` are exposed as properties.
    """
    slot: str               # normalised slot key, e.g. "action_title" or "cells[].heading"
    style: str              # DSL style name, e.g. "act-title"
    size_px: float          # font size in design-px
    line_height: float      # CSS line-height multiplier
    width_px: float         # maxwidth in design-px
    height_px: float        # maxheight in design-px (0 = unconstrained)
    font_family: str        # primary font family name
    bold: bool              # whether the style uses bold weight
    emu_per_px: float = units.EMU_PER_PX_BASELINE  # design-px → EMU scale (derived from tokens slide.width_emu)
    px_to_pt: float = units.PX_TO_PT_BASELINE       # design-px → pt scale (emu_per_px / EMU_PER_PT)

    # ── derived geometry ──────────────────────────────────────────────────
    @property
    def font_size_pt(self) -> float:
        """Rendered font size in pt — size_px at the build's px→pt scale,
        identical to what pptx_emit's Pt() conversion produces."""
        return self.size_px * self.px_to_pt

    @property
    def size_pt(self) -> float:
        """Deprecated alias for :attr:`font_size_pt` (one release)."""
        return self.font_size_pt

    @property
    def width_emu(self) -> int:
        return int(self.width_px * self.emu_per_px)

    @property
    def height_emu(self) -> int:
        return int(self.height_px * self.emu_per_px)

    @property
    def chars_per_line(self) -> int:
        """Estimated characters that fit on one wrapped line."""
        return _cpl(self.font_family, self.font_size_pt, self.bold, self.width_emu)

    @property
    def max_lines(self) -> int:
        """Maximum full lines that fit in height_px at this line-height.

        Returns a large sentinel (999) when height_px is 0 or very large,
        meaning the slot is effectively unconstrained vertically.
        """
        if self.height_px <= 0:
            return 999
        line_h_px = self.size_px * self.line_height
        if line_h_px <= 0:
            return 999
        return max(1, math.floor(self.height_px / line_h_px))

    @property
    def max_chars(self) -> int:
        """Rough total character capacity (chars_per_line × max_lines)."""
        if self.max_lines >= 999:
            return 9999
        return self.chars_per_line * self.max_lines


def _extract_single_slot(label: str) -> str | None:
    """Return the normalised slot name if *label* contains exactly one slot
    interpolation, otherwise None (multi-slot or no-slot labels are skipped).
    """
    matches = _SLOT_RE.findall(label)
    if len(matches) != 1:
        return None
    raw = matches[0].strip()
    # Drop Jinja filters (e.g. `{{ text_5 | default("…") }}`) so the key is the
    # bare slot reference. Brand layouts write every slot with a `| default(…)`
    # fallback; keying on the whole expression made budgets unmatchable by the
    # content-lint and verify-static lookups (which key on the normalised slot
    # name via `iter_slot_values`) — silently disabling the overflow check for
    # those slots.
    raw = raw.split("|", 1)[0].strip()
    return _IDX_RE.sub("[]", raw)


def _bold_for_weight(weight: int) -> bool:
    return weight >= 600


def _best_font(font_family: list[str]) -> str:
    """Return the first font in *font_family* known to textfit, or 'default'.

    Walks the full list so that fallback fonts (e.g. ``['BrandFont', 'Open
    Sans']``) can resolve to 'Open Sans' when BrandFont has no empirical
    width ratio. Logs a warning to stderr when no explicit match is found.
    """
    known = _supported_fonts()
    for name in font_family:
        if name in known:
            return name
    if font_family:
        print(
            f"slot_budget: font {font_family[0]!r} not in width-ratio table; "
            "falling back to default ratios",
            file=sys.stderr,
        )
    return "default"


def _budget_face(font_family: list[str], weight: int) -> tuple[str, bool]:
    """The (face, bold) textfit should model for this budget — the same face
    the emitter's fit paths use, whenever textfit can actually model it.

    Priority:
    1. The emitter's face (family[0] + weight suffix via pptx_emit._resolve_face)
       when it is registered/ratio-table-known or has real measured metrics —
       keeps gate predictions on the same glyph widths the emitter fits with.
    2. Otherwise today's fallback walk (_best_font + _bold_for_weight) so
       fallback-list brands and metric-less environments are unchanged.
    """
    if font_family:
        # Lazy import: pptx_emit pulls python-pptx/PIL — only needed here.
        from feinschliff.dsl.pptx_emit import _resolve_face
        face, bold = _resolve_face(font_family[0], weight)
        if face in _supported_fonts() or _has_real_metrics(face, bold):
            return face, bold
    return (_best_font(font_family) if font_family else "default",
            _bold_for_weight(weight))


def compute_slot_budgets(
    nodes: Sequence[DSLNode],
    tokens: Tokens,
    *,
    # Safety margin: reduce effective width/height by this fraction before
    # computing chars_per_line / max_lines. 0.0 = use raw values (default,
    # conservative callers can pass 0.10 for a 10% buffer).
    margin: float = 0.0,
    # When provided, compound calls inside `nodes` are expanded with the
    # call's positional/keyword args substituted into the compound body
    # before slot extraction. This lets the budget gate see text primitives
    # that live inside compounds like `kpi-cell`. Pass the same compounds
    # dict used at render time (load_compounds_for_brand).
    compounds: dict[str, CompoundDef] | None = None,
) -> dict[str, SlotBudget]:
    """Parse *nodes* and return a per-slot typographic budget dict.

    Only ``text`` nodes whose label contains **exactly one** ``{{ slot }}``
    interpolation are considered. Nodes without ``maxwidth`` are skipped
    (their width is effectively unbounded and no useful budget can be stated).
    When the same normalised slot key appears more than once with different
    geometry (e.g. two text boxes using the same slot at different sizes),
    the **tightest** budget (smallest ``max_chars``) wins — that's the
    box most likely to overflow first.

    The optional *margin* argument shrinks effective width and height by a
    fraction, e.g. ``margin=0.10`` provides a 10% safety buffer above the raw
    pixel constraint.

    The production default is ``margin=0.0`` — the showcase corpus is tuned
    to fit at the raw pixel envelope. A non-zero margin would weaken the
    constraint (false negatives) on already-fitting content; callers who
    want a safety buffer should pass it explicitly.
    """
    # Brand packs ship width ratios for their own (often proprietary) fonts
    # via a tokens `font-metrics` block. Register them here, not only in
    # compile_slide: budgets are also computed from entry points that never
    # compile a slide (the default static gate, deck plan-skeleton), and all
    # of them pass `tokens`.
    register_tokens_font_metrics(tokens)

    candidates: dict[str, list[SlotBudget]] = {}

    if compounds:
        # Pre-expand compound calls so text primitives inside compound
        # bodies become visible to the budget walker. The call args carry
        # their slot references (e.g. value:"{{ kpis[0].value }}") through
        # parameter substitution — the resulting text labels end up with
        # the right `{{ slot }}` shape for `_extract_single_slot`.
        from feinschliff.dsl.expander import expand_compounds  # local import; avoid cycle
        nodes, _ = expand_compounds(list(nodes), compounds)

    # Derive px→EMU/pt scale from the canvas width and tokens slide.width_emu.
    # Decompiled brand packs write width_emu to tokens.json; without it we fall
    # back to the 1920px/13.33in legacy baseline so existing layouts are unchanged.
    canvas_w = 1920.0
    for n in nodes:
        if n.kind == "canvas" and n.pos_args:
            try:
                canvas_w = float(str(n.pos_args[0]).lower().split("x")[0])
            except ValueError:
                pass
            break
    try:
        width_emu_token = tokens.slide("width_emu")
    except Exception:
        width_emu_token = 0
    emu_per_px = units.emu_per_px(width_emu_token, canvas_w)
    px_to_pt = emu_per_px / units.EMU_PER_PT

    for node in nodes:
        if node.kind != "text":
            continue
        label = node.label
        if not label:
            continue
        slot = _extract_single_slot(label)
        if slot is None:
            continue

        style_name = node.kw_args.get("style", "body")
        maxwidth_str = node.kw_args.get("maxwidth")
        if not maxwidth_str:
            continue  # unbounded width — no useful budget
        try:
            width_px = float(maxwidth_str) * (1.0 - margin)
        except ValueError:
            print(
                f"slot_budget: skipping node — cannot parse maxwidth {maxwidth_str!r}",
                file=sys.stderr,
            )
            continue

        maxheight_str = node.kw_args.get("maxheight")
        try:
            height_px = float(maxheight_str) * (1.0 - margin) if maxheight_str else 0.0
        except ValueError:
            print(
                f"slot_budget: cannot parse maxheight {maxheight_str!r}; "
                "treating slot as vertically unconstrained",
                file=sys.stderr,
            )
            height_px = 0.0

        # resolve_node_style raises on unknown style/color/weight/size tokens —
        # such nodes are unbudgetable, skip them (the emitter will fail loudly on the same token).
        try:
            resolved = resolve_node_style(node, tokens, px_to_pt=px_to_pt)
        except (KeyError, ValueError):
            continue

        font_name, bold = _budget_face(resolved.font_family, resolved.weight)
        budget = SlotBudget(
            slot=slot,
            style=style_name,
            size_px=resolved.size_px,
            line_height=resolved.line_height,
            width_px=width_px,
            height_px=height_px,
            font_family=font_name,
            bold=bold,
            emu_per_px=emu_per_px,
            px_to_pt=px_to_pt,
        )
        candidates.setdefault(slot, []).append(budget)

    # Keep tightest budget per slot. Primary key: max_chars (overall capacity);
    # tie-break on chars_per_line so the narrowest box wins when multiple
    # candidates are unconstrained vertically (all have max_chars=9999).
    result: dict[str, SlotBudget] = {}
    for slot, budget_list in candidates.items():
        result[slot] = min(budget_list, key=lambda b: (b.max_chars, b.chars_per_line))
    return result


def format_budget_hint(budgets: dict[str, SlotBudget]) -> str:
    """Return a compact, LLM-readable table of slot constraints.

    Suitable for injection into Step 2 of the /deck generation prompt so the
    model targets the actual pixel envelope rather than generic char counts.

    Example output::

        Slot typographic budgets (derived from layout DSL + tokens):
        action_title  : style=act-title 56px | ~51 chars/line | max 2 lines | max ~102 chars total
        heading       : style=h-hd      32px | ~19 chars/line | max 2 lines | max ~38 chars total
        body          : style=body      26px | ~28 chars/line | max 3 lines | max ~84 chars total

        Rules:
        - Stay within chars/line to avoid unintended wrapping.
        - Avoid hyphenated compounds (week-on-week, production-grade) in narrow slots
          (≤25 chars/line) — renderers break at hyphens, causing extra lines.
        - Prefer short, unhyphenated words when chars/line < 25.
    """
    if not budgets:
        return ""

    lines = ["Slot typographic budgets (derived from layout DSL + tokens):"]
    max_slot_len = max(len(s) for s in budgets)
    for slot, b in sorted(budgets.items()):
        if b.max_lines >= 999:
            lines_str = "unconstrained"
        else:
            lines_str = f"max {b.max_lines} line{'s' if b.max_lines != 1 else ''}"
        if b.max_chars >= 9999:
            chars_str = "unconstrained"
        else:
            chars_str = f"max ~{b.max_chars} chars total"
        lines.append(
            f"  {slot:<{max_slot_len}} : style={b.style} {b.size_px:.0f}px"
            f" | ~{b.chars_per_line} chars/line"
            f" | {lines_str}"
            f" | {chars_str}"
        )

    lines += [
        "",
        "Rules:",
        "  - Stay within chars/line to avoid unintended wrapping.",
        "  - Avoid hyphenated compounds (week-on-week, production-grade) in slots",
        "    with ≤25 chars/line — renderers break at hyphens, producing extra lines.",
        "  - Prefer short, unhyphenated words when chars/line < 25.",
    ]
    return "\n".join(lines)
