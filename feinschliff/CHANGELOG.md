# Changelog

## Unreleased — hybrid PPTX+SVG decompiler

### Added
- **`lib/dsl/pptx_svg_decompile.py`** — hybrid PPTX+SVG decompiler,
  brand-agnostic. Higher-fidelity alternative to the existing
  `lib/dsl/pptx_decompile.py`: combines PPTX XML (canonical for shape
  semantics, placeholders, text run styles, theme color resolution)
  with an optional SVG pass (rendered from each slide's PDF via
  `pdf2svg`) that recovers bounding boxes for custGeom shapes whose
  PPTX xfrm is inherited from the layout. `theme_name`, `tokens_path`,
  and `placeholder_rel` are explicit parameters; footer-region text is
  emitted as plain `text` primitives (brands ship their own
  `footer(...)` compound and post-process the decompile output). Chart
  geometry extraction, pt-to-style classifier with `body-sm` for ≤12pt
  source text, and `cap="all"` → literal-uppercase conversion are
  preserved as generic improvements.
- **`scripts/brand_decompile_all.py`** — bulk-decompile every layout
  in a brand's `verify-map.yaml` from a source PPTX in one command.
  Snapshots existing layout files into `<brand>/layouts.bak/` before
  overwriting. Pairs with `scripts/brand_verify_loop.py` and the
  `improve-brand` skill to close the loop: decompile → verify →
  improve → re-verify.

### Changed
- **`cli/decompile.py`** — adds `--with-svg` flag that routes through
  the new hybrid decompiler instead of `pptx_decompile`. Backwards
  compatible: omitting the flag preserves the existing behaviour
  (primitive-level reverse mapping with asset extraction). The
  hybrid path does not yet extract pictures to disk — pictures land
  as placeholder slots in the emitted DSL, consistent with the
  `picture path:"{{ image | default:'…' }}"` slot convention.

### Why
Bundle 1 (verify-loop + improve-brand skill) gave a way to measure how
close a brand pack matches a source PPTX and an LLM loop to drive the
gap down — but brands still had to hand-write every `.slide.dsl` to
start (or use the existing simpler decompiler, which loses chart
geometry and footer chrome).

This bundle ships the workhorse decompiler whose output is good enough
to `feinschliff build` straight away. Combined with
`brand_decompile_all.py`, the full bootstrap → polishing loop now runs
end-to-end:

```bash
# 1. bootstrap layouts from a source deck
uv run python scripts/brand_decompile_all.py \
    --brand-pack brands/<brand> \
    --source-pptx <source>.pptx

# 2. measure how close the first pass is
uv run python scripts/brand_verify_loop.py \
    --brand-pack brands/<brand> \
    --source-pptx <source>.pptx

# 3. polish via the improve-brand skill (sub-agent per layout)
#    — see skills/improve-brand/SKILL.md
```

## Unreleased — brand verify-loop orchestrator + per-slide improvement skill

### Added
- **`scripts/brand_verify_loop.py`** — end-to-end orchestrator that
  chains source-PNG export → layout render → visual diff in one
  command. Any brand pack with a `verify-map.yaml` and source PPTX
  can run a single command to refresh `source-png/`, `render-png/`,
  `diff/report.json`, and `diff/score-trace.jsonl`. Mtime-keyed
  caching means re-runs after one DSL edit only rebuild the affected
  layout. Brand-specific paths drop in via `--brand-pack` and
  `--source-pptx`.
- **`skills/improve-brand/`** — new skill that wraps the orchestrator
  and dispatches **one sub-agent per layout** above a configurable
  threshold. Each sub-agent receives the per-slide overlay + current
  DSL via paths only (no inline PNG bytes), edits exactly one
  `.slide.dsl`, and returns a one-line change summary. The parent
  re-runs the loop, detects plateau (Δ struct_diff_ratio < 0.5%
  across rounds), and stops when all layouts hit the threshold or
  the iteration budget is exhausted. Includes
  `references/per-slide-prompt.md` (the per-layout sub-agent prompt
  template) and `references/workflow.md` (full end-to-end loop,
  dispatch shape, plateau handling, cost notes).

### Changed
- **`scripts/brand_visual_diff.py`** — `struct_diff_ratio` now
  ALWAYS masks picture-slot regions before scoring, even when
  picture coverage exceeds 90%. The prior carve-out (fall back to
  `total_diff_ratio` for picture-heavy layouts) hid meaningful
  chrome diffs in layouts like covers and full-bleed editorials.
  `picture_coverage` is still reported so coverage-bias remains
  visible. Pathological all-picture canvases fall back to
  `total_diff_ratio` to keep the metric defined.

