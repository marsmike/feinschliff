# /deck Pipeline

The 7-step recipe that `/deck` follows for all modes. Read this before the skill body for the full detail; the skill body is a thin index over this file.

## Pipeline timing log

Every step of the pipeline emits a row to `<deck-dir>/timing.jsonl` so
you can run `uv run feinschliff deck timing <deck-dir>` after a deck
completes and see where wall-clock time went. The Python CLI
auto-instruments `feinschliff deck build` (per-slide + total). The
orchestrator (you) is expected to bookend each step manually:

```
# before Step N:
uv run feinschliff deck log-event step:1-ingest start --dir .debug/<deck>/

# after Step N:
uv run feinschliff deck log-event step:1-ingest end --dir .debug/<deck>/ --elapsed-ms <ms>
```

Use phase names that match the step name (`step:0-ask`, `step:1-ingest`,
`step:1b-approve`, `step:1c-storyline`, `step:2-plan`, `step:2a-fanout`,
`step:3-build`, `step:4-verify`, `step:4a-fanout`, `step:5-revise`).
For sub-agent work, add `--agent <id>` so the parallel windows are
distinguishable. Missing `end` events still show up as dangling `start`
in the report — useful for catching aborted phases.

## Parallel mode — when slide_count ≥ 10

For larger decks (≥10 slides), Step 2 (authoring) and Step 4 (verify)
parallelize cleanly via subagents:

- **Step 2a (fan-out authoring)**: parent runs `deck plan-skeleton` to
  centrally pick layouts and emit an empty plan.yaml; parent spawns
  3–5 subagents (one per slide range) to author the `content:` blocks
  in parallel; parent runs `deck plan-merge` to collate. See
  [§ Step 2a](#step-2a--fan-out-authoring) below.
- **Step 4a (fan-out verify)**: parent spawns one subagent per
  verify aspect (`bbox`, `font`, `narrative`, `brand`, `image`,
  `content`); each runs `deck verify-aspect <name>` and emits a
  `verify-<aspect>.json`; parent runs `deck verify-collate` to fold
  them into a single `verify_report.md`. See
  [§ Step 4a](#step-4a--fan-out-verify) below.

Decks under 10 slides skip the fan-out — the coordination overhead
(extra subagent input tokens, parent-side merge) eats the wall-clock
win.

## Brand layout inventory — before you do anything else

Every brand inherits the toolkit pool of 43 layouts (process-flow,
excalidraw-diagram, excalidraw-diagram-full, svg-infographic,
svg-infographic-full, kpi-grid, bar-chart, roadmap, recommendation,
etc.) from `feinschliff/layouts/`. A brand's own `layouts/` directory
is **additive**: bespoke layouts add to the pool or override toolkit
layouts by name.

Before claiming a brand can't serve a brief, run (from the repo root):

```
uv run feinschliff brand inspect <brand>
```

The output reports `N inherited, M overridden, K brand-only`. Treat
the total — not just brand-only — as the available pool. For example,
`gs-ramspau` ships 6 bespoke layouts and inherits 41 toolkit ones, so
diagram, chart, and framework layouts are all available even though
none of them live in `brands/gs-ramspau/layouts/`.

**Never tell the user "this brand has only N layouts" by counting
only the brand-local directory.** That's the toolkit pool not yet
queried.

## Step 0 — Set the perfection bar (ask the user)

Before ingesting, ask the user once:

> **How perfect should this be?** Default is **3 iterations** (good enough for most decks). Say "perfectionist" or "polish it" if you want **6 iterations** (first-impression decks, exec audiences, board materials).

The answer sets the iteration budget for step 6. Defaults to 3 if the user doesn't respond or says "normal" / "default".

If image style is ambiguous from the brief, also ask here (bundle it into the same message, not a separate turn):

> **Visual style for images?** Options: photorealistic photos · illustrations · minimal/no images · data-viz only. Skip this if the brief makes it obvious (e.g., a data-heavy technical deck → data-viz; a human-narrative deck → photorealistic).

## Step 1 — Ingest

**Infer verbosity tier.** Before generating slide content, decide how much text each slide should carry. Three tiers:

| Tier | Slide text budget | When to use |
|---|---|---|
| `concise` | ~20 words per slide (action title + minimal body) | Live presentation, exec audience, high visual-to-text ratio |
| `standard` | ~40 words per slide | Default — most internal decks, team reviews |
| `text-heavy` | ~60 words per slide | Leave-behind / async deck, developer audience, reference material |

Infer the tier from the brief: exec audience or `delivery: live` → `concise`; async deck or developer audience → `text-heavy`; otherwise → `standard`. Record as `verbosity` in `design_brief.json`. Use it when filling content slots in step 2 — a `concise` deck's body slots get one sentence; a `text-heavy` deck's get two or three. These targets apply to the **outline** phase; layout-specific slot constraints (maxItems, maxwidth) still govern the final render.

**Infer delivery context.** Decide how the deck will be consumed (`live | async | both`) and the physical setting (`in-person | virtual | hybrid`). Record as `delivery` and `delivery_mode` in `design_brief.json`. When `delivery_mode` is `virtual` or `hybrid`, apply the safe-zone rule during step 2: place critical content (headlines, KPIs, CTAs) in the top 60% and centre 80% of the slide canvas.

**Infer image style.** Before sourcing any assets, lock down a single visual style that will govern all image slots in the deck. Record as `image_style` in `design_brief.json`. Use the following heuristics:

| Brief cues | `image_style` |
|---|---|
| Technical/engineering deck, architecture, data-heavy | `data-viz` |
| Human-centred story, customer narrative, leadership pitch | `photorealistic` |
| Product UI, startup, B2B SaaS | `illustration` |
| Minimal brand pack (Nord, Solarized, Catppuccin) | `minimal` |
| Abstract / conceptual strategy deck | `abstract` |
| No images planned (data-only deck, all-chart deck) | `none` |

If the user explicitly names a style preference ("keep it clean and minimal", "use real photos"), that overrides the heuristic. If the brief is ambiguous, ask once at Step 0 ("Should the deck use photorealistic photos, illustrations, or a minimal/data-viz style?") rather than guessing. Step 4 fires `image-consistency` when image assets visually diverge from the declared style, and `image-slide-fit` when an individual image competes with the slide's action title or clashes with the brand palette.


**Create mode:** parse the brief. Identify:
- Overall deck purpose (executive update, technical review, product announcement, etc.).
- Each distinct concept / topic → one slide.
- Quantitative data → kpi-grid or bar-chart candidates.
- Comparisons → 2-column-cards or bar-chart.
- Sections → chapter-opener if >2 sections.

**Polish mode:** open the `.pptx` with python-pptx. For each slide:
- Extract: title, body text, bullet lists, image references, table data.
- Classify concept (via LLM): one of [title, chapter, agenda, data-quantity, data-comparison, content, quote, closer].
- Capture raw content verbatim — don't paraphrase.

**Critique mode:** same as polish ingest (content is derived from the existing `.pptx`).

**Also infer the design brief.** See `design-brief-schema.md` for fields. Write `design_brief.json` alongside `content_plan.json`.

### Brief inference — concrete procedure

Given `content_plan.json`, produce `design_brief.json` in one LLM pass:

1. **Audience:** infer per `audience-calibration.md` inference cues. Default to `manager` when ambiguous. Record a one-sentence `audience_notes`.
2. **Takeaway:** the single sentence the audience should repeat. Derive from the brief's strongest claim; if several compete, pick the one aligned with the business outcome.
3. **Frame:** apply `narrative-frames.md` inference cues. Pick ONE frame based on the cues — the planner does not maintain a separate frame registry. Candidates include the original consulting arcs (SCQA, PSSR, Sparkline, Man-in-a-Hole, ABT) plus three audience-design framings: **PPF** (Past-Present-Future, for trajectory / evolution decks), **PSE** (Problem-Solution-Evidence, for sales / pitch decks that need to convince skeptical buyers), and **KEA** (Knowledge-Emotion-Action, for change-management decks where the audience must feel urgency before they will act). If ambiguous, SCQA is the default. Name the runner-up in `frame_rationale`.
4. **Hook:** pick a technique (`startling-stat` / `provocative-question` / `brief-story` / `demonstration` / `contrast`) and draft the opener ≤20 words.
5. **Red line:** one sentence capturing the slide sequence's argument arc.
6. **Slides[]:** for each slide in `content_plan.json`, assign a `role` (from the frame's role set), a `claim` (see `slide-claim-test.md` — must be a claim, not a topic), and a one-sentence `audience_fit`.
   - **For data/chart slides** (role `evidence` with `concept_count > 1` quantitative; or any slide whose planned layout is in the data/chart set — `bar-chart`, `line-chart`, `kpi-grid`, `scorecard`, `stacked-bar`, `waterfall`), also emit a `so_what` slot in `content_plan.json` carrying the LLM-derived takeaway from the data, not just the data itself. The takeaway must name a metric AND a magnitude AND an actor or driver (e.g. `"Enterprise churn drove 12% revenue loss in Q3"`, not `"Improving customer outcomes through optimized retention"`). The downstream `vague-so-what` content lint enforces this — see `iteration-loop.md` defect #25.

Validate the result against the schema:

```python
import sys
sys.path.insert(0, "/<path>/agentic-toolkit/feinschliff/skills/deck/lib")
from design_brief import save_brief

save_brief(brief, Path("design_brief.json"))  # raises ValueError on invalid
```

If validation fails, the inference is broken — re-run with the error as additional context.

Output:
- `content_plan.json` — an ordered list of slide intents + raw content.
- `design_brief.json` — audience + narrative frame + takeaway + hook + red line + per-slide role and claim.

## Step 1b — Present the plan (single approval gate)

Print the `design_brief.json` as a compact summary + the planned slide order with roles and claims. Exact format in `modes.md`.

Ask once:

> Approve? (press enter) · Edit: say what to change · Redo from scratch: type 'redo'

### Handling the response

**Empty / "y" / "ok" / "approve":**
Proceed to step 2.

**Free-form edit request** — examples and handling:

| User says | Revise |
|---|---|
| "make it 6 slides" | Cap `slides[]` to 6 by merging / dropping the weakest claims. Re-print. |
| "audience is developers" | Change `audience` to `developer`, re-derive `audience_notes`, re-write each `slides[].audience_fit`, re-print. |
| "drop slide 5" | Remove `slides[4]`, renumber indices, re-print. |
| "use PSSR instead" | Change `frame` to `pssr`, re-sequence slide `role`s per the frame's role order, re-print. |
| "make the takeaway punchier" | Rewrite `takeaway`; if it shifts the whole deck, offer a redo. Re-print. |

Targeted revision preserves everything the user didn't complain about. Re-print the full summary (so the user sees the delta in context); re-ask.

**"redo" / "start over":**
Discard `design_brief.json` and `content_plan.json`, re-run step 1 from scratch, re-print.

### For `/deck critique` mode only

After step 1b displays, stop here. Don't proceed to step 2. Jump directly to step 4 on the existing `.pptx`. See `modes.md`.

## Step 1c — Storyline phase (NEW)

Between step 1b approval and step 2 plan, run a **title-only storyline
gate**. This catches broken narrative arcs *before* render budget is
spent on layouts and content.

The orchestrating LLM (you) does four things, in order:

1. **Materialize the contact sheet.** Run:

   ```bash
   uv run feinschliff deck storyline content_plan.json -o out/storyline_report.md \
     --brief-summary "<one-line summary from design_brief.json>"
   ```

   This writes a "Verdict: pending" report with the numbered titles. If the
   user passed `--no-storyline` (skill-level flag — see modes.md), skip this
   step entirely.

2. **Judge the narrative arc.** Read `out/storyline_report.md`. Ask:

   - Do the titles **lead with the answer** (Pyramid Principle)? The first 1-3
     titles should carry the recommendation or thesis, not the lead-in data.
   - Do they form a **coherent argument** when read in order? A reader scanning
     only the titles should grasp both (a) the main conclusion and (b) how you
     got there.
   - Is each title a **claim**, not a topic? See `slide-claim-test.md`.
   - **Tag each slide with its SCR role.** Add a `narrative_act` field per
     slide in `content_plan.json` with one of `situation`, `complication`,
     or `resolution`. Slides that don't carry narrative weight (chapter
     openers, agenda, closer) may be tagged `null` or omitted. This feeds
     the deck-level `narrative-arc-missing` verify class at step 4 (see
     `iteration-loop.md` defect #20) and the picker's `narrative_act`
     signal for Phase 4 layouts.

   If problems exist, list them as one-line suggestions.

3. **Rewrite the report with a verdict.** Overwrite
   `out/storyline_report.md` with `verdict: clean` or `verdict: dirty` in the
   header (use the same shape — see step 4's `verify_report.md` for the
   pattern). If dirty, include a `## Suggestions` section with one bullet per
   issue.

4. **Surface to the user.** Print the contact sheet + verdict to the chat. If
   dirty, ask whether to revise `content_plan.json` titles now or proceed
   anyway. If clean, proceed to step 2 automatically.

**Why this gate exists.** The title-only readability test is the universal
McKinsey/BCG/Bain quality check ("read just the slide titles — does the story
make sense?"). Catching narrative breaks here is *cheap*: no layouts picked,
no content slots filled, no render. Catching them at step 4 verify is
*expensive*: one full build cycle wasted. This gate trades 30 seconds of LLM
judgment for an entire iteration of the build/verify loop.

**Skip path.** If the user invoked /deck with `--no-storyline` (or said "skip
storyline" at step 1b), proceed directly to step 2. The deck-level
`title-story-spine` verify class at step 4 still catches narrative breaks,
just later in the loop.

## Step 2 — Plan

Score candidate layouts using `lib.layout_picker.pick_layout`. The picker
consumes the planning-time signals you already have on each slide:

```python
from lib.layout_picker import pick_layout
from lib.dsl.parser import parse_file
from lib.dsl.tokens import load_tokens
from lib.slot_budget import compute_slot_budgets, format_budget_hint
from lib.brand_discovery import find_brand

brand_dir = find_brand("feinschliff").root
tokens = load_tokens(brand_dir)

for slide in content_plan["slides"]:
    candidates = pick_layout(
        role=slide.get("role"),
        concept_count=slide.get("concept_count"),
        data_quantity=slide.get("data_quantity"),
        comparison=slide.get("comparison"),
        narrative_role=slide.get("narrative_role"),
        narrative_act=slide.get("narrative_act"),
        time_axis_role=slide.get("time_axis_role"),
        audience_mode=slide.get("audience_mode"),
        diagram_kind=slide.get("diagram_kind"),
        layout_history=picked_so_far,
        top_k=3,
    )
    chosen = candidates[0]
    picked_so_far.append(chosen["layout"])
```

The picker enforces `when_not_to_use` rules declared on each layout and
applies a variety penalty over `layout_history`, so consecutive slides
don't reuse the same layout.

**Compute slot budgets** before drafting slot values. The same call
runs at pre-render content-lint time, so honoring the budget here
avoids burning an iteration on `slot-overflow` defects:

```python
layout_path = Path("layouts") / f"{chosen['layout']}.slide.dsl"
nodes, _ = parse_file(layout_path)
budgets = compute_slot_budgets(nodes, tokens)
print(format_budget_hint(budgets))
```

**Diagram and tech-radar layouts are first-class v2 layouts.** When
the brief mentions diagram / flowchart / architecture / system overview
/ layers / concept map / block diagram, pick a diagram layout based on
audience and complexity:

- `excalidraw-diagram` (narrow band, 1720×480 slot) — 2-8 nodes, simple
  or medium complexity, general / executive audiences.
- `excalidraw-diagram-full` (full-slide, 1720×720 slot, virtual
  6880×2880 canvas) — 10-20+ nodes, deep architecture diagrams with
  zones / typed arrows / typed callouts, technical audiences
  (firmware / embedded Linux / safety / architecture). Pass
  `diagram_complexity: deep` in the slide signals.
- `svg-infographic` / `svg-infographic-full` — same narrow/full split
  for quantitative custom infographics.
- Parameterized diagram templates (`process-flow`, `pyramid`, `venn`,
  `2x2-matrix`, `funnel`, `gantt`) when they fit the data shape.

Author the diagram DSL inline as the slide's `dsl` slot value. See
`excalidraw/references/dsl-syntax.md` (narrow) +
`excalidraw/references/examples-deep.md` (full) for the grammar and
patterns. One big diagram per slide — never split one concept across
two diagram slides; instead, pair a narrow overview slide with a
follow-on `-full` deep-dive slide.

When the brief mentions tech radar / technology radar / GenAI radar,
pick `tech-radar`. Slot args: `view` (one of
`genai-thoughtworks`, `genai-agents`, `genai-models`, `genai-skills`,
`genai-tooling`), optional `volume` (edition number), and `new_since`
(ISO date for the NEW badge).

Output: `plan.yaml` — an ordered list of `{layout, content_inline|content_file}`
entries that `feinschliff deck build` consumes directly (see Step 3).

## Step 2a — Fan-out authoring (decks ≥ 10 slides)

Use this when slide_count ≥ 10 to cut authoring wall-clock by ~3-5x.
Required to be opted into — short decks should skip.

**Parent (orchestrator) flow:**

1. Mark phase: `feinschliff deck log-event step:2a-fanout start --dir <deck-dir>`.
2. Run centralized layout pick:
   ```bash
   uv run feinschliff deck plan-skeleton \
     <deck-dir>/content_plan.json \
     -o <deck-dir>/plan.skeleton.yaml \
     --out-pptx <deck-dir>/deck.pptx
   ```
   This consumes the same `layout_history` discipline as a serial pass.
   Resulting file has `layout:` filled and `content: {}` empty per slide.
3. Emit a one-page **color contract** (`<deck-dir>/color_contract.md`)
   that pins semantic→token mappings so subagents don't pick divergent
   colors. Sample contract:
   ```
   Primary callout / hero accent  → `accent`
   Problem markers / red lines    → `severity-medium`
   Secondary chrome / neutral box → `surface-2`
   Success state                  → `status-done`
   Inactive / muted               → `inactive` (auto-dashed)
   ```
4. Spawn N subagents (typically 3 for 10–15 slides, 5 for ≥18) using the
   `general-purpose` Agent type. Pass each subagent:
   - The full `design_brief.json` and `content_plan.json` content (read into the prompt).
   - The skeleton entries for **their assigned slide range** (e.g. slides 1–5).
   - The `color_contract.md` content.
   - The **picked layout DSL files** for their slides (so they know what slots exist).
   - Instruction: "Author the `content:` block for each assigned slide. Write the
     result as one YAML file per slide at `<deck-dir>/chunks/slide-NN.yaml` in
     the shape `{index: N, content: {...}}`. Use the color contract verbatim.
     Do not change the `layout:` unless you have a strong reason."
5. Wait for all subagents to return.
6. Merge:
   ```bash
   uv run feinschliff deck plan-merge <deck-dir>/plan.skeleton.yaml \
     --chunk <deck-dir>/chunks/slide-01.yaml \
     --chunk <deck-dir>/chunks/slide-02.yaml \
     ... \
     -o <deck-dir>/plan.yaml
   ```
7. Mark phase: `feinschliff deck log-event step:2a-fanout end --dir <deck-dir> --elapsed-ms <ms>`.
8. Continue to Step 3 with the merged `plan.yaml`.

**Why the centralized pick first?** The variety-penalty in
`lib.layout_picker.pick_layout` is a sliding window over `layout_history`.
Subagents picking layouts in parallel can't see each other's choices —
the result is monotony (three bar-charts in a row). Pre-picking on the
parent side preserves the variety guarantee.

**When a subagent disagrees with the picked layout** (e.g. the AI for
slides 6–9 thinks slide 7 should be `excalidraw-diagram` not the picked
`text-picture`), it can override by adding `layout: layouts/<name>.slide.dsl`
to its chunk entry. `deck plan-merge` honors per-slide layout overrides.

## Step 3 — Build

The build is one CLI invocation. The orchestrator hands `feinschliff deck build`
a plan YAML; the CLI runs `compile_slide()` per slide, validates each, composes
the multi-slide deck, and writes `.pptx` + diagrams alongside.

```yaml
# out/<deck>/plan.yaml
brand: feinschliff
out: out/<deck>/deck.pptx
slides:
  - layout: layouts/title-cover.slide.dsl
    content_file: out/<deck>/slide-01.yaml
  - layout: layouts/executive-summary.slide.dsl
    content_inline:
      title: "Q1 results"
      subtitle: "What we shipped"
      body: "Three things drove the quarter..."
  - layout: layouts/excalidraw-diagram.slide.dsl
    content_file: out/<deck>/slide-03.yaml      # has a `dsl` slot with the diagram body
```

Run:

```bash
uv run feinschliff deck build out/<deck>/plan.yaml
```

The CLI:
1. Resolves the active brand via `lib.brand_discovery.find_brand`.
2. For each slide, calls `lib.pipeline.compile_slide(...)` — parsing, interpolating, expanding diagrams (running the diagram validators), and expanding compounds.
3. Aborts on any fatal defect (defect taxonomy: see `feinschliff/docs/quality-contract.md`). Pass `--allow-diagram-warnings` to demote diagram-overflow / diagram-text-too-small. Pass `--allow-missing-assets` to ship with grey-box pictures (not recommended for final builds).
4. Composes all slides into one `.pptx`, writes `diagrams/` next to the output, and writes per-source asset locks under `out/<deck>/asset_lock.json` and credits under `out/<deck>/credits.md` whenever search-resolved assets were used.

Diagram layouts (`excalidraw-diagram.slide.dsl`,
`excalidraw-diagram-full.slide.dsl`, `svg-infographic.slide.dsl`,
`svg-infographic-full.slide.dsl`) are full first-class v2 layouts. The
agent authors the diagram DSL inline in the slide's content YAML as
the `dsl` slot value; the expander turns it into a PNG and embeds it.
The `-full` layouts use a virtual 6880×2880 canvas so the model has
16× more pixel area to compose into; PowerPoint downscales on insert.
See `feinschliff/excalidraw/references/dsl-syntax.md` and
`feinschliff/skills/excalidraw/references/examples-deep.md`.

Output: `out/<deck>/deck.pptx` (draft).

## Step 4 — Verify (visual + theory) — MANDATORY, NEVER SKIPPED

**This step runs at least once. No exceptions.** You do not know whether step 3 succeeded until you look at the rendered PNGs. "The build didn't error" is not verification. Even if the iteration budget is 1, you still run one verify pass before declaring completion.

Render the draft:
```bash
soffice --headless --convert-to pdf --outdir /tmp/deck-verify out/<name>.pptx
pdftoppm -r 96 -png /tmp/deck-verify/<name>.pdf /tmp/deck-verify/slide
```

For each PNG, LLM inspects (visually read the PNG file — do not skip the Read call) for all 29 defect classes per `iteration-loop.md`. The canonical visual reference for "what this layout should look like" is the active brand's `feinschliff/<brand-root>/claude-design/<brand>-2026.html` (e.g. `feinschliff/brands/feinschliff/claude-design/feinschliff-2026.html` by default) — open it alongside when uncertain whether a slide matches brand intent.

**Required artifact:** write `out/verify_report.md` — human-readable, overwritten on each verify pass. Shape:

```markdown
# Verify Report — <name>.pptx

- **Iteration:** 1 of 3
- **Verdict:** dirty — 2 defects across 1 of 8 slides
- **Rendered PNGs:** `/tmp/deck-verify/slide-*.png`
- **Reference:** `feinschliff/<brand-root>/claude-design/<brand>-2026.html`

---

## Slide 3 — "Our Approach" (layout: two-column-cards)

- **claim-title** — title "Our Approach" is a topic noun.
  **Fix:** Rewrite as a claim, e.g. "We ship daily because we test first".
- **bullet-dump** — 7 peer-level bullets, no hierarchy.
  **Fix:** Subordinate under 3 sub-headings; drop weakest two bullets.

## Slide 5 — "Q1 Results" (layout: kpi-grid) ✅

_No defects._

<!-- ...one section per slide... -->
```

The header block is the completion gate: `Verdict:` must be readable by both Claude (to decide whether to loop) and the user (to understand what's wrong). If `verdict` is `clean`, list every slide with `✅ No defects.` so the user sees the full coverage — don't silently omit passing slides.

`out/verify_report.md` is overwritten on each iteration; the file always reflects the most recent build. If you need iteration history, prior reports are recoverable from `git log` or conversation transcript.

If the file does not exist on disk, the deck is not done — regardless of how confident you feel about the build. Before telling the user "done", confirm the file exists and the header says `Verdict: clean` (or budget is exhausted and you're emitting residuals per step 5).

## Step 4a — Fan-out verify (decks ≥ 10 slides)

Use this when slide_count ≥ 10 to cut verify wall-clock from ~3-5 min to
~1-1.5 min. The verify pass is decomposed into six independent aspects,
each runnable as a subagent in parallel:

| Aspect | Checks | Determinism | Time budget |
|---|---|---|---|
| `bbox` | bounding-box overflow, text-overflow, out-of-bounds, diagram-overflow | full | ~5-10s |
| `font` | text-too-small, role-mismatch, fragile-detail-role | full | ~2-5s |
| `narrative` | SCQA / claim-title / title-story-spine / MECE | LLM | ~30-60s |
| `brand` | non-canonical-token, color-contrast | partial (token check is full) | ~5-15s |
| `image` | image-style consistency, image-slide-fit | LLM | ~30-60s |
| `content` | filler-word, title-body-coherence, redundancy | partial (filler is full) | ~30-60s |

**Parent (orchestrator) flow:**

1. Mark phase: `feinschliff deck log-event step:4a-fanout start --dir <deck-dir>`.
2. Spawn 6 subagents in parallel (one per aspect). Each subagent runs:
   ```bash
   uv run feinschliff deck verify-aspect <aspect> \
     --plan <deck-dir>/plan.yaml \
     --design-brief <deck-dir>/design_brief.json \
     --png-dir <deck-dir>/verify/ \
     -o <deck-dir>/verify-<aspect>.json
   ```
   Aspects with `needs_llm: true` (narrative, image, content) require the
   subagent to follow up with LLM judgment on the materialized data
   (contact sheet for narrative, PNG inspection for image) and append
   findings to the JSON before returning.
3. Wait for all 6 subagents to return.
4. Collate:
   ```bash
   uv run feinschliff deck verify-collate \
     --plan <deck-dir>/plan.yaml --iteration N --budget M \
     --png-dir <deck-dir>/verify/ \
     --aspect <deck-dir>/verify-bbox.json \
     --aspect <deck-dir>/verify-font.json \
     --aspect <deck-dir>/verify-narrative.json \
     --aspect <deck-dir>/verify-brand.json \
     --aspect <deck-dir>/verify-image.json \
     --aspect <deck-dir>/verify-content.json \
     -o <deck-dir>/verify_report.md
   ```
5. Mark phase: `feinschliff deck log-event step:4a-fanout end --dir <deck-dir> --elapsed-ms <ms>`.

**Defect dedup.** Two aspects can flag the same root cause from different
angles (e.g. `bbox`/`text-overflow` and `font`/`detail-fragile` on the
same slide). The collator preserves both findings — the revise pass can
fix once and clear both flags on the next iteration.

**Token cost.** Six subagents each load the design_brief + plan.yaml
extract. Roughly 5–6× the input tokens vs serial. Worth it above
~10 slides; not worth it below.

## Step 5 — Revise (if defects)

If `verify_report.md` header says `Verdict: dirty`: adjust `deck_plan.json` (change layouts, shorten text, split slides, rewrite titles as claims) and loop back to step 3. Increment `Iteration:` in the next verify report.

**Hard stop at the budget set in step 0.** Default = 3 iterations, perfectionist = 6. Each iteration = one build + one verify pass. The verify pass runs on iteration 1 too — there is no "skip verify on the last happy-path build" shortcut.

If the final iteration still has defects:
- Emit the current draft to `out/<name>.pptx`.
- Emit `out/RESIDUAL_ISSUES.md` listing unresolved defects (derived from the final `verify_report.md`).
- Surface both to the user, explicitly noting "budget exhausted with N defects remaining".

## Critique-mode flow (variant)

`/deck critique existing.pptx` runs a subset of the pipeline:

```
Step 0   ASK perfection bar                             — SKIPPED (no iteration loop)
Step 1   INGEST existing .pptx → content_plan.json
         DERIVE design_brief.json from extracted content
Step 1b  PRESENT brief for approval / edit             — user can correct audience/frame
Step 2   PLAN                                          — SKIPPED
Step 3   BUILD                                         — SKIPPED
Step 4   VERIFY                                        — runs on the existing .pptx
Step 5   REVISE                                        — SKIPPED (read-only)
```

Outputs next to the source `.pptx`:
- `<name>-critique.md` — per-slide defect list with suggested fixes.
- `design_brief.json` — the brief Claude derived.

No mutation of the source. See `modes.md` for the critique output format.

## Out of scope

- Chart regeneration (charts in the source pptx stay embedded as pictures).
- Animations and transitions.
- Speaker-notes reformatting (copy verbatim).
- Multi-brand within a single deck (one active brand pack per `/deck` invocation, resolved from `FEINSCHLIFF_BRAND` / `--brand`).
