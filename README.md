<p align="center">
  <img src="feinschliff/brands/feinschliff/assets/gem.svg" alt="Feinschliff gem mark" width="120">
</p>

<h1 align="center">feinschliff</h1>

<p align="center">
  <strong>Brand-pluggable design system for Claude Code</strong><br>
  Turn DESIGN.md or HTML into brand-perfect PowerPoint decks.
</p>

[![CI](https://github.com/marsmike/feinschliff/actions/workflows/ci.yml/badge.svg)](https://github.com/marsmike/feinschliff/actions/workflows/ci.yml)
[![Pages](https://github.com/marsmike/feinschliff/actions/workflows/pages.yml/badge.svg)](https://marsmike.github.io/feinschliff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-orange)](https://docs.claude.com/claude-code)

[Browse the brand gallery](https://marsmike.github.io/feinschliff/brands/) — every brand pack rendered against every layout.

## Plugins

This repo ships three independent Claude Code plugins. Install only what you need.

| Plugin | Install | Description |
|---|---|---|
| [`feinschliff`](feinschliff/) | `/plugin marketplace add marsmike/feinschliff` | Core generator — `/deck`, `/excalidraw`, `/svg` skills + `feinschliff` CLI. Ships with 3 brand packs and 50 layouts. |
| [`feinschliff-extra`](feinschliff-extra/) | `/plugin marketplace add marsmike/feinschliff-extra` | 10 additional brand packs (light/dark themes, terminal palettes, bold corporate looks). Requires `feinschliff`. |
| [`feinschliff-builder`](feinschliff-builder/) | `/plugin marketplace add marsmike/feinschliff-builder` | Brand-pack authoring toolkit — compile HTML, decompile PPTX, verify quality, improve brand packs. Requires `feinschliff`. |

## Why separate plugins?

Most users only need `feinschliff` — the core generator with the default brand pack.
`feinschliff-extra` and `feinschliff-builder` are optional add-ons:

- **`feinschliff-extra`** is for users who want more brand variety without writing
  any DSL. Just install and pick a brand.
- **`feinschliff-builder`** is for brand authors who want to create or tune their
  own brand pack. It adds six authoring CLI subcommands and two AI-assisted skills.

Splitting them keeps the core plugin lean and avoids installing build tools that
most end users will never run.

## Quick start

```bash
/plugin marketplace add marsmike/feinschliff
/deck "Q1 update: 12 launches, 3 customers, $4.2M ARR"
```

To use a different brand:

```bash
/plugin marketplace add marsmike/feinschliff-extra
FEINSCHLIFF_BRAND=catppuccin-macchiato /deck "..."
```

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). All commits require a
[DCO](https://developercertificate.org/) sign-off (`git commit -s`).

## Author

[Mike Mueller](https://marsmike.com) — `mike@objektarium.de`

## License

MIT — see [LICENSE](LICENSE). Third-party attribution: [NOTICE.md](NOTICE.md).
Security policy: [SECURITY.md](SECURITY.md).