### Why
The brand-iteration loop was already documented end-to-end in
`skills/compile/references/verification-pipeline.md`, but every step
ran as a separate script invocation with hand-stitched paths. For
LLM-driven brand polishing, that's both slow (serial dispatch) and
context-hostile (every layout's evidence shares the same window).
The new orchestrator collapses the wiring into one command; the
new skill turns the loop into a parallel fan-out where each layout
gets its own focused sub-agent.

## Unreleased — image-provider framework

### Added
- **`lib/image_provider.py`** — pluggable image-provider ABC + global
  registry + 5-tier discovery (bundled → plugin → env → cwd-dev →
  user). Mirrors `lib/brand_discovery.py`'s scan idiom; plugin
  providers land under `~/.claude/plugins/.../feinschliff_providers/`
  and survive every upstream resync. Discovery is idempotent;
  first-write-wins on name collisions; broken provider files log a
  truncated traceback and skip rather than blocking unrelated builds.
- **`lib/providers/unsplash.py`** — reference `UnsplashProvider`
  built-in. Uses stdlib `urllib.request` (no new dependency). Stub
  mode is the default when `UNSPLASH_ACCESS_KEY` is unset, with one
  `RuntimeWarning` per process — OSS builds without a key still
  complete. Single retry on 429 / 5xx and network errors, 30 s total
  wall budget.
- **`$image_provider` field on `tokens.json`** (schema-validated,
  `extends:`-inherited). `kind` selects a registered provider; `config`
  is forwarded to its constructor. `config` is deep-merged across
  `extends`; a child swapping `kind` drops the parent's
  provider-scoped `config`.
- **`picture query:"..."` DSL primitive.** Resolves through the
  active brand's provider at build time. Deterministic per-deck
  pinning via `<deck_dir>/asset_lock.json` (atomic writes; brand /
  provider switch invalidates the file). HTTP hits are materialised
  into `<deck_dir>/.cache/<sha1(url)>.<ext>`; `file://` and bare-path
  hits are checked on disk. `query:` and `path:` are mutually
  exclusive on a single picture node.
- **CLI auto-wires providers.** `cli/build.py` and `cli/deck.py`
  (both single-slide and multi-slide build paths) call
  `discover_providers()` + `get_provider()` after brand resolution
  and thread the result onto `EmitContext.image_provider` along with
  `deck_dir`. Brands without `$image_provider` build unchanged —
  the field is opt-in and the existing `path:` flow is untouched.
- **Docs.** New [`references/image-providers.md`](references/image-providers.md)
  covers the ABC, the 5-tier discovery, a worked custom-provider
  example, lock-file format, the built-in `unsplash`, and the
  failure-modes table. `references/brand-pack-spec.md` gains an
  "Image provider" section; `docs/architecture.md` gets the lookup
  step in the pipeline diagram; `docs/port-your-brand.md` points
  brand authors at the new reference.

## Unreleased

### Added — water-cycle showcase + 7 image-slot layouts

- **7 new image-slot layouts** (toolkit-shared, inherited by every brand pack),
  derived as abstracted layout patterns:
  - `photo-grid` — 3×2 photo-card grid + summary headline (Folie 30)
  - `kpi-photo` — 2-3 KPIs left + hero photo right half (Folie 33)
  - `chart-photo` — chart left + hero photo right half (Folie 21/22/23)
  - `full-bleed-editorial` — full-bleed image + corner title overlay (Folie 35)
  - `end-image` — hero photo above closing line (Folie 42)
  - `agenda-photo` — agenda items + hero photo right half (Folie 8)
  - `photo-strip-four` — 4 vertical strips text-top + photo-bottom (Folie 31/32)

  Bumps feinschliff's image-slot-layout count from 3 to 10.
- **Canonical narrative showcase** at `examples/water-cycle/` —
  30-slide SCQA "Hidden Engine" deck on the `nord` brand, English,
  educated-adult register. Exercises 26+ distinct layouts including the 7
  new image layouts; ships with rendered `.pdf`, `.pptx`, 30 per-slide
  thumbnails, README, and ATTRIBUTION (per-slot Unsplash credits).
- Two centerpiece diagrams in the showcase: Excalidraw six-stage cycle
  (slide 7) + bespoke SVG "drawn to scale" reservoir cross-section (slide 5).

### Changed

- `Feinschliff-Template.pdf/.pptx` regenerated to include the 7 new
  layouts (50 layouts now, was 43). TAXONOMY_ORDER updated in
  `scripts/render_brand_preview.py`.

### Removed — v1 resolver cluster + pattern atlas + retired docs
- **v1 asset-resolver chain deleted.** `lib/{fetcher,resolver,search_cache,cache}.py`
  were orphaned in v2 (no caller in `cli/` or `lib/dsl/` — confirmed by grep before
  removal; `tests/conftest.py` had already flagged them "orphan in v2"). Removed
  the four modules plus 12 v1-only tests (`test_fetcher`, `test_fetcher_search`,
  `test_resolver`, `test_resolver_search`, `test_resolve_icon`, `test_search_cache`,
  `test_cache`, `test_e2e_search_source`, `test_integration_iconify`,
  `test_integration_wikimedia`, `test_integration_unsplash`) and the shared
  `tests/_http_fixture.py`. `conftest.py` lost the `sample_v2_catalog` /
  `tmp_cache_root` fixtures along with them.
- **Pattern atlas deleted.** The Airbnb-style exemplar library (`feinschliff/atlas/`,
  ~5.8 MB) plus `lib/atlas.py`, `tests/test_atlas_retrieval.py`, and the four
  atlas-only scripts (`build_atlas_gallery`, `build_atlas_index`,
  `compare_atlas_ratings`, `rate_atlas_with_gemma`) are gone. The picker imported
  `lib.atlas` optionally as a tiny tie-breaking nudge (`+0.5` when a narrative-role
  exemplar matched); that nudge and its `try/except ImportError` shim are removed
  from `lib/layout_picker.py`. The **brand atlas** (`scripts/render_brand_atlas.py`,
  `scripts/build_brand_atlas_overview.py`, `tests/test_render_brand_atlas_cache.py`,
  output in `docs/brand-previews/`) is a separate concept and stays.
- **Retired reference docs removed.** `references/asset-sources-spec.md` (v1
  fetcher/resolver extension contract), `references/renderer-protocol.md` (v1
  pptx-template renderer contract — superseded by the DSL pipeline), and
  `references/claude-design-prompt.md` (older standalone authoring prompt —
  superseded by the per-brand DESIGN.md flow in `docs/brand-system.md`).
- **One-off scripts removed.** `scripts/extract_sewp_slides.py` (one-time SEWP
  PDF extraction) and `scripts/render_goldens.py` (v1 template golden regen —
  golden refs now flow through `scripts/render_v2_goldens.py` / `dsl_golden_compare.py`).
- README + `skills/deck/references/pipeline.md` updated to drop
  atlas/v1 references. (The standalone `docs/migration-dsl-architecture.md`
  rationale doc was dropped in a later pass.)

### Changed — Excalidraw renderer: rough primary, Playwright fallback
- `lib/diagrams/render.py:_render_excalidraw` no longer routes through the partial flat translator. Primary path is **`render_rough`** — pure-Python `rough` (Python port of rough.js) at `roughness=0 + disableMultiStroke=True`, rendered via cairosvg, ~150 ms per diagram, no browser. **Fallback** is **`render_playwright`** — real Excalidraw web app in headless Chromium (~1.5 s + 200 MB), kicks in when rough/cairosvg are unavailable or the document contains elements rough doesn't model (freedraw / image / frame).
- The old `lib/diagrams/excalidraw_to_svg.py` flat translator is **deleted** along with `tests/test_excalidraw_to_svg.py`. End-to-end coverage moved to `tests/test_excalidraw_render.py` (3 new tests exercising the dispatcher).
- **Arrow routing rewritten**: was a 4-point Z that pierced unrelated boxes in dense layouts. Now **edge-to-edge straight line** along the center-to-center ray, matching the upstream Excalidraw plugin's `make_arrow` and excalidraw.com's native export. Author places boxes thoughtfully so straight arrows have a clear path; the router doesn't bend.

### Added — Full Excalidraw DSL vocabulary parity
- New primitives in `excalidraw_expand`:
  - `diamond <id> <x>,<y> <w>x<h> "<label>" [fill:<color>]` — decision shape (rendered as 4-point polygon via rough.polygon).
  - `dot <id> <x>,<y> [fill:<color>]` — 12 px filled marker.
  - `line <id> <x1>,<y1> <x2>,<y2> [dashed] [fill:<color>]` — structural divider with optional dashed stroke.
  - `theme dark` — flips canvas background to `ink` and labels to `paper`.
  - `group <id1> <id2> ...` — assigns shared `groupIds` for Excalidraw selection grouping.
- **Color aliases** mirroring the upstream plugin's semantic vocabulary, all resolving to brand tokens: `start → accent`, `end → success`, `decision → accent`, `ai → tertiary`, `inactive → neutral-soft` (auto dashed stroke), `error → danger`, `code/data → ink` (dark fill).
- **Extended text levels** on the `text` primitive: `title` (28 px), `subtitle` (20), `eyebrow` (12), `body` (14, default), `detail` (11), `mono` (13, fontFamily 3). New optional `color:<token>` kwarg.
- **Rectangle styling**: `roundness: {type: 3}` for rounded corners (matches upstream); `strokeStyle: dashed` automatically applied when fill is `inactive`.
- New tests in `tests/test_diagrams_excalidraw_expand.py` cover every new primitive (diamond, dot, line+dashed, theme dark, inactive→dashed, group). 21/21 passing.
- Skill docs updated: `skills/excalidraw/references/dsl-syntax.md` documents the full vocabulary + render-backend policy. `feinschliff/CLAUDE.md` "Diagram pipeline notes" rewritten.

### Changed — Examples discipline (PDFs/PPTX/PNGs only)
- `examples/` now ships **only** final artifacts: `*.pdf`, `*.pptx`, `*.png` (rendered diagrams + slide thumbnails), `README.md`, and `ATTRIBUTION.md` where licensing requires. Intermediate / debug artifacts (`brief.txt`, `content_plan.yaml`, `design_brief.json`, `wireframe.svg`, `verify_report.md`, `*.exc.dsl`, `*.excalidraw`, `*.svg.dsl`, `*.svg`, build-plan YAMLs) now live under `feinschliff/.debug/examples/<mirror-path>/` and are gitignored. Policy documented in `feinschliff/CLAUDE.md`.
- READMEs across `examples/` shortened to describe what the rendered output shows; reproduction commands moved to `CLAUDE.md` (Examples discipline section).
- `tests/test_examples_decks.py` reads `brief.txt` / `content_plan.yaml` / `design_brief.json` / `verify_report.md` from `.debug/examples/decks/<name>/` instead of `examples/decks/<name>/`. Tests stay green; skip when `.debug/` is empty.

### Fixed — Review-driven pipeline + diagram fixes
- **Diagram artifact cache key collision** (Review #0.1). `expand_diagram_blocks` hashed only `body`, so two slides with the same diagram id and same body but different brand or region size silently shared a PNG (later render overwrote earlier). Cache key now includes `{slide_index, kind, w, h, brand_dir.name, body}`; output filename prefixed with `s{slide_index}-`.
- **Multi-slide deck build skipped diagram validators** (Review #0.2). `feinschliff deck build` now runs `validate_diagrams`, `validate_diagrams_color`, and `validate_diagrams_text_size` per slide — matching the single-slide `build` CLI.
- **Diagram overflow + text-too-small now fatal** (Review #0.3). `feinschliff build` aborts when those defects appear; new `--allow-diagram-warnings` flag opts out.
- **Brace parser ignores braces in quoted strings** (Review #0.4). `_collect_brace_body` was naively counting `{`/`}` per line — a label like `"Cache {warm}"` corrupted block depth. Switched to a state machine that walks character-by-character and skips quoted regions (with `\"` escapes).
- **Brand atlas glob fixed: `*.yaml` → `*.dsl`** (Review #0.5). Shared compounds live in `feinschliff/compounds/*.dsl`; the cache invalidation was checking the wrong extension and missing compound edits.
- **Excalidraw `arrow label:"…"` now implemented** (Review #3, #7). The grammar advertised it; the emitter ignored it. Now parsed and rendered as a centered text element at the polyline midpoint (with `\n` → real newline support).
- **SVG `rect label:"…"` + `circle label:"…"` now implemented** (Review #6, #7). Same story — silently dropped before; now emitted as centered text with luminance-aware fill color.
- **SVG arrow emit switched to `<polyline>` with `marker-end`** (Review #2). The old `<line>` emit collapsed multi-point Z-routes to a single line; corresponding test renamed `test_arrow_emits_line_with_marker` → `test_arrow_emits_polyline_with_marker`.
- **Playwright SVG-render fallback now sets viewport from the SVG dimensions** (Review #7). Previously screenshotted with default browser viewport, producing whitespace / clipping depending on SVG size. Now parses `width`/`height` (or `viewBox`) and calls `set_viewport_size` + clips the screenshot to that box.

### Fixed — second-pass review (review.md 2026-05-15)
- **deck build now fails on fatal diagram defects** (review #1). Previously matched `feinschliff build` on running the validators but not on the policy: deck-build printed `diagram-overflow` / `diagram-text-too-small` defects to stderr and continued. Now collects defects per slide, aborts after the loop with a count + slide list, and accepts `--allow-diagram-warnings` for the override. Same fatal kinds as single-slide `build`.
- **`find_brand()` now drives build / deck build / deck polish brand resolution** (review #6). All three CLIs called `(BRANDS_DIR / args.brand).resolve()` directly, so `feinschliff brand list` could show plugin / env / user-local brands that `build` couldn't actually use. Replaced with `lib.brand_discovery.find_brand()`, which walks the full discovery chain (bundled → plugin → env → cwd-dev → user). `extends:` chain resolution still uses bundled `BRANDS_DIR` (parent brands from external sources is a deeper refactor — out of scope here).
- **Required-asset policy is now strict by default** (review #7). Previously a missing or unset picture path silently emitted a grey placeholder rectangle and the build succeeded; broken image references could ship in production decks. `EmitContext` now accumulates a `missing_assets` list, `build_presentation` / `build_multi_slide` expose it as `prs.missing_assets`, and both `feinschliff build` / `deck build` abort with the missing-path list unless `--allow-missing-assets` is passed. Picture nodes can opt out per-slot with `optional:true` — already wired into the brand-pack `header` / `header-dark` compounds (descendant brands without their own gem.png no longer fail) and into `chapter-ink.slide.dsl`'s right-half image (the layout is explicitly designed to look complete with or without the image).

### Deferred (called out in Review.md, not in this PR)
- Real Excalidraw renderer for `.excalidraw` artifacts (Review #1). The shipped converter is a partial flat-SVG approximation; the older `lib/diagram/pipeline.py` has a higher-fidelity path that is not wired into `expand_diagram_blocks`. Out of scope for this batch — needs an architectural decision.
- Refactor into `compile_slide / render_diagram / emit_deck` shared contract (Review #8). Pipeline logic is still repeated in `build.py`, `deck.py` (build + polish), and the atlas / golden scripts.
- Wire rendered-image quality gate / golden-image smoke tests for `excalidraw-diagram` and `svg-infographic` layouts (Review #5, #8).

### Added — Diagrams integration
- `/excalidraw` and `/svg` skills — brand-aware diagram authoring via compact DSL.
- `excalidraw-diagram.slide.dsl` and `svg-infographic.slide.dsl` whole-slide layouts.
- `excalidraw {…}` and `svg {…}` DSL block primitives, embeddable in any layout (inline body or `from:"path"` external file).
- `lib/diagrams/brand_bridge.py` — semantic color names (17-name vocabulary) → active brand tokens; literal hex / rgb / hsl rejected at parse time; `extends:` chain walking with cycle guard.
- `lib/diagrams/excalidraw_to_svg.py` — Python translator that lets `.excalidraw` files render via cairosvg (no playwright runtime dep).
- `lib/diagrams/refurbish/` — `/deck polish` refurbish path: vector extractor (python-pptx, lossless, EMU→pixel scaled) + raster extractor (Claude vision, mockable). Multi-slide PPTX rebuild via `build_multi_slide`. Slide title heuristic prefers PPTX title placeholder or largest free-floating textbox (never a node label).
- `--refurbish-all`, `--no-refurbish`, `--refurbish-default` flags on `/deck polish`.
- Three deterministic verify defect classes: `diagram-overflow`, `diagram-color-mismatch`, `diagram-text-too-small` — wired into the build pipeline (the only point where DSLNode meta is still live).
- `diagram_kind` signal in `lib.layout_picker.pick_layout()` — values `concept` / `chart` / `None`.
- New layout-picker registry roles: `concept-diagram`, atlas keys `system` and `custom-viz`.

### Changed
- `cairosvg` promoted from `dev` to runtime `dependencies` in `pyproject.toml`.
- `lib/dsl/pptx_emit.py:_emit_picture` accepts both slide-authored (`pos_args`) and diagram-emitted (`kw_args` + `_diagram_meta`) picture node shapes.
- `lib/dsl/svg_wireframe.py` recognizes diagram-emitted picture nodes and renders an internal primitive bbox layer (dashed, kind-coloured) alongside the outer region.
- `scripts/render_v2_goldens.py` runs `expand_diagram_blocks` so goldens for diagram-embedding layouts render correctly.
- Moved `examples/v2/` (41 per-layout content fixtures) to `tests/fixtures/layouts/` — they're renderer/test inputs, not user-facing examples. Three renderer scripts updated.

### Internal renderer note
On macOS, set `DYLD_FALLBACK_LIBRARY_PATH=$(brew --prefix cairo)/lib` once per shell so cairosvg can locate `libcairo` (no-op on Linux).

### Added — Slide generation quality
- **Layout variety enforcement** — `pick_layout()` accepts `layout_history`; recency penalties (−0.5 most-recent, −0.25 second-most-recent) discourage repeating the same layout. Structural layouts (`title-*`, `end`, `agenda`, `chapter-*`) exempt via `_VARIETY_EXEMPT`.
- **New content defect classes**: filler-word detector (≥2 meaningless intensifiers in `so_what`); vague-so-what keyword list extended with 15 LLM clichés; numeric-anchor detection upgraded from `isdigit()` to a regex catching `%`, currency symbols, ratios, and multipliers.
- **Design brief schema additions**: `image_style`, `delivery`, `delivery_mode`, `verbosity` fields; `frame` enum extended (`ppf`, `pse`, `kea`, `abt`).
- **Brand gallery upgrades** — role chips, MIT/demo license badges, Phase 4 badges on every layout card.
- **39-slide showcase deck** (`examples/showcase-39/`) covering all toolkit layouts.

### Changed — Slide generation quality
- **`four-column-cards` role corrected**: `data-timeline` → `content-columns`, `comp: False`.
- **Layout DSL geometry fixes**: kpi-cell `maxwidth` tightened; 2×2-matrix rotated y-axis label corrected; stacked-bar and waterfall label vertical-shift values adjusted.

### Added — Examples revamp
- Four domain mini-decks under `examples/decks/`, each demonstrating one narrative frame and one brand: q1-update-saas (SCQA · feinschliff), ml-research-findings (KEA · claude), budget-non-profit (PSSR · solarized-dark), postmortem-eng (Man-in-a-Hole · gruvbox-dark). Each ships brief.txt, design_brief.json, content_plan.yaml, rendered .pptx + .pdf + thumbnails, verify_report.md (clean across all 14 LLM + 5 deterministic defect classes), and wireframe.svg.
- `/deck polish --refurbish-all` before/after demo at `examples/refurbish/` using a 3-slide extract from the NASA SEWP June 2024 deck (public domain, 17 U.S.C. § 105). Ships before.pptx, after.pptx, refurbish_report.md, emitted DSL artifacts, and a side-by-side composite PNG.
- Three standalone `/excalidraw` fixtures (auth-flow, microservices-arch, user-journey) and three `/svg` fixtures (q1-revenue-breakdown, feature-adoption-funnel, stat-card-grid), each across a different brand. Multi-fixture `preview.pdf` per directory.
- Per-skill READMEs (`examples/excalidraw/README.md`, `examples/svg/README.md`) and a rewritten top-level `examples/README.md`.
- New scripts: `scripts/extract_sewp_slides.py`, `scripts/render_side_by_side.py`, `scripts/render_examples_pdfs.py`.
- New test files: `tests/test_examples_decks.py`, `tests/test_examples_refurbish.py`, `tests/test_examples_diagrams.py`.

### Fixed
- `cli/deck.py:cmd_build` now calls `expand_diagram_blocks` before `expand_compounds`, so slide-embedded `excalidraw {…}` / `svg {…}` block primitives expand correctly in the standard build pipeline (previously only `cmd_polish` had this wiring).
- `lib/diagrams/refurbish/extract_vector.py` silently drops edges whose endpoint shape-IDs can't be resolved (python-pptx connectors don't always expose `begin_connection_shape_id` / `end_connection_shape_id`).
- All 12 brand-preview atlases re-rendered. The dark-brand text-contrast fix from PR #19 had left stale renders cached with invisible titles, funnel trapezoids, and labels. Orphan pre-PR19 numbered PNGs removed.
- `scripts/render_brand_atlas.py:_cache_inputs_mtime` now walks the brand's `extends:` chain so a parent brand's `tokens.json` (merged at render time) also invalidates descendant PNGs. Previously only the direct brand's `tokens.json` was tracked — changes to a parent silently left descendants stale. Regression test: `tests/test_render_brand_atlas_cache.py`.

### Added — Diagram module CLIs
- `python -m lib.diagrams.excalidraw_expand <input.exc.dsl> [--brand X] [-o OUT]` — expand Excalidraw DSL to `.excalidraw` JSON (writes alongside input by default).
- `python -m lib.diagrams.svg_expand <input.svg.dsl> [--brand X] [-o OUT]` — expand SVG DSL to `.svg`.
- `python -m lib.diagrams.render <input.svg|.excalidraw> [-o OUT]` — render to PNG.
- Both expanders honor the documented precedence: inline `@brand <name>` directive at top of DSL > `--brand` CLI flag > `FEINSCHLIFF_BRAND` env > `'feinschliff'` default. Matches the CLI pattern referenced from `skills/svg/SKILL.md` and the better-examples plan.

### Changed — Examples directory cleanup
- `examples/excalidraw/README.md` + `examples/svg/README.md` now show the proper `python -m lib.diagrams.X` quick-start (replacing inline-Python shims that pre-dated the `__main__` blocks).
- `examples/README.md` verify-claim corrected from "clean across all 14 LLM + 5 deterministic defect classes" → "`feinschliff verify` clean — layout-validator + chrome checks pass" (matches what the shipped CLI actually emits).
- `examples/feinschliff/README.md` references migrated from `examples/v2/<id>.yaml` to `tests/fixtures/layouts/<id>.yaml` (path moved earlier this branch); layout count updated 39 → 41 (excalidraw-diagram + svg-infographic now listed); per-category counts added.
- All three legacy per-brand template PDFs re-rendered against the current 41-layout catalog with the post-PR-19 contrast tokens: `Feinschliff-Template.pdf`, `Catppuccin-Latte-Template.pdf`, `Solarized-Dark-Template.pdf`.
- `examples/feinschliff/` now ships a 39-slide curated showcase deck (`out/feinschliff-showcase.pptx` + `.pdf`) built from the existing `feinschliff-showcase.yaml`, demonstrating how the layouts string together into a coherent business review.
- `examples/catppuccin-latte/` + `examples/solarized-dark/` README layout count updated 34 → 41.

### Removed — Examples directory cleanup
- `examples/teaser.mp4` (16 MB) — orphaned, no README referenced it.
- `examples/design-md-to-tokens/` — self-declared v1 LEGACY stub with no shipped artifacts; the historical context is preserved in earlier CHANGELOG entries.

### Fixed — Excalidraw diagram quality
- **Arrow routing.** `lib/diagrams/excalidraw_expand.py:_emit_arrow` was hard-coded to exit the source's RIGHT edge and enter the destination's LEFT edge, so any non-horizontal link rendered as a diagonal slashing through unrelated boxes (visible in the auth-flow / microservices-arch / postmortem fixtures). Now:
  - Same row → straight horizontal between facing edges.
  - Same column → straight vertical between facing edges.
  - Diagonal → 4-point Z bending in the row-gap between source and destination rows (avoids piercing either row).
- **SVG arrow emit.** `lib/diagrams/excalidraw_to_svg.py:_emit_arrow` collapsed any multi-point arrow to a single `<line>` between endpoints. Switched to `<polyline>` with `stroke-linejoin="round"` so the Z-route renders as drawn.
- **Multi-line box labels.** `\n` inside a quoted box label shipped through as the literal two-character escape sequence (visible as "Circuit breaker\\n(DISABLED)" on postmortem slide 3). `_emit_box` + `_emit_text` now normalize `\n` to a real newline; the SVG translator emits `<tspan>` per line with proper vertical centering.
- **Label contrast on dark fills.** Box labels always inherited `ink` color, leaving the text invisible on dark fills (Audit Log on auth-flow). Added a luminance check so dark fills flip the label to `paper`.

### Added — Feinschliff architecture showcase deck
- `examples/decks/feinschliff-architecture/` — 8-slide SCQA deck for new contributors. Three slides (3, 4, 5) embed Excalidraw concept diagrams: the /deck pipeline, the brand-pack contract (DESIGN.md + tokens.json + extends chain → resolver → 41 layouts × 12 brands), and the verify + polish iteration loop. Ships brief.txt, design_brief.json, content_plan.yaml, out/{deck.pptx, deck.pdf, thumbnails/, verify_report.md}, wireframe.svg, README.md.
- Existing 3 standalone excalidraw fixtures (auth-flow, microservices-arch, user-journey) regenerated with the routing fixes — their preview.pdf reflects the new quality bar.
- `examples/decks/postmortem-eng/` deck rebuilt so slide 3's embedded diagram benefits from the same routing + label fixes.

## 0.3.0 (v2 GA)

### Architecture
- **New DSL pipeline.** Slides are authored as `.slide.dsl` files (line-oriented,
  primitives + compound calls + slot interpolation). The v2 emitter walks the
  primitives to produce a `.pptx`. See [`docs/dsl-grammar.md`](docs/dsl-grammar.md).
- **Shared toolkit layouts.** 33 canonical layouts live at `feinschliff/layouts/`
  and are inherited by every brand. Brands ship `tokens.json` + `DESIGN.md` and
  optionally override layouts or add compounds.
- **Brand-pack contract refresh.** `catalog.json` retired; `tokens.json` (DTCG
  format) is the source of truth. `DESIGN.md` frontmatter carries `extends:` for
  token inheritance. See [`references/brand-pack-spec.md`](references/brand-pack-spec.md).
- **Multi-slide composer.** `feinschliff deck build <plan.yaml>` emits one
  multi-slide `.pptx`, mixing layouts and brands per slide.
- **Structured layout picker.** `feinschliff deck pick <signals.yaml>` ranks
  layouts by (role, concept_count, data_quantity, comparison, narrative_role).
- **Skeleton generator.** `feinschliff compile-html <html>` walks
  `<section data-slots>` entries and emits one `.slide.dsl` skeleton per slide.

### Engine
- Added DSL primitives: `text`, `rect`, `line`, `picture`, `shape` (oval,
  triangle, chevron, diamond, trapezoid, arrows), `chip`.
- `color:TOKEN` override on `text`; `fill-opacity` on `shape`.
- Multi-op arithmetic in `{{ … }}` placeholders (e.g. `{{ y+h-1 }}`).
- `\n`, `\t` escape sequences inside quoted strings.
- `if:VALUE` kw-arg suppresses node emission when the value is empty/false.
- Unbound compound parameters default to empty string (no more `{{ name }}` leaks).
- Per-paragraph `line_spacing` from style bundles; inter-paragraph gap zeroed.
- Font-weight resolution maps the weight number to the Noto Sans face name
  (`Noto Sans Light`, `Medium`, `SemiBold`, …) so soffice picks the right weight.

### Brand packs
- **17 brands ship.** binance, bmw, catppuccin-{frappe,latte,macchiato,mocha},
  claude, dracula, feinschliff, feinschliff-{dark,light}, ferrari, gruvbox-dark,
  gs-ramspau, nord, solarized-dark, spotify.
- **gs-ramspau** in-place port: 6 bespoke school-flavoured layouts
  (stundenplan, termine, team, leitbild, statistik, checkliste) authored in
  v2 DSL; the 906-line `build_templates.py` retired.

### Removed
- `lib/pptx_fill.py` (v1 placeholder-fill engine).
- `lib/catalog.py` + catalog/asset JSON schemas.
- `scripts/extract_v2_template.py`, `port_brand.py`, `verify_v2_template.py`,
  `visual_verify_asset_slot.py`, `audit_atlas_layouts.py`.
- ~570 frozen `templates/pptx/*.pptx` files across all brand packs (replaced
  by 34 golden PNGs at `tests/golden/feinschliff/`).
- 17 `brands/*/catalog.json` files.
- `cli/brand` sub-commands: `sync`, `bundle`, `install` (v1-specific).

### Skills
- `/deck` rewritten to drive `feinschliff deck pick` / `build` / `verify`.
- `/compile` rewritten to drive `feinschliff compile-html` + golden-compare.

### Tests
- `tests/golden/feinschliff/` — 34 PNG fidelity references rendered from the
  pre-deletion `.pptx` baselines.
- Removed 9 v1-only test files (test_pptx_fill, test_fill_layout, test_catalog,
  test_brand_drift, test_feinschliff_brand_pack, test_cli_brand, test_schemas,
  test_integration_v2, test_pptx_layouts_v2). 116 tests pass.

### Known limitations
- Negative letter-spacing not always applied by soffice — heavy-weight font
  fallback can still distort big-display layouts.
- v2 has no triangle/ellipse for very-fine pyramids/venn diagrams; uses
  trapezoid + oval-with-alpha approximations.
- WCAG-contrast suite flags one gs-ramspau token combination as below AA on
  paper (pre-existing token-tuning task).

## Pre-v0.3 history

Earlier v1 (catalog-based) releases and the v1 → v2 migration plan
were tracked in a `docs/migration-dsl-architecture.md` rationale doc
that was retired together with the v1 code. The pre-v0.3 entries above
remain as a short audit trail.
