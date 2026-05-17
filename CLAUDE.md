# CLAUDE.md — feinschliff repo

Working memory for AI contributors to this repo. Read before touching
`feinschliff/examples/`, build scripts, the diagram pipeline, or the brand
gallery / R2 publish flow.

## Repo size discipline

This repo stays small on purpose. Rendered artifacts are NOT committed:

- `docs/brand-previews/` — per-brand × per-layout PNGs (gitignored; ~50 MB
  local) → uploaded to R2 via `feinschliff/scripts/upload_brand_previews_to_r2.py`.
- `docs/brands/` and `docs/index.html` — gallery HTML, generated fresh by
  the Pages workflow on every push to `main`.
- `feinschliff/examples/<brand>/Template.{pdf,pptx}` — multi-slide brand
  showcases (gitignored).
- `feinschliff/.debug/` — every intermediate / debug artifact (see below).

The only committed binary assets are `feinschliff/docs/images/hero-grid.png`
and `feinschliff/docs/images/showcase.gif` — small marketing material
referenced from the README.

## Examples folder discipline

`feinschliff/examples/` is a public-facing showcase, watched by users browsing
the repo on GitHub. **Users want proof of high-quality generation, not the
DSL inputs.** Keep the folder ruthlessly clean.

**Allowed in `feinschliff/examples/`:**

- `README.md` (one per example directory + the top-level one)
- `*.pdf` — rendered deck previews, multi-fixture preview sheets
- `*.pptx` — downloadable PowerPoint output
- `*.png` — rendered diagrams + per-slide thumbnails
- `ATTRIBUTION.md` — only where third-party content licensing requires it
  (currently `refurbish/`)

**Forbidden in `feinschliff/examples/` (move to `feinschliff/.debug/`):**

- `brief.txt`, `content_plan.yaml`, `design_brief.json` — the deck inputs
- `wireframe.svg` — diagnostic visualization
- `verify_report.md` — diagnostic output
- `*.exc.dsl`, `*.excalidraw` — Excalidraw DSL + intermediate JSON
- `*.svg.dsl`, `*.svg` — SVG DSL + intermediate SVG
- `*.yaml` build plans (e.g. `feinschliff-showcase.yaml`)
- Any other "how it was built" intermediate

## The `feinschliff/.debug/` mirror

`feinschliff/.debug/` is gitignored. It mirrors the `feinschliff/examples/`
directory structure and holds every intermediate / debug artifact that used
to clutter `examples/`. Build scripts that regenerate examples should:

1. Render the full chain to `feinschliff/.debug/examples/<mirror-path>/`.
2. Copy only the user-facing final artifacts (pdf / pptx / png) into
   `feinschliff/examples/<path>/`.

When you (the AI) regenerate any example output, write everything to
`.debug/` first, then mirror the polished artifacts to `examples/`. Never
add a new file type to `examples/` without first asking whether it belongs
in `.debug/` instead.

**This also covers ad-hoc / debugging renders.** A/B comparison runs,
prototype-render-backend testing, one-off PNG inspection — all of it
lands under `feinschliff/.debug/<descriptive-subdir>/`, never `/tmp/`.
Even single-use renders. Every intermediate file the project generates
lives inside `.debug/` so the contributor can scrub through them later
without hunting across `/tmp` or `~/Downloads`.

## Diagram pipeline notes

- **DSL expander** — `feinschliff/lib/diagrams/excalidraw_expand.py`.
  Primitives: `box`, `ellipse`, `diamond`, `dot`, `line` (with `dashed`
  flag), `arrow` (with `label:"..."`), `text` (levels: `title`, `subtitle`,
  `eyebrow`, `body`, `detail`, `mono`), `theme dark`, `group`. Color tokens
  resolve through `brand_bridge.resolve()`; upstream Excalidraw color names
  (`start`, `end`, `decision`, `ai`, `inactive`, `error`, `code`, `data`)
  alias onto brand tokens. `\\n` inside a quoted label becomes a real
  newline. Label color flips to `paper` on dark fills (luminance check).
  Arrow routing is **edge-to-edge straight line** along the center-to-center
  ray (matches upstream Excalidraw's `make_arrow`); no Z-elbows, no
  collision avoidance — author places boxes so straight arrows have room.
- **Render dispatcher** — `feinschliff/lib/diagrams/render.py`. Tries
  **`render_rough`** (pure-Python: `rough` Python port + `cairosvg`, ~150
  ms, no browser) first with `roughness=0 + disableMultiStroke=True` for
  the clean "normal" Excalidraw look. Falls back to **`render_playwright`**
  (real Excalidraw web app in headless Chromium, ~1.5 s + 200 MB) when
  the rough path is unavailable or the document contains elements it
  doesn't model (freedraw / image / frame).
- `expand_diagram_blocks` (`feinschliff/lib/dsl/expander.py`) cache key
  includes `{slide_index, kind, w, h, brand_dir.name, body}` — do not
  regress to hashing only `body`.
- Diagram validators (`validate_diagrams`, `_color`, `_text_size`) run in
  both `feinschliff build` and `feinschliff deck build`. Keep parity if
  you add another build entry point.

## Brand-gallery publish flow

The gallery at `https://marsmike.github.io/feinschliff/brands/` is the
public face of the brand-pack work. Update path:

1. `cd feinschliff && uv run python scripts/render_brand_atlas.py --force --workers 8`
   — renders `docs/brand-previews/<brand>/<NN>-<id>.png` for all 12 brands.
2. `uv run python scripts/build_brand_atlas_overview.py` — composes the
   per-brand `_atlas.png` grid overview.
3. `uv run python scripts/upload_brand_previews_to_r2.py --workers 8` —
   uploads to `r2://marsmike-assets/feinschliff/brand-previews/<brand>/`
   via wrangler (reuses the operator's existing wrangler auth).
4. Push to `main` OR run `gh workflow run pages` — Pages workflow rebuilds
   the gallery HTML with a fresh `?v=<timestamp>` cache-bust on every run.

The PPTX/PDF showcases (`scripts/render_brand_preview.py`) are an
orthogonal artifact — multi-slide downloadable templates per brand, also
gitignored.

## Commit + push hygiene

- All commits require DCO sign-off: `git commit -s -m "..."`. CI enforces.
- Branch protection on `main`: status checks must pass; linear history; no
  force-pushes / deletions. PR reviews are NOT required (solo dev). Admin
  bypass is enabled so direct-to-main pushes work; CI runs post-hoc.
- Don't add new file types to `feinschliff/examples/` (see discipline
  above). Don't commit PNG/PPTX/PDF outside the allowed list.

## Verify the rules with `git status`

After any examples regeneration, `git status` should show:

- modifications only to `*.pdf` / `*.pptx` / `*.png` / `README.md` under
  `feinschliff/examples/`
- untracked changes only under `feinschliff/.debug/` or `docs/brand-previews/`

If `git status` shows a `.yaml`, `.json`, `.dsl`, `.svg`, or `.txt` file
under `feinschliff/examples/`, you've broken the discipline — move it to
`.debug/` and update the README to stop referencing it.
