# feinschmiede architecture — engine extraction + plugin family

**Date:** 2026-06-09
**Status:** approved design (supersedes one decision in the Obsidian spec/plan
`2026-06-09-feinschmiede-plugin-split-{spec,plan}`)
**Branch:** `worktree-cli-loose-coupling`

## Context

The Obsidian spec/plan split the `feinschliff` monolith into a `feinschmiede`
marketplace of CLI-coupled plugins, keeping the engine's Python import name as
`feinschliff` to avoid a rename. **This design overrides that one decision:**
`feinschmiede` becomes the name of the *shared engine package itself* — the
umbrella term for **common things only**. Each media product is an independent
plugin (`feinschliff` office, `feinbild` image, `feinschnitt` video,
`feinklang` audio). Phase 0 (`feinklang`, audio) is already built, committed,
and gate-verified; it is unaffected by this naming change.

## Goals / non-goals

**Goals**
- One **shared engine package, `feinschmiede`**, holding only what 2+ plugins
  need — chiefly the cross-media *brand/look* system and the diagram engine.
- Every plugin **installs and runs independently**, auto-loading its `bin/` CLI
  into a self-contained venv; the engine rides along as a vendored wheel.
- **No engine-source drift:** the engine has exactly one source of truth.
- Cross-plugin links are **CLI capability calls** (guaranteed by plugin
  `dependencies`), never file-path coupling.

**Non-goals (this design)**
- Converting the `feinschliff` *office* plugin to the launcher/bundled-wheel
  model (it keeps running as today, just importing `feinschmiede`) — that is a
  later phase.
- PyPI publication (deferred; bundled wheels now).
- Physically renaming the git repository directory (cosmetic; later).

## Naming hierarchy

| Name | Kind | Role |
|---|---|---|
| **feinschmiede** | umbrella | git repo + marketplace name (rename later, optical) **and** the shared engine Python package |
| **feinschliff** | plugin | office / decks (Word, Excel, PPTX) |
| **feinbild** | plugin | image / 2D (imagine, svg, excalidraw) |
| **feinschnitt** | plugin | video (Remotion + recorder) |
| **feinklang** | plugin | audio (TTS) — ✅ built (Phase 0) |
| **feinschliff-builder** | plugin | brand-pack authoring/verify tooling |
| **feinschliff-extra** | plugin | brand-pack data (10 packs) |

## The engine package: `feinschmiede` (what is "common")

The contents are the **empirically-computed import closure** of the diagram/
SVG/Excalidraw entry points — exactly what `feinbild` (image) and `feinschliff`
(office) both need, and the cross-media brand system that also styles video:

```
feinschmiede/                        ≈4.7k LOC — cross-media "look" + diagram core
  brand/            (BrandPack)              ← a brand (e.g. BSH) styles decks, diagrams AND video
  brand_discovery                            cross-plugin brand-pack discovery
  dsl/ast  dsl/tokens                        DSL data model + token/brand resolution
  diagnostics  jsonwalk                      shared diagnostics + JSON utilities
  diagrams/         svg_expand · excalidraw_expand · render · render_rough
                    · render_playwright (lazy) · brand_bridge · text_metrics · _dsl_common
                    (+ renderer, diagram_wireframe)
```

**Brands are the strongest "common" justification:** a brand is a cross-media
look — the same BSH brand must style a deck, a diagram, and a video
consistently — so the brand/token/discovery system belongs in the shared
engine, not in any one plugin.

**Stays office-specific in `feinschliff`** (not common): `deck/`, `book/`,
`dsl/{parser,expander,pptx_emit,polish}`, `cli/`, `io/`, `layout_*`,
`pipeline*`, `content_validator`, `textfit`, `slot_budget`, etc.

**Engine dependencies** are a strict subset of today's `feinschliff` deps —
the diagram/brand runtime set (`cairosvg`, `rough`, `pillow`, `pyyaml`,
`jsonschema`, …) — and explicitly **exclude `python-pptx` and `lxml`** (office
only). `render_playwright` keeps its `playwright` import lazy so the engine
never requires a browser.

## Coupling & distribution

- **Engine = bundled wheel.** `feinschmiede` is a pure library (no skills, no
  CLI), so it is not itself a plugin. It is built once and **vendored as a
  `.whl` into each plugin that needs it** (`feinbild`, later `feinschliff`,
  and `feinschnitt` for brand styling), installed offline into that plugin's
  own venv by its `bin/` launcher. One source → no drift; each plugin stays
  independent. → PyPI later (Phase 3) replaces vendoring.
- **Cross-plugin capability = CLI call.** When one plugin needs another's
  capability (e.g. `feinschnitt` → `feinbild imagine …` / `feinklang tts …`),
  it declares the other in plugin `dependencies` (auto-install + PATH) and
  calls the bare command. This is the Phase-0-proven model.
- **Brand packs = discovered data**, unchanged: `feinschmiede.brand_discovery`
  scans every installed plugin's `brands/` dir plus the env/home overrides and
  bundled packs — co-installed packs auto-unify across plugin boundaries. The
  override names (`FEINSCHLIFF_BRAND_PATH`, `~/.feinschliff/brands`) are
  **kept as-is for backward compatibility** with existing brand setups (e.g.
  the BSH packs); a `feinschmiede`-prefixed alias is a deferred, additive
  follow-up, not part of this work.

## Repository layout (transition state)

