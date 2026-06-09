# Iteration Loop — Build, Verify, Revise

The central discipline that separates Feinschliff decks from one-shot AI generators: after building, LOOK at what you generated and revise until it's good.

## The non-negotiable rule

**You never declare the deck done without running the verify pass at least once.** One build + zero looks = not a deck, a guess. The failure mode this prevents: Claude builds a `.pptx`, sees no Python error, announces "done", and hands the user a draft with empty placeholders, text overflow, and off-brand colours because nobody ever opened the rendered output.

Concretely:
- **Minimum 1 verify pass**, always — even on the happy path where the first build looks plausible.
- **`out/verify_report.md` is the completion gate.** Markdown, human-readable, so the user can scan it without parsing JSON. If it isn't on disk, the skill hasn't finished. See `pipeline.md` step 4 for the format.
- **The HTML design is the visual ground truth.** The active brand's `feinschliff/<brand-root>/claude-design/<brand>-2026.html` defines what each layout should look like (e.g. `feinschliff/brands/feinschliff/claude-design/feinschliff-2026.html` by default). When the rendered PNG diverges from the HTML reference for that layout, that's a defect — even if it doesn't map cleanly to one of the 11 named classes.

## Budget (ask the user at the start)

Ask once, before the first build: **"How perfect should this be?"**

| Answer | Iteration budget | When to use |
|---|---|---|
| default / normal / "3" | **3 iterations** | Everyday decks — weekly updates, internal reviews, working drafts. Catches obvious defects without spiraling. |
| perfectionist / "polish it" / "6" | **6 iterations** | First-impression decks — exec audiences, board packs, client-facing teasers. Extra passes for typography tuning, overflow edge cases, cover-slide polish. |

Default to 3 if the user doesn't respond or says "normal". **The budget is a ceiling on revise cycles, not a floor on verify passes — verify always runs at least once regardless of budget.**

## Loop

```
 build    ─┐
           ▼
     [autofix inner loop — up to 3 cycles, no LLM, no render]
     deck verify-static --json > defects.json
     deck apply-fixes plan.yaml --defects defects.json   ← resolves ~30-40% dirty verdicts
           ▼
     render (soffice → PDF → pdftoppm → PNGs)
           ▼
     verify (LLM eyeballs each slide for defects)
           ▼
       ┌───────┐
       │ pass? │── yes ──> done
       └───┬───┘
           │ no
           ▼
       revise (adjust deck_plan.json, e.g. change layout, shorten text)
           │
           └──────────────────────┐
                                  ▼
                             (back to build)

Max N iterations total (N = 3 or 6 per the budget ask).
After iter N, emit RESIDUAL_ISSUES.md.
```

### `deck apply-fixes` — mechanical defect resolution

Before the render pass, `deck apply-fixes` (or `deck build --autofix`) runs the
static verifier and applies deterministic patches for known defect classes.  This
resolves ~30-40% of dirty verdicts inside the same iteration without an LLM
revise turn.

**Supported patch actions (v1):**

| Defect class | Patch action | What it does |
|---|---|---|
| `slot-overflow` | `shorten_slot` | Trim `plan.slides[i].content[slot]` to `budget_chars`. Cuts at sentence boundary first, then word boundary, then hard-cut. |
| `text-overlap` | `shorten_slot` | Shorten the offending slot by 75% of current length (or to explicit budget if present). |
| `filler-word` | `delete_word` | Remove the filler token from the slot with word-boundary regex; case-insensitive; all occurrences. |
| `bullet-dump` (>5 peers) | `drop_bullet` | Parse bullet lines; score by length (shortest = weakest); drop weakest until ≤5 remain; preserve order of survivors. |
| `empty-placeholder` (count mismatch) | `swap_layout_smaller` | Use `pick_layout()` to find a layout with fewer required slots; update `slide["layout"]`. |
| `slot-overflow` (>20% over after shorten) | `swap_layout_larger` | Optional v1 — find a layout with the same role but more body/bullet room; skip if picker returns nothing. |

**Defects skipped (LLM revise only):** `claim-title`, `title-body-coherence`,
`layout-concept-mismatch`, `out-of-bounds`, all chrome defects, etc.

