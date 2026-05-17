# Examples — Feinschliff

Polished, rendered proof of the Feinschliff surfaces. Open them straight
from GitHub without running any build.

## Canonical showcase

The `feinschliff/` directory ships the full 43-layout template as
**`Feinschliff-Template.pdf`** + **`Feinschliff-Template.pptx`** — one page
per layout in taxonomy order (covers → editorial → data → strategic → text
→ diagrams → end). Every layout passes `feinschliff verify` (layout +
chrome + LLM-judged) before publishing.

## Where the other examples went

Earlier this repo also shipped:

- `decks/` — 7 domain demo decks across 4 narrative frames and 5 brands
  (~9 MB).
- `refurbish/` — NASA SEWP slide refurbish (before/after).
- `excalidraw/` — 3 standalone concept diagrams across 3 brands.
- `svg/` — 3 standalone infographics.

They were moved out of the public repo in 2026-05-16 (commit history
under `chore: move examples/* to vault`) because the rendered binaries
bloated every clone for no runtime benefit — they were proof-of-craft
artifacts, not part of the toolkit. The canonical showcase above is
sufficient to evaluate every layout.

To regenerate any of them locally, run `uv run feinschliff deck build`
against the original `content_plan.yaml`. For standalone diagrams use
the `feinschliff:excalidraw` or `feinschliff:svg` skills directly.

## Brand-pack previews

For comprehensive brand coverage see the interactive gallery at
**[docs/brands/](../../docs/brands/)** — 12 brand packs × 43 layouts
rendered as 516 PNGs with role and license badges.
