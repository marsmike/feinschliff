# feinschliff

> *Feinschliff* — German for "fine polish." Brand-pluggable design system that
> builds `.pptx` decks from a DSL and per-brand tokens.

[Browse the brand gallery](https://marsmike.github.io/feinschliff/brands/) — every brand pack rendered against every layout.

![Feinschliff showcase grid — six slides rendered from the eponymous brand pack](docs/images/hero-grid.png)

## Install

```bash
/plugin marketplace add marsmike/feinschliff
```

## What it does

Three Claude Code skills:

- **`/deck`** — create or polish a brand-compliant `.pptx` from a brief or rough
  draft. Generates speaker notes and an annotated handout PDF via `deck book`.
- **`/excalidraw`** — author concept-flow diagrams in a brand-aware DSL.
- **`/svg`** — author SVG infographics and custom charts in a brand-aware DSL.

Three CLI subcommands (`feinschliff <subcommand>`):

| Subcommand | What it does |
|---|---|
| `build` | Expand a single `.slide.dsl` into a `.pptx` |
| `deck` | Multi-slide composer with layout picker + speaker notes |
| `ship` | One-command build + verify + verify-quality with a single verdict |

## Quick start

```bash
# Claude Code skill
/deck "Q1 update: 12 launches, 3 customers, $4.2M ARR"

# Pick a different brand
FEINSCHLIFF_BRAND=catppuccin-macchiato /deck "..."

# Standalone CLI (no Claude Code required)
feinschliff build layouts/quote.slide.dsl \
  --brand feinschliff --content tests/fixtures/layouts/quote.yaml -o out.pptx
```

## Brand packs (3 ship in the box)

| Pack | Description | License |
|---|---|---|
| `feinschliff` (default) | Navy ramp + warm paper + single gold accent. Bauhaus register | MIT |
| `blank` | Minimal scaffold, no color opinions | MIT |
| `claude` | Anthropic Claude brand colors | MIT |

Additional brands are available as separate plugins:

- **[feinschliff-extra](https://github.com/marsmike/feinschliff)** — 10 more brand packs
  (terminal palettes, light/dark themes, bold corporate looks).
- **[feinschliff-builder](https://github.com/marsmike/feinschliff)** — authoring toolkit
  to compile HTML to DSL, decompile existing PPTX files, and verify brand quality.

## 50 shared layouts

The toolkit ships 50 layout templates covering title slides, chapter dividers,
content grids, charts, diagrams, and more. Every layout renders with any brand pack.
Brand packs can add or override layouts in their own `layouts/` directory.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — pipeline walkthrough
- [`docs/brand-system.md`](docs/brand-system.md) — DESIGN.md authoring + bake recipe
- [`docs/dsl-grammar.md`](docs/dsl-grammar.md) — DSL primitive reference
- [`docs/port-your-brand.md`](docs/port-your-brand.md) — new-brand tutorial
- [`docs/BRAND-PACK-CONTRACT.md`](docs/BRAND-PACK-CONTRACT.md) — brand-pack specification

## License

MIT — see repo root [`LICENSE`](../LICENSE). Third-party attribution: [`NOTICE.md`](../NOTICE.md).
