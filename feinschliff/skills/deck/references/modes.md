# /deck Modes

Three user-facing modes. All share the same pipeline described in `pipeline.md`; they differ in which steps run.

## create (default)

```
/deck "content brief"
```

Runs the full pipeline (steps 0–5). New deck from scratch. **Verify (step 4) always runs at least once** — no matter how obviously-correct the first build looks. The universal completion gate is `out/verify_report.md` with `Verdict: clean`; see `pipeline.md` step 4. When the `feinschliff-builder` plugin is installed, office delegates advanced subcommands (storyline, wireframe, polish, autofix) to the `feinschliff-builder` CLI.

## plan

```
/deck plan "content brief"
/deck plan polish rough.pptx
```

Runs **steps 0 → 1 → 1b → 1c only** (ingest, design-brief inference, 1b approval gate, step 1c Storyline gate). Stops after step 1c. Does NOT proceed to step 2 plan / step 3 build / step 4 verify.

**Outputs (only):**

- `content_plan.json`
- `design_brief.json`
- `out/storyline_report.md`

No `.pptx`, no `deck_plan.json`, no `out/verify_report.md`.

**Use case.** Fast iteration on the narrative arc *before* committing render budget. Especially useful when the user wants to validate the storyline with stakeholders before slide design — the title-only paper draft is the cheapest checkpoint in the pipeline.

The CLI helper that materializes the storyline report from a saved `content_plan.json` / `deck_plan.json` is `feinschliff deck plan <plan.json> -o out/storyline_report.md` (a thin alias for `feinschliff deck storyline …`, same output byte-for-byte).

## polish

```
/deck polish rough.pptx
/deck polish rough.pptx "make it 5 slides, executive-focused"
```

Ingests an existing `.pptx`, reflows into brand layouts. Same steps as create; step 1 starts from existing content instead of a brief. **Verify is mandatory here too** — reflowing into brand layouts doesn't guarantee the result fits the slots.

## critique

```
/deck critique existing.pptx
```

Read-only defect analysis. Runs steps 1 → 1b → 4 only. No build, no revise.

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