**Usage:**

```bash
# Standalone fix pass:
uv run feinschliff deck verify-static plan.yaml --json > defects.json
uv run feinschliff deck apply-fixes plan.yaml --defects defects.json
# Exit 0 = patches applied; exit 1 = nothing to fix

# Integrated into build (up to 3 inner cycles, writes plan back to disk):
uv run feinschliff deck build plan.yaml --autofix
```

The `--autofix` flag runs up to **3 inner cycles** of verify → fix → verify.
After 3 cycles any residual static defects are printed but do **not** block the
compile — the outer orchestrator iteration handles them.

## What "verify" checks — 29 defect classes (14 legacy + 4 Layer 1 + 11 Phase 2-5)

For each slide in the rendered PNG, inspect for all 29 classes. The deterministic Layer 1 chrome rules run in `cli/verify.py` (pp-chrome + chrome-drift); the LLM placeholders (accent-as-decoration, focal-ambiguity) get implemented when Layer 3's Tier 2 composite prompt lands. Same prompt as before, extended to cover theory + the new chrome surface.

### Visual defects (5 legacy + 4 Layer 1)

1. **text-overflow**: text bleeding past layout placeholder. Fix: shorten source text OR move to a layout that accommodates longer content.
2. **empty-placeholder**: a placeholder that didn't get filled. Fix: the source content didn't match the layout's slot expectations — move to a smaller layout, or add the missing content if reasonable.
3. **layout-concept-mismatch**: the chosen layout doesn't match the content's concept (e.g. comparing 2 items but used 4-column-cards). Fix: pick a better layout from the catalog.
4. **brand-violation**: a colour or font off-brand. Fix: a slot was filled with raw html/markdown that overrode styling. Plain-text the content.
5. **density-mismatch**: slide feels too dense or too sparse. Fix: split or merge slides.
6. **pp-chrome** *(deterministic, Layer 1)*: a shape carries a drop-shadow, gradient fill, or outline wider than 1pt outside an `effect:allow` scope. The emitter's `sanitize_chrome` post-build pass should remove these; this rule asserts it did. Fix: investigate why a shape bypassed sanitation — usually a per-brand override emitted raw XML.
7. **accent-as-decoration** *(LLM, Layer 3 — Tier 2 composite)*: accent-coloured pixels exceed 15% of canvas OR are spread as decoration rather than concentrated on one emphasis element. Detected in Layer 3's Tier 2 composite prompt; placeholder here so layout authors can write `Watches for:` blocks against it. Fix: reduce accent surface; reserve colour for the answer.
8. **focal-ambiguity** *(LLM, Layer 3 — Tier 2 composite)*: the LLM's first-fixation report does not match the layout's `theory.focal_hierarchy[0]`. Placeholder for Layer 3. Fix: strengthen the focal element (size + weight + accent) or demote competing elements.
9. **chrome-drift** *(deterministic, Layer 1)*: logo / footer / pgmeta positions vary across slides beyond a 4-design-px tolerance. Fix: the chrome compound should be sourced once and reused; per-slide overrides are a bug.

### Theory defects (16 classes)

