---
name: svg
description: Generate SVG diagrams from a compact DSL with brand-resolved colors. Use for charts, flows, and schematic 2D graphics.
---

# feinbild — SVG diagrams

`feinbild` is a command on your PATH. Two steps: expand a `.svg.dsl` to `.svg`
(brand colors resolved), then render to PNG.

```bash
feinbild svg expand chart.svg.dsl --brand feinschliff   # -> chart.svg
feinbild svg render chart.svg                           # -> chart.png
```

`--brand` (or a leading `@brand <name>` line in the DSL) selects the brand;
`render` takes no brand (it consumes already-resolved colors). Write outputs
into the project so other plugins can consume them.
