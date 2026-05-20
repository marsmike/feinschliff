# Feinschliff brand-pack — full layout reference

The full 50-layout template lives on R2 (kept out of the repo to stay
lightweight — the plugin install includes the renderer, not the
pre-rendered binaries):

- **[`Feinschliff-Template.pdf`](https://assets.marsmike.com/feinschliff/examples/feinschliff/Feinschliff-Template.pdf)** — every layout
  rendered once, in the taxonomy order below. Use this to browse the
  slide vocabulary.
- **[`Feinschliff-Template.pptx`](https://assets.marsmike.com/feinschliff/examples/feinschliff/Feinschliff-Template.pptx)** — the same
  50 slides as an editable PowerPoint, useful as a starting point.

Live brand gallery (every brand × every layout):
👉 <https://marsmike.github.io/feinschliff/brands/>

To regenerate locally:

```bash
cd feinschliff
uv run python scripts/render_brand_preview.py feinschliff
# outputs to examples/feinschliff/Feinschliff-Template.{pdf,pptx} locally;
# binaries are gitignored so they stay out of the repo by design.
```

## Layout vocabulary

The 50 layouts cover the full deck-authoring surface:

- **Cover variants** (3) — `title-orange`, `title-ink`, `full-bleed-cover`
- **Section openers** (2) — `chapter-orange`, `chapter-ink`
- **Editorial** (4) — `executive-summary`, `action-title`, `key-takeaways`, `quote`
- **Data** (14) — `kpi-grid`, `bar-chart`, `line-chart`, `stacked-bar`, `waterfall`,
  `2x2-matrix`, `venn`, `pyramid`, `funnel`, `scorecard`, `process-flow`,
  `gantt`, `table`, `v-model`
- **Strategic** (6) — `recommendation`, `next-steps`, `roadmap`, `timeline`,
  `risk-matrix`, `risk-register`
- **Text layouts** (9) — `horizontal-bullets`, `vertical-bullets`,
  `two-column-cards`, `three-column`, `four-column-cards`, `text-picture`,
  `agenda`, `components-showcase`, `graphical`
- **Diagrams** (4) — `excalidraw-diagram`, `excalidraw-diagram-full`,
  `svg-infographic`, `svg-infographic-full`
- **Image-bearing** (7) — `agenda-photo`, `chart-photo`, `end-image`,
  `full-bleed-editorial`, `kpi-photo`, `photo-grid`, `photo-strip-four`
- **Closer** (1) — `end`

The other 11 brand packs ship the same layouts with palette-substituted
colors (plus the shared placeholder photo duotoned to each brand). See
[`docs/brand-system.md`](../../docs/brand-system.md) for the brand-pack
contract.
