# /deck Modes

Three user-facing modes. All share the same pipeline described in `pipeline.md`; they differ in which steps run.

## create (default)

```
/deck "content brief"
```

Runs the full pipeline (steps 0–5). New deck from scratch. **Verify (step 4) always runs at least once** — no matter how obviously-correct the first build looks. The universal completion gate is `out/verify_report.md` with `Verdict: clean`; see `pipeline.md` step 4. When the `feinschliff-builder` plugin is installed, office delegates advanced subcommands (storyline, wireframe, polish, autofix) to the `feinschliff-builder` CLI.

**Outputs (all required):** `deck_brief.yaml` · `commitment.yaml` · `content_plan.json` · `ghost_deck_report.md` · `title_lint_report.md` · `picker_report.json` · `plan.yaml` · `craft_report.md` · `verify_report.md`. Every artifact on this list MUST exist on disk before the skill reports completion.

## plan

```
/deck plan "content brief"
/deck plan polish rough.pptx
```

Runs **steps 0 → 0a → 1 → 1b → 1c only** (intake, ingest, design-brief inference, 1b approval gate, step 1c Storyline gate). Stops after step 1c. Does NOT proceed to step 2 plan / step 3 build / step 4 verify.

**Outputs (all required for this mode):**

- `deck_brief.yaml` (committed at Step 0a)
- `commitment.yaml`
- `content_plan.json`
- `ghost_deck_report.md` · `title_lint_report.md`
- `design_brief.json`
- `out/storyline_report.md`

No `.pptx`, no `deck_plan.json`, no `out/verify_report.md`.

**Use case.** Fast iteration on the narrative arc *before* committing render budget. Especially useful when the user wants to validate the storyline with stakeholders before slide design — the title-only paper draft is the cheapest checkpoint in the pipeline.

The CLI helper that materializes the storyline report from a saved `content_plan.json` / `deck_plan.json` is `feinschliff deck plan <plan.json> -o out/storyline_report.md` (a thin alias for `feinschliff deck storyline …`, same output byte-for-byte).

## polish

```
/deck polish rough.pptx
/deck polish rough.pptx --mode cosmetic
/deck polish rough.pptx --mode redesign
```

Ingests an existing `.pptx` and applies brand-correct output. The command has two modes that differ in how much of the source deck is preserved. Verify is mandatory in both — reflowing into brand layouts doesn't guarantee slot fit. Intake (Step 0a) runs in both modes; `deck_brief.yaml` fields are seeded from the extracted source content.

### Mode picker (`--mode` or AskUserQuestion)

When no `--mode` flag is supplied, the skill extracts content (Step 1) and then pauses for a single AskUserQuestion before any planning:

```
Header: Polish mode

Options:
  cosmetic   (Recommended) — keeps slides, order, and content; fixes brand
             chrome, typography, and slot overflow only.
  redesign   — keeps raw content; rebuilds slide count, layouts, titles, and arc.
```

Default recommendation is `cosmetic`. Power users can skip the question by passing `--mode cosmetic` or `--mode redesign` at invocation.

### cosmetic mode

Preserves:
- Slide count and order (no inserts, merges, or splits)
- Per-slide content verbatim — titles, bullets, data, claims
- Slide-to-layout mapping via brand-map (source layout → brand analog by role + slot count)
- User-authored images (re-cropped / re-positioned only)

Fixes:
- Typography, colors, brand chrome (header/footer, cover/closer)
- Slot overflow — visual shrink only (font-size/line-height/slot expansion); text values are never rewritten
- Native chrome substitution (per-brand cover / closer / chapter layouts)

Does NOT touch:
- Storyline or arc (no SCR gate, no claim-evidence check, no ghost-deck check)
- Slide count or order
- Per-slide claims or evidence
- Layout picker scoring beyond brand-map-driven role substitution

### redesign mode

Preserves:
- Raw content (claims, evidence, numbers, quotes) captured verbatim from the source `.pptx`
- User-authored images (offered for re-use; planner may drop or re-place them)

Reworks:
- Slide count (may collapse, expand, or reorder)
- Per-slide layout (full picker run)
- Titles (claim titles, not topic labels)
- Arc and storyline (full pipeline: storyline gate, claim-evidence check)

This is the original polish behavior, now made explicit via `--mode redesign`. Add `--refurbish-all` to also extract embedded diagrams, rebuild them as brand-aware DSL (`.exc.dsl`/`.svg.dsl`), and substitute back into the rebuilt deck.

### Pipeline-skip matrix

