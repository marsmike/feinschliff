# CLAUDE.md — Feinschliff plugin

Working memory for AI contributors to this codebase. Read before touching
`examples/`, build scripts, or diagram pipelines.

## Examples folder discipline

`feinschliff/examples/` is a public-facing showcase, watched by users browsing
the repo on GitHub. **Users want proof of high-quality generation, not the
DSL inputs.** Keep the folder ruthlessly clean.

**Allowed in `examples/`:**

- `README.md` (one per example directory + the top-level one)
- `*.pdf` — rendered deck previews, multi-fixture preview sheets
- `*.pptx` — downloadable PowerPoint output
- `*.png` — rendered diagrams + per-slide thumbnails
- `ATTRIBUTION.md` — only where third-party content licensing requires it (currently `refurbish/`)

**Forbidden in `examples/` (move to `.debug/`):**

- `brief.txt`, `content_plan.yaml`, `design_brief.json` — the deck inputs
- `wireframe.svg` — diagnostic visualization
- `verify_report.md` — diagnostic output
- `*.exc.dsl`, `*.excalidraw` — Excalidraw DSL + intermediate JSON
- `*.svg.dsl`, `*.svg` — SVG DSL + intermediate SVG
- `*.yaml` build plans (e.g. `feinschliff-showcase.yaml`)
- Any other "how it was built" intermediate

## The `.debug/` mirror

`feinschliff/.debug/` is gitignored. It mirrors the `examples/` directory
structure and holds every intermediate / debug artifact that used to clutter
`examples/`. Build scripts that regenerate examples should:

1. Render the full chain to `.debug/examples/<mirror-path>/`.
2. Copy only the user-facing final artifacts (pdf / pptx / png) into
   `examples/<path>/`.

When you (the AI) regenerate any example output, write everything to
`.debug/` first, then mirror the polished artifacts to `examples/`. Never
add a new file type to `examples/` without first asking whether it belongs
in `.debug/` instead.

**This also covers ad-hoc / debugging renders.** A/B comparison runs,
prototype-render-backend testing, one-off PNG inspection — all of it
lands under `feinschliff/.debug/<descriptive-subdir>/`, never `/tmp/`.
Even single-use renders. The discipline: every intermediate file the
project generates lives inside `.debug/` so the contributor can scrub
through them later without hunting across `/tmp` or `~/Downloads`.

## Diagram pipeline notes

- **DSL expander** — `lib/diagrams/excalidraw_expand.py`. Primitives:
  `box`, `ellipse`, `diamond`, `dot`, `line` (with `dashed` flag), `arrow`
  (with `label:"..."`), `text` (levels: `title`, `subtitle`, `eyebrow`,
  `body`, `detail`, `mono`), `theme dark`, `group`. Color tokens go
  through `brand_bridge.resolve()`; upstream Excalidraw color names
  (`start`, `end`, `decision`, `ai`, `inactive`, `error`, `code`, `data`)
  alias onto brand tokens. `\\n` inside a quoted label becomes a real
  newline. Label color flips to `paper` on dark fills (luminance check).
  Arrow routing is **edge-to-edge straight line** along the center-to-
  center ray (matches upstream Excalidraw's `make_arrow`); no Z-elbows,
  no collision avoidance — author places boxes so straight arrows have
  room.
- **Render dispatcher** — `lib/diagrams/render.py:_render_excalidraw`.
  Tries **`render_rough`** (pure-Python: `rough` Python port +
  `cairosvg`, ~150ms, no browser) first with `roughness=0 +
  disableMultiStroke=True` for the clean "normal" Excalidraw look.
  Falls back to **`render_playwright`** (real Excalidraw web app in
  headless Chromium, ~1.5s + 200MB) when the rough path is unavailable
  or the document contains elements it doesn't model (freedraw / image
  / frame).
- `expand_diagram_blocks` (lib/dsl/expander.py) cache key includes
  `{slide_index, kind, w, h, brand_dir.name, body}` — do not regress to
  hashing only `body`.
- Diagram validators (`validate_diagrams`, `_color`, `_text_size`) run in
  both `feinschliff build` and `feinschliff deck build`. Keep parity if
  you add another build entry point.

## Verify the rules with `git status`

After any examples regeneration, `git status` should show:

- modifications only to `*.pdf` / `*.pptx` / `*.png` / `README.md` under `examples/`
- untracked changes only under `.debug/`

If `git status` shows a `.yaml`, `.json`, `.dsl`, `.svg`, or `.txt` file
under `examples/`, you've broken the discipline — move it to `.debug/` and
update the README to stop referencing it.
