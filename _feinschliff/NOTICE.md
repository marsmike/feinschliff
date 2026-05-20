# NOTICE — Feinschliff plugin

This plugin is licensed MIT (see repo root `LICENSE`).

It bundles or depends on the following third-party material. Each entry retains its upstream license; the listing below is provided in good faith for attribution.

## Fonts (referenced by name; loaded by the rendering OS)

- **Noto Sans / Noto Sans Mono** — Copyright (c) Google LLC. SIL Open Font License 1.1. https://github.com/notofonts/noto-fonts

## Runtime dependencies

- **python-pptx** — Copyright (c) Steve Canny. MIT License. https://github.com/scanny/python-pptx
- **Playwright** — Copyright (c) Microsoft. Apache License 2.0. https://github.com/microsoft/playwright

## Methodology credit

- **Excalidraw skill methodology** (`skills/excalidraw/references/methodology.md`) — the visual-argument framing ("diagrams argue, not display"), isomorphism / education tests, depth assessment, the nine-pattern visual library (fan-out, convergence, tree, cycle, cloud, assembly line, side-by-side, gap), container-discipline rules (including the <30%-in-containers threshold), hierarchy-through-scale dimensions (Hero 300×150 / Primary 180×90 / Secondary 120×60), the evidence-artifact concept, the shape-semantic mapping, and the hard-rule constants (`fontFamily: 3`, `roughness: 0`, `opacity: 100`) originated in [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) by Cole Medin. The implementation in this plugin (DSL authoring layer, brand-pack color resolution, arrow routing, structural validator, renderer, render template, and pipeline integration) is original to feinschliff.

## Upcoming (v0.2 — DESIGN.md ingestion)

- **VoltAgent / awesome-design-md** — MIT License. https://github.com/VoltAgent/awesome-design-md
  - Feinschliff v0.2 will accept a `DESIGN.md` file from the awesome-design-md collection (76+ public design systems) as direct brand-pack input. Credit will be added to this NOTICE at that release.