| Step | Cosmetic | Redesign |
|---|---|---|
| 0. Pre-flight (image style if ambiguous) | Yes | Yes |
| 0a. Intake — `deck_brief.yaml` | Skip by default (no goal/audience change) | Yes (full intake) |
| 1. Content extraction | Yes — verbatim | Yes — verbatim |
| 1b. Design-brief inference | Skip | Yes |
| 1c. Storyline gate | Skip | Yes |
| 1d. Approval gate | Yes — "I will preserve N slides; brand-fit only" | Yes — full plan summary |
| 2. Layout pick | Brand-map only (source layout → brand analog) | Full picker run |
| 2b. Claim-evidence check | Skip | Yes |
| 3. Compile | Yes | Yes |
| 4. Static verify (slot overflow, autofix) | Yes — visual shrink only, no content edit | Yes |
| 5. PPTX emit | Yes | Yes |
| 6. Post-render rubric | Brand-fit subset only (chrome, typography, slot, color) | Full rubric |
| Iteration budget | Up to 8 (scorer terminates) | Up to 8 (scorer terminates) |

### Edge cases

- **Missing brand layout (cosmetic)**: if the source has a layout with no brand analog (no role match), fall back to the brand's nearest `content-columns` layout and log a warning. Never silently substitute a redesign for a slide.
- **Slot overflow that can't be fixed visually (cosmetic)**: prompt the user inline ("Slide 7's title is 87 chars; brand cap is 60. Shorten or accept overflow?"). Do not silently rewrite content.
- **User-authored images (redesign)**: extracted images are listed in `image_inventory.json`; the planner is told which exist and may use them but is not required to.

## critique

```
/deck critique existing.pptx
```

Read-only defect analysis. Runs steps 1 → 1b → 4 only. No build, no revise. Intake (Step 0a) still runs; `deck_brief.yaml` fields are seeded from the extracted source content so the rubric has goal and audience context when flagging off-tone slides.

### Procedure

1. **Ingest** (step 1) — open the existing `.pptx` with python-pptx, extract content per slide into `content_plan.json`.
2. **Derive brief** (step 1 continued) — infer `design_brief.json` from the extracted content. The `frame` inference looks at slide-role ordering in the existing deck; the `audience` inference looks at jargon density and bullet structure.
3. **Present brief** (step 1b) — print the derived brief + slide list in the usual summary format. The user can edit (same edit-handling as create/polish modes) if the inferred audience or frame is off; this is useful because a critique against the wrong audience produces spurious `audience-mismatch` flags.
4. **Verify** (step 4) — render the existing `.pptx` to PNGs; LLM-eyeball for all 14 defect classes.
5. **Emit outputs** — next to the source `.pptx`:
   - `<name>-critique.md` — defects grouped by slide with suggested fixes, plus a summary count at the top.
   - `design_brief.json` — the brief Claude derived.

### `<name>-critique.md` format

```markdown
# Critique: <name>.pptx

Derived audience: **exec** — _time-poor, outcomes-driven_.
Derived frame: **SCQA** — _pitch-style answer-first deck (runner-up: PSSR)_.

**Summary:** 7 defects across 4 / 12 slides.

---

## Slide 3 — "Our Approach"

- **claim-title**: title "Our Approach" is a topic noun.
  **Fix:** Rewrite as a claim, e.g. "We ship daily because we test first".
- **bullet-dump**: 6 peer-level bullets, no hierarchy.
  **Fix:** Group under 2 sub-headings; drop weakest two bullets.

## Slide 7 — "Q1 Results"

- **red-line-break**: slide's role is `context` but sits after `recommendation` (slide 5 was the rec).
  **Fix:** Move to earlier in the deck, or re-role as `evidence`.

---
```

### Title flip-through (Phase 6)

After the existing critique pass, emit a one-page **title flip-through**
to `out/title_flipthrough.md`. This is the consulting "read the titles
in order, ignore the bodies" check — narrative breaks jump out when
slide bodies are stripped away.

1. List every slide's title in slide-order, numbered.
2. Beside each title, flag narrative breaks:
   - `▲ break` — title doesn't follow logically from the prior.
   - `= repetition` — title restates the prior without advancing.
   - `✗ pivot` — title pivots without a complication marker.
   - _(blank)_ — title follows cleanly.
3. Below the list, a one-paragraph **verdict**: `clean` /
   `breaks-but-recoverable` / `structurally broken`.

