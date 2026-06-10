# Architecture

`feinschmiede` is a family of Claude Code plugins for branded media creation —
decks, images & 2D, video, audio — plus a codebase-intelligence plugin, built
over one shared Python engine. This document is the map: how the pieces fit,
why the boundaries are where they are, and the rules a contributor must keep.

## The two coupling rules

Everything here follows from two deliberate constraints:

1. **Plugins are coupled by CLI capabilities, never by file paths or imports.**
   When one plugin needs another's capability (e.g. `feinschnitt` building a
   voiceover, or `feinschliff` rendering a diagram), it calls the sibling's
   bare command (`feinklang tts …`, `feinbild excalidraw …`) — guaranteed on
   PATH by a declared plugin `dependency`. No plugin reaches into another
   plugin's files, and no plugin imports another plugin's Python package.

2. **Shared code lives in exactly one engine, vendored — not duplicated.**
   The `feinschmiede` engine package holds only what 2+ plugins need (the
   cross-media brand/look system and the diagram engine). It is built once and
   vendored as a wheel into each plugin's venv, so there is a single source of
   truth and every plugin still installs independently.

The one sanctioned exception to rule 1 is the **office sub-family**:
`feinschliff-builder` is Python-coupled to `feinschliff` by design (it is an
authoring/verification layer *on top of* the office generator and imports it).
That edge points builder → office (acyclic) and is declared in
`feinschliff-builder`'s `plugin.json`.

## The components

| Component | Kind | Role |
|---|---|---|
| **feinschmiede** | engine (library) | Cross-media brand/token/discovery system + the diagram engine (SVG & Excalidraw DSL expanders, render dispatcher, structural validator, text metrics). Not a plugin; vendored as a wheel. |
| **feinschliff** | plugin | Office / decks — `.slide.dsl` + brand tokens + content → `.pptx`. Ships 3 brand packs + 50 layouts. |
| **feinbild** | plugin | Image & 2D — AI images (Replicate/Gemini) + SVG + Excalidraw diagrams, over the engine. |
| **feinklang** | plugin | Audio — ElevenLabs voiceover. |
| **feinschnitt** | plugin | Video — Remotion videos + CLI session recordings; composes feinbild + feinklang. |
| **feinblick** | plugin | Codebase intelligence — unified Python + Claude-skill findings, audit gate, agent report. Standalone, stdlib-only. |
| **feinschliff-builder** | plugin | Brand-pack authoring toolkit (compile-html, decompile, verify, improve-brand). The office sub-family; imports feinschliff. |
| **feinschliff-extra** | plugin (data) | 10 extra brand packs. No Python. |

### Dependency directions

```
feinschmiede (engine)  ◀── feinbild ◀── feinschliff ◀── feinschliff-builder
        ▲                     ▲              │
        └──────────────┬──────┘              ├── feinschliff-extra (brand data)
                       │                     │
        feinschnitt ───┘ (calls feinbild + feinklang CLIs)
        feinklang  (engine-free; standalone)
        feinblick  (engine-free; standalone, stdlib-only)
```

Solid arrows are *import/vendor* dependencies (toward the engine). `feinschnitt`
depends on `feinbild` and `feinklang` only as **CLI calls**, not imports. The
engine never imports any plugin — a test (`feinschmiede/tests/
test_engine_smoke.py`) fails the build if any `feinschliff` import appears in
engine source.

## Distribution & the bootstrap layer

Every distributable plugin ships a `bin/<name>` launcher. On first run it:

1. builds a wheelhouse from the bundled source if none is present (a
   marketplace/git install ships no wheels — they're gitignored), then
2. provisions a self-contained venv from that wheelhouse **offline** and execs
   the real CLI; later runs just exec the installed CLI.

The venv is keyed on a content signature of **the wheelhouse + the plugin's
`pyproject.toml`**, so a plugin update (new wheels or bumped source) rebuilds
the venv instead of silently running stale code — the same content-hash idea
the whole family relies on for update detection (we deliberately do **not**
carry manual version fields in `plugin.json`/`marketplace.json`).

The launchers and each `build-wheels.sh` are **generated** from a single
manifest + templates in [`scripts/gen_launchers.py`](scripts/gen_launchers.py).
The bootstrap logic exists in exactly one place; CI runs
`gen_launchers.py --check` to keep the committed files in sync. `build-wheels.sh`
assembles the wheelhouse in a staging dir and swaps it into place only on
success (no half-populated wheelhouse can disable rebuilds), and pins the
third-party closure to the CI-tested lock via the committed `constraints.txt`.

> Phase 3 (PyPI Trusted Publishing) will replace the vendored-wheel bootstrap
> with a plain index install; the same `constraints.txt` pins that path too.

## The engine in more detail

```
feinschmiede/
  brand/            BrandPack — a cross-media "look" (a brand styles decks,
                    diagrams, AND video consistently)
  brand_discovery   discovery across bundled / plugin / env / cwd / user sources
  dsl/{ast,tokens}  DSL data model + DTCG-flavoured token loader (extends:
                    inheritance via DESIGN.md frontmatter, schema-validated)
  diagnostics       Defect / DiagnosticBag taxonomy
  diagrams/         svg_expand · excalidraw_expand · render (rough+cairosvg
                    primary, Playwright fallback) · brand_bridge · text_metrics
                    · structural_validator (overflow/overlap/collision checks)
  paths             compounds_dir() and other shared resource locations
```

**Brands are the strongest "common" justification:** the same brand must style a
deck, a diagram, and a video identically, so the brand/token/discovery system
belongs in the shared engine, not in any one plugin. Token resolution is
semantic-only (a fixed vocabulary of names like `accent`, `ink`, `chart-series-1`
resolved through brand tokens) with luminance-based contrast.

The render dispatcher tries the pure-Python **rough + cairosvg** path first
(~150 ms, no browser) and falls back to a real headless-Chromium Excalidraw
render only for documents it can't model (freedraw / image / frame). A missing
`libcairo` surfaces an actionable libcairo message, not a misleading
"install Playwright".

## The office pipeline (feinschliff)

`.slide.dsl` layout + brand tokens + content YAML →

```
parser → expander → pptx_emit → defect gating
```

`pipeline.compile_slide` is the **single** per-slide compile path shared by
`build`, `deck build`, and `verify-aspect`, so defect policy can't drift between
entry points. Diagram blocks render to PNG through the engine's svg/excalidraw
expanders, content-hash-cached on the merged (extends-resolved) brand tokens.

The advanced `deck` subcommands (storyline, wireframe, polish, book,
strict-static, autofix, …) are built on `feinschliff_builder`. Under the
per-plugin venv model the office venv does not contain that package, so these
subcommands follow rule 1: when the builder package isn't importable but the
`feinschliff-builder` CLI is on PATH (its venv bundles office + builder), office
re-execs the command through it; with neither, it exits with an accurate
`/plugin install feinschliff-builder@feinschmiede` hint. In a dev checkout
(everything in one venv) the inline path runs unchanged.

## Brand packs

A brand pack is discovered data: `tokens.json` (+ optional `DESIGN.md`,
`layouts/`, `assets/`). `feinschmiede.brand_discovery` scans every installed
plugin's `brands/` dir plus env/home overrides (`FEINSCHLIFF_BRAND_PATH`,
`~/.feinschliff/brands`) and the bundled packs, so co-installed packs unify
across plugin boundaries. The discovery error lists every searched source with
found/missing markers and the env-var fix.

The public gallery at <https://marsmike.github.io/feinschliff/brands/> renders
every pack against every layout; see
[`feinschliff/CLAUDE.md`](CLAUDE.md) for the publish flow.

## Testing & CI

CI gates, per `.github/workflows/ci.yml`:

- **per-package tests + ruff** for every Python package (feinschliff,
  feinschliff-builder, feinschmiede, feinbild, feinklang, feinschnitt,
  feinblick) — the `feinschliff lib tests` job name is a required status check
  and must not be renamed;
- **production render path** exercised with `libcairo2` installed (the
  rough+cairosvg path, not skipped);
- **wheel-install smoke** — each plugin's wheelhouse is built from source,
  the launcher bootstraps a clean venv offline, and the CLI is started (the
  sole distribution path, gated end-to-end);
- **consistency** — `gen_launchers.py --check`, `constraints.txt` freshness vs
  the lock, single-version coherence across packages, and a grep forbidding
  `uv run <cli>` / retired `lib.*` paths in skill docs.

## Conventions a contributor must keep

- Don't import one plugin's Python from another (except builder → office).
  Call the sibling CLI instead.
- Don't duplicate engine code into a plugin; put shared code in `feinschmiede`.
- Don't edit `bin/<name>` or `build-wheels.sh` by hand — edit
  `scripts/gen_launchers.py` and re-run it.
- Don't add manual `version` fields to `plugin.json`/`marketplace.json`; keep
  Python package versions aligned in `pyproject.toml` (CI enforces).
- Keep `feinschliff/examples/` to user-facing artifacts only; intermediates go
  under `.debug/` (see [`CLAUDE.md`](CLAUDE.md)).
- Sign off every commit (`git commit -s`).
