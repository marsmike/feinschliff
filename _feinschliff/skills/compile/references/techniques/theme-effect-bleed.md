# Theme effect bleed through `<p:style>`

## Pattern
python-pptx's `add_shape` / `add_connector` writes a `<p:style>` block that
references the theme's `<a:effectRef idx="2">` — a soft outer-shadow. Both
PowerPoint and LibreOffice honour it at render time **even when** the code
sets `shape.shadow.inherit = False` (which only writes an explicit
`<a:effectLst/>` on the shape — it doesn't drop the styleRef).

## Trigger
Every shape and connector emitted via python-pptx gets a phantom drop-shadow
below it. Catastrophic for flat-design brands (modern Bauhaus, anything
post-2015). Most visible on stroked outlines and high-contrast color blocks.

## Fix shape
Strip `<p:style>` from each newly-added shape AND connector at emit time.
We added `_strip_theme_style()` and call it from `_emit_rect`, `_emit_shape`,
and (later) `_emit_line`. Without the line-emitter fix, every parallelogram
edge stamps a shadow even though the per-shape effects are off.

## For `feinschliff:compile`
When scaffolding any new brand pack: assume flat-design intent and verify
that all primitive emitters call `_strip_theme_style`. If a brand wants
shadows, opt in explicitly per-shape (`effect:allow`); don't inherit from
the theme.

## Evidence
- styleguide-frames pass 1: 5 parallelogram outlines all rendered with soft
  drop-shadows that source didn't have.
- bar-chart: orange bar rectangles all had visible shadow under them.
- Fixed by stripping `<p:style>` in shape emitter, then later in line
  emitter once we caught the bleed on connector primitives too.
