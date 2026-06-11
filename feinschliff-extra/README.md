# feinschliff-extra

Fourteen additional brand packs for [feinschliff](https://github.com/marsmike/feinschmiede).
No Python, no CLI — just brand tokens and layouts that feinschliff picks up
automatically once the plugin is installed.

## Install

```bash
/plugin marketplace add marsmike/feinschmiede   # once per machine
/plugin install feinschliff-extra@feinschmiede
```

Then use any brand with `/deck --brand <name>` or `FEINSCHLIFF_BRAND=<name>`.

## Brand packs

| Pack | Description | License |
|---|---|---|
| `annual-review` | MS gallery "Annual Review" port — pastel section panels, black ink, Arial Nova | MIT¹ |
| `binance` | Bold yellow accent on a deep crypto-black canvas, tabular numerics | MIT |
| `catppuccin-latte` | Light, warm pastel theme — Catppuccin's daylight flavor | MIT |
| `catppuccin-macchiato` | Medium-dark Catppuccin flavor — gentle contrast | MIT |
| `feinschliff-dark` | Inverted-canvas variant of feinschliff — navy-900 surface | MIT |
| `ferrari` | Near-black canvas, Rosso Corsa accent, cinematic editorial | MIT |
| `geometric` | MS gallery "The power of communication" (Geometric) port — flat colour blocks, Arial Black | MIT¹ |
| `gruvbox-dark` | Retro warm palette — soft brown surfaces and muted earthtone accents | MIT |
| `gs-ramspau` | Bespoke 8-layout school pack — wiese green + warm paper | MIT |
| `nord` | Arctic north-bluish palette for clear and minimal interfaces | MIT |
| `scientific` | MS gallery "Scientific discovery" pitch-deck port — engraved artwork, condensed display | MIT¹ |
| `shapes` | MS gallery "The power of communication" (Shapes) port — scattered geometry, blue title circle | MIT¹ |
| `solarized-dark` | Ethan Schoonover's precision-engineered warm yellows on teal-black | MIT |
| `spotify` | Spotify green accent on near-black, pill-and-circle geometry | MIT |

¹ Layout DSL + tokens are MIT. The four MS-gallery packs were decompiled
from free Microsoft presentation templates
(<https://powerpoint.cloud.microsoft/create/en/presentation-templates/>);
carried template chrome (vector freeforms, table styles, background artwork)
is © Microsoft, redistributed under Microsoft's free-use terms. Each pack's
13 layouts ship pre-slotified (`text_N` / `image` slots with the source
showcase copy as defaults) — measured ≥95 % block fidelity against the
source renders.

## Requirements

`feinschliff` must be installed first. `feinschliff-extra` adds no Python —
it only provides brand directories that feinschliff discovers via the plugin
brand path.

## License

MIT — see repo root [`LICENSE`](../LICENSE). Third-party brand marks (`binance`,
`ferrari`, `spotify`) are for demonstration only; not official design systems.
Upstream palette licenses: Catppuccin MIT, Gruvbox MIT, Nord MIT, Solarized MIT.
