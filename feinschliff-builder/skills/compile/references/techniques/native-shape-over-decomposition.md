# Prefer native MSO_SHAPE over multi-primitive decomposition

## Pattern
Composing a parallelogram (or any non-rect closed shape) from 4 stroked
`line` primitives produces visible artifacts:
- Rounded line-caps at each corner (connector default; not user-settable
  through the high-level python-pptx API).
- Sub-pixel gaps or overshoots at corner junctions.
- Theme effect inheritance applies per-line, not per-frame.
- The result is 4 selectable shapes in PowerPoint, not one.

## Trigger
Any compound that decomposes a closed shape into lines/triangles "pending
upstream support" for the real MSO_SHAPE. The comment usually starts with
"two HQ-grade workarounds:".

## Fix shape
- Add the MSO_SHAPE to `_SHAPE_KIND` in `pptx_emit.py` (single line).
- If the shape has an adjustment handle (parallelogram skew, pie angle,
  callout pointer), expose it via an `adj1:` kw_arg on the shape primitive
  that maps to `shape.adjustments[0]`.
- Rewrite the compound to use one `shape kind:<name>` call.

Native shape inherits `_strip_theme_style` automatically, gets sharp
mitered corners, becomes one editable shape.

## Arbitrary custGeom with no MSO preset: carry it verbatim (`native`)
When the source is a freeform `<a:custGeom>` with no MSO_SHAPE equivalent
(decorative blobs, dividers, logo geometry), don't decompose it into
`svg { path }` either — that path **rasterises to a PNG and inserts as
`<p:pic>`**, which distorts non-square shapes (square render canvas → squashed
"dome") and is a picture "cheat".

The decompiler instead emits a **`native <id> b64:"<p:sp>"`** primitive: the
source `<p:sp>` XML, base64-embedded inline in the DSL (self-contained brand
pack), spliced verbatim into the output `spTree` by `_emit_native`. The shape
stays a real, **editable** vector — pixel-exact, no raster, no picture.
- Decompiler bakes `schemeClr → srgbClr` from the SOURCE theme (colours survive
  the output deck's theme) and shifts the xfrm by the group/layout offset to
  slide-absolute. Grouped/scaled shapes keep the `svg` path.
- Evidence: MS "Shapes" cover (4 decorative custGeom) 51.2% → 1.75% struct_diff,
  pixel-exact + editable.

## For `feinschliff:compile`
When scaffolding a brand pack with diagonal frames, rotated shapes, or
asymmetric callouts: check MSO_SHAPE enum FIRST before decomposing. The
toolkit already exposes `parallelogram`, `pie`, `pie-wedge`, `arc`,
`block-arc`, `chevron`, `trapezoid`, `diamond`. If a brand needs
`snip1Rect`, `homePlate`, `roundedRect` etc., add them to `_SHAPE_KIND`
upstream as a one-liner per kind. For freeform custGeom with no preset, the
decompiler emits `native` (verbatim carry) automatically — no scaffolder action.

## Evidence
- `frame-outline` shipped as 4-line compound → visible rounded corners +
  shadows + 16% structural diff on styleguide-frames.
- Converted to single `MSO_SHAPE.PARALLELOGRAM` with `adj1:dx/w` → corners
  sharp, no shadow leak, frames now editable as one shape each.
- Same swap applied to `text-image-grid`, `key-figures-image`,
  `thank-you`, `graphic-image`.
