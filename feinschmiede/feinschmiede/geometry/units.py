"""Single source of truth for design-px <-> pt <-> EMU conversions.

DSL geometry lives in *design pixels* on a declared canvas (1920x1080
baseline). The physical slide size comes from tokens.json `slide.width_emu`
(decompiled brand packs write the source PPTX value); when absent, the
legacy 13.33in / 1920px baseline applies. There is NO fixed px->pt constant:
a 12in slide renders a 16pt font from ~35.6 design-px, a 13.33in slide from
32 design-px. Every consumer (pptx_emit, slot_budget, layout_profile_gen,
textfit) must derive its scale from here — a drift test greps for locally
re-defined constants.
"""
from __future__ import annotations

EMU_PER_PT: float = 12700.0                     # PowerPoint: 914400 EMU/in / 72 pt/in
LEGACY_SLIDE_WIDTH_EMU: float = 12_192_000.0    # 13.333in standard 16:9 slide
LEGACY_CANVAS_W: float = 1920.0
EMU_PER_PX_BASELINE: float = LEGACY_SLIDE_WIDTH_EMU / LEGACY_CANVAS_W   # 6350.0
PX_TO_PT_BASELINE: float = EMU_PER_PX_BASELINE / EMU_PER_PT             # 0.5


def emu_per_px(width_emu: float | None = None, canvas_w: float | None = None) -> float:
    """Design-px -> EMU scale. Falsy width_emu or canvas_w -> legacy baseline."""
    if not width_emu or not canvas_w:
        return EMU_PER_PX_BASELINE
    return float(width_emu) / float(canvas_w)


def px_to_pt(width_emu: float | None = None, canvas_w: float | None = None) -> float:
    """Design-px -> pt scale (= emu_per_px / EMU_PER_PT)."""
    return emu_per_px(width_emu, canvas_w) / EMU_PER_PT


def font_px_to_pt(px: float, *, scale: float = PX_TO_PT_BASELINE) -> float:
    """Font size design-px -> pt at the given px->pt scale."""
    return px * scale


def font_pt_to_px(pt: float, *, scale: float = PX_TO_PT_BASELINE) -> float:
    """Font size pt -> design-px at the given px->pt scale."""
    return pt / scale