Use `feinschmiede.verify.deck.titles.extract_titles_from_pptx` to fetch titles
from the built `.pptx`. The flag emission is LLM judgment per-title —
no deterministic helper is appropriate here (the same title can be a
break or a clean follow depending on the prior title's claim).

Format:

```markdown
# Title flip-through — <name>.pptx

1. Five years ago this took a week.
2. = repetition  Five years ago, decks took a week.
3. ▲ break       Q1 revenue: +5.1%.
4.               Q1 revenue tells us the new pricing held.
...

**Verdict:** breaks-but-recoverable — slide 2 restates slide 1; slide 3
pivots without a complication marker. Suggest merging 1+2 and adding a
"so what" beat between 2 and 3.
```

### Thumbnails grid (Phase 6)

Alongside the title flip-through, emit a thumbnails-grid PDF to
`out/thumbnails_grid.pdf`. The verify step renders each slide as a PNG
(these already exist on disk from step 4). Compose them into a
4-column grid PDF via:

```python
from feinschmiede.verify.deck.thumbnails_grid import render_thumbnails_grid_pdf

render_thumbnails_grid_pdf(png_paths, Path("out/thumbnails_grid.pdf"))
```

Default grid is 4 cols × 4 rows = 16 thumbs per page on US-Letter
landscape; thumbs preserve aspect ratio and are centered in each cell.
The grid PDF lets humans + LLMs see the whole deck on one page — the
consulting "print and lay on the table" tactic. Structural problems
(missing acts, late hook, body-heavy middle) are obvious at this zoom
in a way they aren't in one-up scrolling.

**Outputs include:** `deck_brief.yaml` · `design_brief.json` · `<name>-critique.md` · `out/title_flipthrough.md` · `out/thumbnails_grid.pdf`.

### No iteration loop

Critique mode is a single pass. No revise loop, no budget cap. If the user wants fixes applied, they should run `/deck polish existing.pptx` afterwards — polish mode is the write path.

## Step 1b approval-gate format

Regardless of mode, step 1b prints a compact brief + plan and asks once. Example:

```
📋 Design brief

  Audience:   exec — time-poor, outcomes-driven
  Takeaway:   "Polish time collapsed from 3 hrs to 15 min per deck"
  Frame:      Duarte Sparkline — alternating What Is / What Could Be
              (runner-up: PSSR, less fit without a discrete 'search' phase)
  Hook:       contrast — "Five years ago this took a week…"
  Red line:   Pain → Solution demo → Results → What this unlocks

🎞  Plan (8 slides)
   1. title-orange      HOOK         "Five years ago…"
   2. kpi-grid          COMPLICATION "3 hrs × 40 decks/week = 120 hrs lost"
   …

Approve? (press enter) · Edit: say what to change · Redo from scratch: type 'redo'
```

Empty input = approve. Free-form edit triggers a targeted revision. `redo` re-infers from scratch.

## What feinschliff-builder is for (NOT runtime gates)

`feinschliff-builder` is an optional authoring plugin. Its absence never justifies skipping or downgrading a pipeline step. The following commands require the builder:

- `feinschliff-builder wireframe` — visual wireframe generation
- `feinschliff-builder polish --mode redesign` — brand-map redesign mode
- `feinschliff-builder book` — multi-deck book output
- `feinschliff-builder verify-static` — pre-render static geometry check (builder CLI surface)
- `feinschliff-builder apply-fixes` — mechanical defect patching

The following commands ship in feinschliff core and are always available:

- `feinschliff deck title-lint`
- `feinschliff deck ghost-deck`
- `feinschliff deck claim-evidence`
- `feinschliff deck commitment-validate`
- `feinschliff deck storyline`
- `feinschliff deck verify-aspect` (all aspects: bbox, font, narrative, brand, image, content)
- `feinschliff deck pick-deck`

If a gate fails, surface the actual stderr. Never tell the user "I skipped these because the builder is missing" — that explanation is always wrong for the core-shipped commands above.

## `--no-storyline` skip flag

`/deck` accepts a `--no-storyline` flag (or the inline phrase "skip
storyline" at step 1b approval). When set, the orchestrating LLM skips
step 1c (Storyline phase) and proceeds directly from step 1b approval
to step 2 plan.

**When to skip.** Quick decks where the narrative arc is trivially
correct (e.g. a 2-slide announcement, a single chapter recap).

**Cost of skipping.** The deck-level `title-story-spine` defect class
at step 4 still catches narrative breaks, but only after one full
build/verify iteration is spent. The storyline gate is the cheap
catch; this defect class is the expensive backstop.
