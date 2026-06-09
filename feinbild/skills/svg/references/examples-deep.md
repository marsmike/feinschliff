# SVG — Deep Infographic Examples

These examples target a dense, full-bleed composition on a large
`canvas` (the source below uses `canvas 6880x2880`; `virtual:WxH` works
too for an even higher render resolution). They demonstrate the extended
SVG DSL primitives — `polyline`, `polygon`, `path`, `area`,
`stacked_bar`, `brace`, `callout`, `swatch_grid`, `label_box`, `group` —
working together in a single composition.

Source files live in `examples/`.

## Yocto build pipeline (`yocto-build-pipeline.svg.dsl`)

Three-column layout: meta-layers (left) → BitBake hub (center) →
artifact outputs (right).

**Primitives demonstrated:**

| Primitive | Where used |
|---|---|
| `stacked_bar orient:vertical` | Left column — layer composition with 7 segments stacked top-to-bottom. Tokens carry semantic meaning (primary = product code, neutral = third-party). |
| `brace side:right` and `side:left` | "third-party" vs "product-owned" partition on the layer stack; "release artifacts" group on the output column. |
| `label_box variant:title \| body` | Hub + output rows — saves the rect+text pair idiom across ~10 outputs. |
| `polyline` | Two short horizontal "flow" arrows from stack → BitBake → outputs. |
| `path d="..."` | A short dashed connector between Sign and Publish boxes. Demonstrates the path-d allowlist. |
| `callout anchor:... at:... tail:auto` | "Regulators want SPDX 2.3+ + CVE list" annotation pointing at the SBOM output row. |
| `swatch_grid cols:4` | Bottom-row legend mapping the four primary token colors to roles. |

**Teaches:** how the new primitives compose. A diagram showing this
content used to need 30+ `rect` + `text` pairs; the extended primitives
cut that to ~20 lines, and the `stacked_bar` carries data semantics
(layer proportions) that the rect-pair version couldn't.

## When not to use a large canvas

A large `canvas` / `virtual:WxH` viewport is for dense compositions. If
the chart has fewer than 8 elements and a single visual idea, a small
canvas is faster to read. The larger viewport isn't "better quality" —
it's "more room for complexity."

| Use large canvas | Use small canvas |
|---|---|
| Build pipeline with layered inputs + multiple parallel outputs | Single bar chart with 4 categories |
| Architecture overview with zones, callouts, and a legend | Stat card grid (4 numbers + labels) |
| Comparison matrix with 6+ columns and 8+ rows | KPI banner with one big number and one sentence |

When in doubt, draft on a small canvas first; size up only if content
visibly cramps.