Plugins live at the **repo root**; `feinschmiede/` is the **engine package
folder** (a uv workspace member). The git repo directory keeps its current name
for now (rename is optical/later).

```
<repo root>                           uv workspace
  pyproject.toml                      [tool.uv.workspace] members += feinschmiede, feinbild, feinklang
  .claude-plugin/marketplace.json     single umbrella marketplace → lists all root plugins
  feinschmiede/                       ENGINE (workspace member; builds the feinschmiede wheel)
    pyproject.toml
    feinschmiede/                     the importable package (diagrams/, brand/, dsl/{ast,tokens}, …)
    tests/                            engine tests (moved from feinschliff/tests where they test engine modules)
  feinklang/                          audio plugin (moved up from feinschmiede/feinklang/)
  feinklang-consumer/                 cross-plugin smoke test (moved up)
  feinbild/                           image plugin (new, this phase): bin/ · wheels/ · src/feinbild/ · skills/ · commands/ · .claude-plugin/
  feinschliff/                        office plugin + workspace member; imports feinschmiede
  feinschliff-builder/  feinschliff-extra/
```

`feinschmiede` (engine) is a workspace member + wheel source, **not** a
marketplace plugin. The single root marketplace is renamed to `feinschmiede`
(umbrella); existing `@feinschliff` members are re-listed there.

## Work breakdown

### Phase 1a — engine extraction (do first; atomic)
1. Create the `feinschmiede` workspace member; **move** the closure modules out
   of `feinschliff/feinschliff/` into `feinschmiede/feinschmiede/` (git mv);
   rewrite the engine's **internal** imports `feinschliff.X → feinschmiede.X`.
   Split `dsl/`: only `ast` + `tokens` move; `parser`/`expander`/`pptx_emit`/
   `polish` stay in office (watch for circular imports).
2. Rewrite the **~193 office import sites across 57 files + test references**
   `from feinschliff.{engine} → from feinschmiede.{engine}`.
3. `feinschliff/pyproject.toml` gains a `feinschmiede` workspace dependency;
   move engine-only tests into `feinschmiede/tests/`.
4. **Gate:** the full existing test suite is green; the required CI check
   **`feinschliff lib tests` keeps its exact name** (add an engine test job in
   lockstep, do not rename the gating check).

### Phase 1b — `feinbild` plugin
1. Scaffold `feinbild/` (root level), same anatomy as `feinklang`: `bin/feinbild`
   launcher (the Phase-0 sentinel/atomic template), bundled wheels (`feinbild`
   + `feinschmiede` engine + `cairosvg`/`rough`/`pillow`/…), `build-wheels.sh`.
2. CLI: `feinbild imagine '{…}'` (port `imagine.sh` → Python/`requests`),
   `feinbild svg expand|render`, `feinbild excalidraw expand|render` — shelling
   into `feinschmiede.diagrams.*`. **This replaces the broken `lib.diagrams`
   invocation** (`feinschliff/skills/svg/SKILL.md` still runs
   `python -m lib.diagrams.svg_expand`).
3. Clean `skills/{imagine,svg,excalidraw}/SKILL.md` + `commands/` documenting
   the CLI — **no `${CLAUDE_PLUGIN_ROOT}/skills/<other>/…` paths, no `cd`**.
4. Add `feinbild` to the umbrella marketplace.
5. **Gate (fresh plugin install):** `feinbild svg expand chart.svg.dsl &&
   feinbild svg render chart.svg` → PNG with brand tokens resolved;
   `feinbild excalidraw …` likewise; `feinbild imagine '{…}'` calls the
   provider or returns a clean key-missing error; **no `lib.diagrams` strings
   remain; no `cd /path/to/feinschliff` needed.**

### Also in this phase
- Restructure the committed Phase-0 layout: `git mv feinschmiede/feinklang →
  feinklang`, `feinschmiede/feinklang-consumer → feinklang-consumer`; fold the
  Phase-0 `feinschmiede/` marketplace + `.gitignore` + README into the root
  umbrella marketplace and the root `.gitignore`. Update feinklang's marketplace
  source path; rebuild its wheelhouse (gitignored).

## Risks & mitigations

- **Extraction touches 57 office files.** Mitigation: mostly-mechanical import
  rewrites; the full `feinschliff` test suite is the safety net and must stay
  green before `feinbild` work starts.
- **`dsl` split** (`ast`/`tokens` move, `parser`/`expander` stay) risks circular
  imports. Mitigation: verify import direction is engine→nothing-office;
  office→engine only.
- **Engine wheel in feinbild's venv** — the original Phase-1 risk; the Phase-0
  mechanism (offline bundled-wheel bootstrap) already proves it works.
- **Marketplace rename** (`feinschliff` → `feinschmiede`) may break existing
  `@feinschliff` install references; acceptable in this solo dev marketplace.

## Success criteria

- `feinschmiede` wheel builds and imports `feinschmiede.diagrams.*` /
  `feinschmiede.brand_discovery` with no `feinschliff` import.
- `feinschliff` (office) test suite green importing `feinschmiede`; CI check
  name unchanged.
- `feinbild` installs independently and renders svg/excalidraw → PNG with brand
  resolution from a fresh plugin install; `imagine` works/clean-errors.
- `feinklang` (root level) still passes its Phase-0 gate.
- No `lib.diagrams` references remain in the diagram path; no engine-source
  duplication anywhere.