10. **claim-title**: title is a topic not a claim. Detection per `slide-claim-test.md`. Fix: rewrite as a claim sentence (verb or specific number).
11. **one-idea-violated**: body has connectives ("and also", "furthermore") or multiple disjoint claims. Detection per `anti-patterns.md`. Fix: split into two slides.
12. **bullet-dump**: 5+ peer-level bullets with no hierarchy. Detection per `anti-patterns.md`. Fix: subordinate / group / split.
13. **audience-mismatch**: jargon density or abstraction level off for `design_brief.audience`. Detection per `audience-calibration.md`. Fix: translate or re-level.
14. **red-line-break**: slide's `role` doesn't match its position in the `design_brief.frame`'s role order. Detection per `narrative-frames.md`. Fix: reorder, re-role, or re-frame.
15. **curse-of-knowledge**: technical term used without grounding for the audience. Detection: term is not defined earlier, not in the audience's tolerated vocabulary (per `audience-calibration.md`), and load-bearing for the slide's claim. Fix: translate / define inline / demote.
16. **redundancy-overload**: slide body duplicates what the presenter would say aloud (Redundancy Effect). Detection per `anti-patterns.md` #7. Fix: strip body to minimum that supports a visual claim; replace at least one text block with a chart, diagram, or image if no visual evidence exists.
17. **truncated-y-axis**: bar/column chart Y-axis baseline is above zero, exaggerating visual difference. Detection per `anti-patterns.md` #8. Fix: start at zero, or switch to a line chart, or annotate the break explicitly with a zigzag.
18. **missing-baseline**: a number presented without a comparative anchor (prior period, target, benchmark, denominator). Detection per `anti-patterns.md` #9. Fix: add the anchor or lead with the qualitative trend instead.
19. **title-story-spine** *(deck-level, NEW Phase 2)*: reading the
    concatenation of slide titles, in order, does *not* tell a coherent
    argument. The reader can't grasp the deck's claim and supporting moves
    from titles alone. Detection: same prompt that runs at step 1c
    storyline (see `pipeline.md` step 1c). If step 1c was skipped, run it
    here against the *built* deck's titles (use
    `lib.verify.deck.titles.extract_titles_from_pptx`). Fix: rewrite titles
    as full-sentence claims; reorder so the answer leads; ensure the deck
    has a Situation → Complication → Resolution shape.
20. **narrative-arc-missing** *(deck-level, NEW Phase 3)*: the deck contains a Situation slide AND a Resolution slide but no Complication. Audience left asking "why act now?" — the Complication slide is what justifies action. Detection: deterministic via `lib.verify.deck.narrative_arc.check_narrative_arc(narrative_acts)`. Input: the `narrative_act` field per slide in `content_plan.json` (assigned at step 1c). Fix: add a Complication slide between Situation and Resolution that names the cost of inaction or the trigger forcing the decision.
21. **title-body-coherence** *(per-slide, deck-level module, NEW PR A)*: each slide's title makes a claim; the body must prove that claim AND nothing more. Two failure modes:
    - Title says X but the body's evidence supports Y (mismatch).
    - Body contains content unrelated to the title's claim (drift).

    Detection: per slide, extract title + body via `lib.verify.deck.title_body.extract_slide_title_and_body(pptx, slide_index)`. Pass both to an LLM judgment with the rule "nothing in title not in body; nothing in body irrelevant to title". Fire defect on either failure mode.

    Fix: rewrite the title to match what the body proves, OR cut the irrelevant body content, OR add evidence so the title's claim is supported.
22. **non-mece-breakdown** *(deck-level, NEW Phase 5)*: a breakdown slide's items don't honor the MECE principle (Mutually Exclusive, Collectively Exhaustive). Two failure modes:
    - **Numeric**: items have explicit values/percentages and sum to something other than 100% (±2pp tolerance). Detection: deterministic via `lib.verify.deck.non_mece.check_non_mece(items)`.
    - **Semantic**: item labels overlap or have gaps that a 100%-sum check can't catch (e.g. "Enterprise", "Mid-market", "Customer churn" — first two are MECE, third overlaps both). Detection: LLM judgment per slide where `narrative_role` is "breakdown" or "segmentation".

    Fix: rebalance the breakdown so categories are mutually exclusive AND collectively exhaustive. Often easier to refactor as 80/20 (the top 2-3 explicit + "Other" for the long tail).
23. **squint-test** *(visual, NEW Phase 5)*: slides that pass per-element checks but fail when you step back and squint — the headline isn't legible at thumbnail size, the visual hierarchy collapses, or the slide reads as a wall of small things. Detection: render the slide PNG at 25% scale via `lib.verify.deck.squint.make_squint_thumbnail(source, output, scale=0.25)`. LLM reads the thumbnail and judges: "Can you still identify the headline message? Does the slide read as one clear thing?". Fire defect if either fails.

    Fix: enlarge the action title relative to body content; reduce slot count; remove decorative chrome that competes with the message.
