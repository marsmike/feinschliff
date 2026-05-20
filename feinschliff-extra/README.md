# feinschliff-extra

Ten additional brand packs for [feinschliff](https://github.com/marsmike/feinschliff).
No Python, no CLI — just brand tokens and layouts that feinschliff picks up
automatically once the plugin is installed.

## Install

```bash
/plugin marketplace add marsmike/feinschliff-extra
```

Then use any brand with `/deck --brand <name>` or `FEINSCHLIFF_BRAND=<name>`.

## Brand packs

| Pack | Description | License |
|---|---|---|
| `binance` | Bold yellow accent on a deep crypto-black canvas, tabular numerics | MIT |
| `catppuccin-latte` | Light, warm pastel theme — Catppuccin's daylight flavor | MIT |
| `catppuccin-macchiato` | Medium-dark Catppuccin flavor — gentle contrast | MIT |
| `feinschliff-dark` | Inverted-canvas variant of feinschliff — navy-900 surface | MIT |
| `ferrari` | Near-black canvas, Rosso Corsa accent, cinematic editorial | MIT |
| `gruvbox-dark` | Retro warm palette — soft brown surfaces and muted earthtone accents | MIT |
| `gs-ramspau` | Bespoke 8-layout school pack — wiese green + warm paper | MIT |
| `nord` | Arctic north-bluish palette for clear and minimal interfaces | MIT |
| `solarized-dark` | Ethan Schoonover's precision-engineered warm yellows on teal-black | MIT |
| `spotify` | Spotify green accent on near-black, pill-and-circle geometry | MIT |

## Requirements

`feinschliff` must be installed first. `feinschliff-extra` adds no Python —
it only provides brand directories that feinschliff discovers via the plugin
brand path.

## License

MIT — see repo root [`LICENSE`](../LICENSE). Third-party brand marks (`binance`,
`ferrari`, `spotify`) are for demonstration only; not official design systems.
Upstream palette licenses: Catppuccin MIT, Gruvbox MIT, Nord MIT, Solarized MIT.
