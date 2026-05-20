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

## For `feinschliff:compile`
When scaffolding a brand pack with diagonal frames, rotated shapes, or
asymmetric callouts: check MSO_SHAPE enum FIRST before decomposing. The
toolkit already exposes `parallelogram`, `pie`, `pie-wedge`, `arc`,
`block-arc`, `chevron`, `trapezoid`, `diamond`. If a brand needs
`snip1Rect`, `homePlate`, `roundedRect` etc., add them to `_SHAPE_KIND`
upstream as a one-liner per kind.

## Evidence
- `frame-outline` shipped as 4-line compound → visible rounded corners +
  shadows + 16% structural diff on styleguide-frames.
- Converted to single `MSO_SHAPE.PARALLELOGRAM` with `adj1:dx/w` → corners
  sharp, no shadow leak, frames now editable as one shape each.
- Same swap applied to `text-image-grid`, `key-figures-image`,
  `thank-you`, `graphic-image`.
