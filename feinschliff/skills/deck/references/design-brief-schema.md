# Design Brief Schema

The inferred-at-step-1 artifact that captures message architecture for a deck. Canonical JSON schema: [`../lib/design_brief.schema.json`](../lib/design_brief.schema.json).

## Example

```json
{
  "$schema": "feinschliff/design-brief/v1",
  "takeaway": "Polish time collapsed from 3 hrs to 15 min per deck",
  "audience": "exec",
  "audience_notes": "Time-poor, outcomes-driven; will stop listening after 30s of buildup.",
  "frame": "sparkline",
  "frame_rationale": "Vision pitch oscillating painful present with desirable future; PSSR rejected because there's no discrete 'search' phase.",
  "hook": {
    "technique": "contrast",
    "opener": "Five years ago this took a week. Today it takes 15 minutes."
  },
  "red_line": "Pain → Solution demo → Results → What this unlocks.",
  "slides": [
    {
      "index": 0,
      "role": "hook",
      "claim": "Polish time has collapsed — here's why that matters.",
      "audience_fit": "Lead with impact; skip architecture for exec."
    }
  ]
}
```

## Field-by-field

### `takeaway`

The single sentence Mike wants the audience to walk away repeating. Top of the Minto Pyramid. One deck → one takeaway.

### `audience` + `audience_notes`

`audience` is one of `exec | manager | developer | peer`. `audience_notes` is the inferred rationale — what they care about, what loses them. Both drive step-2 claim wording and step-4 audience-mismatch checks. See `audience-calibration.md`.

### `frame` + `frame_rationale`

`frame` is one of:
- `scqa` — Minto Pyramid (answer first; exec / decision decks)
- `pssr` — Problem / Search / Solution / Result (journey matters; project / post-mortem decks)
- `sparkline` — What Is / What Could Be (vision / change pitch; oscillating pain↔future pairs)
- `man-in-hole` — incident / migration / crisis-and-recovery arc
- `ppf` — Past / Present / Future (trajectory / evolution decks)
- `pse` — Problem / Solution / Evidence (sales / pitch to skeptical buyers)
- `kea` — Knowledge / Emotion / Action (change-management; audience must feel urgency before they act)
- `abt` — And / But / Therefore (pre-flight narrative check; if you can't write a clean ABT, the argument isn't ready)

`frame_rationale` MUST name the runner-up frame and why it was rejected — this is the hint the user sees at step-1b for cheap override. See `narrative-frames.md`.

### `hook`

The opener. `technique` is one of 5 categories; `opener` is the actual line Claude will fill into the cover or first content slide. ≤20 words.

### `red_line`

One sentence capturing the deck's spine as a sequence. Step 4 uses this to check red-line-break defects.

### `verbosity` *(optional)*

Inferred at Step 1. One of `concise | standard | text-heavy`. Controls per-slide word budget when filling content slots at step 2.

**Inference order (highest wins):**
1. Explicit CLI/API flag passed to `/deck`.
2. User text in the brief prompt (e.g. "detailed leave-behind", "exec one-pager").
3. Brand-pack default — `brief_defaults.verbosity` in the active brand's `tokens.json`, read via `load_brief_defaults(brand_dir)` (see `brand-system.md` → Brief defaults).
4. Heuristic (below).

| Value | Budget | When |
|---|---|---|
| `concise` | ~20 words | Exec audience, live-projected deck, high visual-to-text ratio |
| `standard` | ~40 words | Default — most internal decks, team reviews |
| `text-heavy` | ~60 words | Async/leave-behind deck, developer audience, reference material |

If absent, the pipeline defaults to `standard`.

### `delivery` *(optional)*

One of `live | async | both`. Records how the deck will be consumed. `live` → presenter carries the narrative, slides carry visuals. `async` → body text must stand without a speaker. `both` → produce presenter deck first, then expand to leave-behind variant. Inferred from brief context at Step 1. Drives verbosity tier inference and step-4 redundancy-overload checks.

### `delivery_mode` *(optional)*

One of `in-person | virtual | hybrid`. Physical delivery context. `virtual` and `hybrid` trigger the **safe-zone rule**: critical content (headlines, KPIs, CTAs) must sit in the top 60% and centre 80% of the slide canvas. Defaults to `in-person` if absent.

### `image_style` *(optional)*

One of `photorealistic | illustration | abstract | minimal | data-viz | none`. Governs all image and illustration assets across the deck — ensures cross-slide visual style consistency. The Resolver uses this as a search signal when sourcing assets via Unsplash or other providers. Step 4 fires `image-consistency` when image assets visually diverge from the declared style. Inferred from brief context (technical deck → `data-viz`; narrative/human deck → `photorealistic`; minimal brand → `minimal`) or set explicitly by the user at Step 0.

### `slides[]`

One entry per planned slide. `role` comes from the frame's role set (see `narrative-frames.md`); `claim` is the slide's title-in-draft (subject to `slide-claim-test.md`); `audience_fit` is a one-sentence note for step 2's planner.

## Persistence

Written to the working directory at step 1, next to `content_plan.json`. Preserved through step 5 (not mutated on revise). Read by:
- step 2 (planning) — consumes `frame`, `audience`, `slides[].claim`, `slides[].role`.
- step 1b (presentation) — renders the summary block.
- step 4 (verify) — checks `audience-mismatch` against `audience`, `red-line-break` against `frame` + `slides[].role`.
- `/deck critique` mode — reconstructs the brief from an existing `.pptx`, writes the same shape.

## Validation

Every write of `design_brief.json` passes through `skills/deck/lib/design_brief.py::validate_brief()`, which loads the schema and runs `jsonschema.validate()`. Validation errors halt the pipeline — a brief that can't be validated is a broken inference.
