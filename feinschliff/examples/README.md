# Examples — Feinschliff

Polished, rendered proof of the Feinschliff surfaces. The big binaries
(deck PPTX + PDF) live on R2 to keep the repo lightweight — `git clone`
stays small; the plugin install ships the renderer, not the rendered
artifacts.

## Canonical showcase

The `feinschliff/` directory documents the full 50-layout template:

- **[`Feinschliff-Template.pdf`](https://assets.marsmike.com/feinschliff/examples/feinschliff/Feinschliff-Template.pdf)** —
  one page per layout in taxonomy order (covers → editorial → data →
  strategic → text → diagrams → image → end).
- **[`Feinschliff-Template.pptx`](https://assets.marsmike.com/feinschliff/examples/feinschliff/Feinschliff-Template.pptx)** —
  the same 50 slides as an editable PowerPoint.

Narrative showcase:

- **[`water-cycle/deck.pdf`](https://assets.marsmike.com/feinschliff/examples/water-cycle/deck.pdf)** /
  **[`water-cycle/deck.pptx`](https://assets.marsmike.com/feinschliff/examples/water-cycle/deck.pptx)** —
  30-slide SCQA "Hidden Engine" deck on the `nord` brand. See
  [`water-cycle/README.md`](water-cycle/README.md) for the story arc
  and slide-by-slide layout map.

Every layout passes `feinschliff verify` (layout + chrome + LLM-judged)
before publishing.

## Brand-pack gallery

The full visual reference — every brand × every layout — is the
interactive gallery at
**<https://marsmike.github.io/feinschliff/brands/>** (12 brands × 50
layouts = 600 slide previews). Generic placeholders are duotoned to
each brand's palette so every brand reads as native.

## Regenerating locally

```bash
cd feinschliff
# Single-brand layout sheet (PDF + PPTX):
uv run python scripts/render_brand_preview.py feinschliff
# Narrative deck:
uv run feinschliff deck build .debug/water-cycle/content_plan.yaml \
    -o examples/water-cycle/deck.pptx
# Brand-gallery atlas (one PNG per brand × layout):
uv run python scripts/render_brand_atlas.py
```

PDFs and PPTXs are gitignored under `examples/` — local renders stay
out of the repo by design.

## Where the other examples went

Earlier this repo also shipped:

- `decks/` — 7 domain demo decks across 4 narrative frames and 5 brands.
- `refurbish/` — NASA SEWP slide refurbish (before/after).
- `excalidraw/` — 3 standalone concept diagrams across 3 brands.
- `svg/` — 3 standalone infographics.

They were moved out of the public repo in 2026-05-16 because the
rendered binaries bloated every clone for no runtime benefit. The
canonical showcase + brand gallery are sufficient to evaluate every
layout.