24. **slide-necessity** *(per-slide, NEW Phase 5, critique-only)*: a slide that doesn't earn its place in the deck. Test: if you remove this slide, does the deck still tell its story? If yes, the slide is unnecessary. Detection: pure LLM judgment using `lib.verify.deck.slide_necessity.materialize_necessity_context(titles, slide_index)` to fetch the surrounding title context. Fire defect only in `/deck critique` mode — in regular verify the fix ("cut this slide") isn't actionable mid-build.

    Fix: cut the slide, OR sharpen its claim so it's load-bearing rather than padding.
25. **vague-so-what** *(per-slide, NEW Phase 5)*: a data/chart slide's `so_what` slot contains only corporate-speak vagueness ("Improving leveraging synergies", "Optimizing transformative innovation") with no concrete numeric or named-entity anchor. The slot is meant to carry the actionable insight from the data — vagueness defeats its purpose. Detection: deterministic via `lib.content_validator._check_so_what_vagueness` (fires when ≥2 vague keywords appear AND no digit/proper-noun anchor is present). Fix: rewrite the so_what as a specific claim — name the metric AND the magnitude AND the actor or driver.

26. **filler-word** *(per-slide, NEW)*: a data/chart slide's `so_what` slot is padded with meaningless intensifiers ("very", "really", "quite", "extremely", etc.) that dilute the claim without adding information. Unlike `vague-so-what`, a numeric anchor does **not** clear this defect — "Revenue very extremely grew by 12%" is still weaker than "Revenue grew 12%". Detection: deterministic via `lib.content_validator._check_filler_words` (fires when ≥2 filler words appear). Fix: delete the fillers; the sentence is stronger without them.

27. **layout-monotony** *(deck-level, NEW)*: three or more consecutive content slides use the same layout, creating visual repetition that forces the audience to re-orient instead of absorb. Structural layouts (title slides, chapter openers, agenda, end) are exempt — they don't rotate. Detection: walk the `deck_plan.json` layout sequence; flag any run of ≥3 identical non-structural layouts. The layout picker's `layout_history` signal pre-empts most monotony at plan time; this check catches cases where the planner had no alternative (e.g., a data-heavy deck with 4 consecutive bar-chart slides). Fix: insert a chapter opener to break the run, or switch to an alternate chart layout (`line-chart`, `stacked-bar`, `waterfall`) if the data permits.

