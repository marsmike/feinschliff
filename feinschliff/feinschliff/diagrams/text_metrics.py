"""Shared text-metric constants for diagram renderers + validators.

Single source of truth so the overflow validator, the rasterizer, and
the wireframe agree on text widths and font sizes.
"""

# Average glyph advance (em units) for the validator's overflow prediction
# and the rasterizer's bbox estimation of free-floating text. The
# validator must err slightly conservative (over-estimate width) so
# overflow is flagged before it gets shipped; the rasterizer's viewBox
# benefits from the same conservative number so text never clips. Both
# paths previously used different values (0.62 vs 0.55) and silently
# disagreed by 13%.
CHAR_WIDTH_EM = 0.62

# SVG-DSL `text` level → font-size in pixels at scale=1. Shared by
# svg_expand emitters and the diagram_wireframe predictor so the
# wireframe overflow forecast matches what the rasterizer will draw.
SVG_TEXT_SIZES = {
    "title": 22,
    "subtitle": 16,
    "body": 14,
    "detail": 12,
    "value": 13,
}

# Excalidraw-DSL `text` level → font-size in pixels at scale=1. The
# Excalidraw canvas has its own visual baseline (sketchy / VirgilSC
# font) and uses a separate (larger) scale than SVG.
EXCALIDRAW_TEXT_SIZES = {
    "title": 28,
    "subtitle": 20,
    "eyebrow": 12,
    "body": 14,
    "detail": 12,
    "mono": 13,
}