28. **image-slide-fit** *(per-slide, NEW)*: an image asset on the slide fails as *presentation material* even if it is visually attractive. Three failure modes:
    - **Crop failure**: the image's subject matter is obscured or crops awkwardly inside the slide's picture frame (e.g., a wide landscape squeezed into a portrait slot; a person's face cut off at the eyes).
    - **Title dominance**: the image overwhelms or visually competes with the slide's action title — the eye can't find the headline because the photo is too busy, too bright, or placed where the title should read.
    - **Brand clash**: the image's dominant colours conflict with the brand palette (e.g., a vivid red hero photo on a cyan-brand deck), reducing perceived brand coherence.

    Detection: LLM visual inspection of the rendered slide PNG. The checks are:
    1. Can the action title be read at a glance (3-second billboard test) without the image competing?
    2. Is the primary subject of the image fully visible and not awkwardly cropped?
    3. Do the image's dominant tones/hues broadly align with or complement the brand palette rather than clash?

    Fix: (a) swap the image for one with better crop alignment; (b) apply a brand-tinted overlay to the picture frame to reduce palette clash; (c) if the layout positions the image behind text, darken the image region or move to a `text-picture` layout with a dedicated picture panel.

29. **image-consistency** *(deck-level, NEW)*: image assets across the deck use inconsistent visual styles, breaking the audience's mental model and making the deck feel AI-stitched rather than authored. Detection: LLM inspects all slides with image assets as a group. Flag if the set contains two or more distinct style categories (e.g., one photorealistic stock photo + one flat illustration + one abstract gradient background). Cross-check the declared `image_style` in `design_brief.json` — if absent, infer the dominant style from the first image and flag divergence in subsequent images.

    Fix: (a) replace divergent images to match the deck's declared `image_style`; (b) if no style was declared, establish one now and swap non-conforming images; (c) for brand packs with a design-system illustration library, replace ad-hoc images with in-system illustrations to guarantee consistency.


## Verify-pass LLM prompt (outline)

Build a side-by-side PNG montage for the LLM — or Read each PNG directly. **You must actually look at the images**; don't invent verdicts from deck_plan.json alone.

For each slide, note defects as `{class, detail, fix}` triples. Any slide with ≥1 defect is "dirty". If any slide is dirty, the overall verdict is `dirty`.

Write the findings as `out/verify_report.md` — the human-readable format in `pipeline.md` step 4. Every slide gets a section; passing slides show `✅ No defects.` so the user sees full coverage at a glance. Writing this file is not optional — it is the artifact that proves verification happened, AND the document the user actually reads to understand what's wrong.

## Budget mechanics

- Each iteration = 1 build + 1 LibreOffice render + 1 LLM eyeball pass. Iteration 1 always includes a verify pass — there is no iteration 0.
- `verify_report.md` header says `Verdict: clean` → done, emit the deck.
- `Verdict: dirty` and iteration < budget → revise and re-build.
- `Verdict: dirty` and iteration == budget → stop; emit residuals.
- If at the final iteration issues remain, emit:
  - Final draft `out/<name>.pptx` (with whatever improvements did land).
  - `out/RESIDUAL_ISSUES.md` listing specifically what's still off (derived from the final `verify_report.md`).
  - User decides: accept, manual-fix, or re-run with different inputs.

Theory defects and visual defects share the same iteration budget. A slide with both `claim-title` and `text-overflow` is one defective slide; one revise pass can fix both.

## Completion checklist

Before telling the user the deck is ready, confirm all of these:

- [ ] `out/<name>.pptx` exists.
- [ ] `out/verify_report.md` exists, is human-readable, and its `Iteration:` header matches the last build.
- [ ] Either the header says `Verdict: clean`, OR `Iteration == budget` AND `out/RESIDUAL_ISSUES.md` exists summarising what's left.
- [ ] You actually read the rendered PNGs during the last verify pass — not just ran `soffice` and assumed.

Skipping this checklist is the failure mode the iteration loop exists to prevent.

## Why a cap at all

One-shot agents produce garbage. 15-shot agents spiral and burn budget. A hard stop keeps iteration a discipline, not a compulsion. **3 is the sweet spot for everyday work** — enough to catch obvious defects, not enough to dither. **6 is for first-impression decks** where the extra passes are worth the cost: cover-slide polish, typography tuning, overflow edge cases that only show up on 3rd-render eyeball.

## Per-slide verify cache

`lib/verify/cache.py` provides a content-hash cache that skips LLM calls for slides whose content has not changed since the last run.

**How it works:**

Each slide's hash is `sha256(brand + layout + json.dumps(content, sort_keys=True))`. The hash intentionally excludes `_meta` (informational) and `slot_budgets` (derived) — only the inputs that affect rendering are hashed. If the hash already has a cached verdict for the rubric being run, the LLM call is skipped and `"cached": True` appears on that slide's result.

**Cost impact on a 15-slide deck with 2 dirty slides per iteration:**

| Run | LLM calls (without cache) | LLM calls (with cache) |
|---|---|---|
| Iteration 1 | 15 | 15 (cold) |
| Iteration 2 | 15 | 2 (~87% saving) |
| Iteration 3 | 15 | 2 (~87% saving) |

**Cache file:** `.verify_cache.json`, stored alongside the deck. It is gitignored.

**CLI usage:**

```bash
# Standard — cache is active when --plan is supplied
uv run feinschliff-builder verify-quality deck.pptx --plan plan.yaml --brand feinschliff

# Force full re-verify (ignore cache)
uv run feinschliff-builder verify-quality deck.pptx --plan plan.yaml --brand feinschliff --no-cache
```

The cache is keyed by `(slide_hash, rubric_name)`. Changing brand, layout, or any content slot produces a new key, invalidating that slide's entry automatically (old entries are not pruned in v1 — acceptable given small cache size).

## Implementation notes

- Always render via `soffice --headless --convert-to pdf` not PowerPoint — LibreOffice is faster, headless, and deterministic.
- `pdftoppm -r 96 -png` gives 1280×720 images that are good enough for LLM eyeballing without being huge.
- Use `PIL.Image.new` to build a side-by-side "before / after" grid for the LLM's eyeball pass — makes defect-spotting fast.
