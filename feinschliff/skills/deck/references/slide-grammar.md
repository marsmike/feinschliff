# Slide Grammar — Adjacency and Sequencing Theory

Why slide order is not arbitrary, and what the picker enforces automatically.

---

## 1. Why adjacency matters

A deck is a sequence, not a collection. Three failure modes appear only at the
transition between slides — they are invisible if you review each slide in
isolation:

**Reader rhythm** — the eye fatigues on sameness. Two consecutive full-bleed
visuals feel like a stutter; two consecutive data tables feel like a report
fragment rather than an argument. Alternating visual weight (dense → airy →
dense) keeps the audience tracking without conscious effort.

**Argument logic** — some slide types are only coherent in certain positions.
A recommendations slide that appears before any complication has been
established is a non-sequitur; a key-takeaways slide that opens a section has
nothing to synthesize. The narrative arc sets the valid positions; the
adjacency rules enforce them locally.

**Credibility** — sequencing errors are legible to experienced audiences even
when they can't name them. A recommendation that follows another recommendation
reads as repetition; a chapter opener immediately after another chapter opener
signals structural confusion. The deck's authority depends on sequencing that
mirrors how confident thinkers build arguments.

---

## 2. Narrative-act ordering (SCQA / Pyramid Principle)

The `narrative_act` field on each slide (one of `situation`, `complication`,
`resolution`) captures its position in the argument arc. The storyline gate
(pipeline step 1c) assigns this field; the adjacency rules in section 5 score
against it at pick time.

**Ordering rules:**

1. **No situation → resolution without an intervening complication.** A
   situation followed directly by a resolution omits the "why act" — the
   audience has no reason to accept the recommendation because they haven't
   been shown the problem. At minimum one complication slide must appear
   between them.

2. **No complication immediately after resolution (backsliding).** Once the
   argument has delivered a resolution, returning to a complication reopens a
   wound the deck appeared to close. Exception: the Sparkline frame
   intentionally oscillates complication / resolution pairs as a rhetorical
   device — in that frame, alternation is the structure. Outside Sparkline,
   treat complication-after-resolution as a sequencing defect.

3. **SCQA places the recommendation after context + complication.** The Minto
   Pyramid Principle (SCQA) builds to the answer: Situation → Complication →
   Question → Answer (recommendation). The recommendation is the culmination.
   Evidence and support slides follow it. Use SCQA when the audience needs
   context before they can evaluate the recommendation (middle-management
   audiences, unfamiliar topics, politically sensitive changes).

4. **Pyramid Principle leads with the answer.** The stricter Pyramid variant
   — used for executive audiences with tight time budgets — inverts the SCQA
   order: recommendation first, then the complications and evidence that
   justify it. The audience can leave after slide 3 and still know the
   conclusion. Evidence slides follow the recommendation; complication slides
   appear as justification, not premise.

5. **Key-takeaways synthesizes; it never opens.** A key-takeaways slide
   compresses the section's conclusions into 2–4 points. Those points only
   have meaning after the evidence slides have run. Placing key-takeaways
   before the content it summarizes is a structural inversion — equivalent to
   printing a conclusion before the argument.

The two frames — SCQA (bottom-up) and Pyramid (top-down) — are not
contradictory. They serve different audience patience levels. The sequencing
rules above apply in both; only the placement of the recommendation differs.
See `narrative-frames.md` for full frame descriptions.

---

## 3. Structural conventions

These rules govern the deck-level positions of the four fixed structural roles
(`title-primary`, `agenda`, `chapter-opener`, `closer`). They are independent
of narrative act.

**Cover / title slide** — always slide 1. Never internal. The cover is not a
chapter opener; do not substitute a chapter opener for a missing cover.

**Agenda** — immediately after the cover (slide 2), or at the very start of an
appendix section. An agenda mid-deck disorients the audience — it signals "the
real deck starts here" and implicitly demotes everything before it to
preamble. A second agenda is acceptable only when a long deck has a major
appendix break (the appendix agenda orients the reader to a new scope). Agenda
slides never follow content slides.

**Chapter openers** — one per section boundary, between runs of 3 or more
content slides. Two consecutive chapter openers signal an empty section: the
first opener has no content, so the second opener immediately replaces it.
This is always a sequencing error; either add content to the first section or
merge the two chapters. Chapter openers do not appear at the deck's end (the
`closer` role owns that position).

**Executive summary** — opens a deck or ends a section as a synthesis. It
never appears mid-section. An executive summary inside a content run is a
key-takeaways misclassification — use key-takeaways for mid-section synthesis
and reserve executive-summary for deck-level framing.

**Closer / next-steps** — last substantive slide before the appendix. Do not
follow a closer with a content slide; that slide belongs in the main body.

---

## 4. Rhythm rules (visual variety)

Adjacency rules for visual weight, independent of narrative act or deck
structure:

**No two consecutive full-bleed visual layouts.** Full-bleed layouts (cover,
chapter openers, quote, full-bleed image) are high-impact moments that derive
their weight from contrast with surrounding content slides. Back-to-back
full-bleed slides cancel each other; the second feels like a stutter rather
than a new beat.

**Quote slides are breath-points.** A quote slide slows the pace, shifts the
voice, and resets audience attention. Chaining two quote slides drains that
effect — the audience normalises to the slow pace and attention drops rather
than resets. Place quote slides singly, with content slides on both sides.

**Action-title immediately precedes its supporting evidence.** The action-title
layout (`role: title-primary`) carries the so-what for what follows. If the
supporting evidence (data, chart, or content slides) does not immediately
follow, the connection dissolves. An action-title at the deck's end, with
nothing following it, is an orphaned claim — move it to be a section-level
synthesis (key-takeaways) or restructure the section so evidence precedes it.

**Layout-monotony threshold: 3.** Three or more consecutive slides using the
same layout triggers defect #11 (`layout-monotony`) in the verify pass. The
picker's `layout_history` recency penalty prevents most monotony at plan time;
the verify check catches edge cases where the planner overrides or pins
layouts. See `anti-patterns.md` #11.

---

## 5. Seeded adjacency rules

The picker evaluates `follows_not` and `follows_well` frontmatter on each
candidate layout against the **predecessor slide's signals** (the slot in
`layout_history` most recently written). The predecessor's signals include its
`role`, `narrative_act`, and `layout` (the chosen layout ID).

**Syntax:** each entry is a `signal=value` predicate matched against the
predecessor. `layout=<id>` matches the predecessor's chosen layout ID exactly.
`role=<value>` and `narrative_act=<value>` match the predecessor's content
signals.

**Scoring:** `follows_not` hit → −1.5 per predicate (additive). `follows_well`
hit → +0.75 per predicate (additive). These adjustments are soft: they shift
rank but never hard-block a layout. A pinned layout (user or plan explicitly
names it) bypasses the picker entirely and is not penalised.

The table below documents the seven layouts receiving seeded adjacency rules in
this release. The "rationale" column states the theory from sections 2–4 that
motivates each rule.

| Layout | `follows_not` | `follows_well` | Rationale |
|---|---|---|---|
| `recommendation` | `role=title-primary`, `role=agenda`, `role=chapter-opener` | `role=content-columns`, `narrative_act=complication` | Recommendation must not open a section cold; it lands after evidence or complication establishes the need. |
| `next-steps` (role: `closer`) | `role=title-primary`, `role=agenda`, `narrative_act=situation` | `layout=recommendation`, `narrative_act=resolution` | Next-steps closes a resolved argument; it reads as non-sequitur after opening or structural slides, and flows naturally from a recommendation. |
| `agenda` | `role=content-columns`, `role=data-quantity`, `role=data-comparison`, `role=closer` | `role=title-primary` | Agenda follows the cover; a mid-deck agenda after content signals a broken structure. |
| `chapter-orange` / `chapter-ink` (role: `chapter-opener`) | `role=chapter-opener` | `role=agenda`, `role=closer`, `role=content-columns` | Back-to-back chapter openers signal an empty section; a chapter opener flows from the prior section's close or the agenda. |
| `key-takeaways` (role: `closer`) | `role=title-primary`, `role=agenda`, `role=chapter-opener` | `role=content-columns`, `role=data-quantity`, `narrative_act=complication` | Key-takeaways synthesizes; it must not open a section before there is anything to synthesize. |
| `action-title` (role: `title-primary`) | `role=closer`, `role=title-primary` | `role=content-columns`, `role=data-comparison`, `role=data-quantity` | Action-title is a so-what that introduces evidence; it must not follow a close (nothing to introduce) or another action-title (two orphaned claims). |

**Role enum values** (from `layout_picker.py` docstring): `title-primary`,
`title-with-visual`, `chapter-opener`, `agenda`, `data-quantity`,
`data-comparison`, `data-timeline`, `content-columns`, `content-with-visual`,
`quote`, `reference`, `closer`.

**Corrections applied to the table above vs. the task brief:**
- `recommendation` layout's real `role` is `content-columns` (frontmatter:
  `role: content-columns`), not a distinct `role=recommendation`. The
  `follows_not` / `follows_well` predicates in the table use the predecessor's
  role, so they remain valid regardless of the recommendation layout's own
  role.
- `next-steps` layout's real `role` is `closer` (not a distinct role), noted
  parenthetically.
- `key-takeaways` layout's real `role` is `closer`, noted parenthetically.
- `action-title` layout's real `role` is `title-primary`, noted
  parenthetically.

---

## 6. Relationship to the picker and verify

The adjacency rules in section 5 are **soft signals at pick time** (layout
selection, pipeline step 2) and **hard checks at verify time** (pipeline
step 4) for the structural conventions in section 3.

At pick time: the picker adds `follows_not` / `follows_well` scores to the
affinity score for each candidate layout. This biases the default pick toward
well-sequenced transitions without blocking planner intent.

At verify time: the `red-line-break` defect class (defect #5 in
`anti-patterns.md`) catches structural role violations. The `narrative-arc-missing`
verify class (defect #20 in `iteration-loop.md`) catches broken `narrative_act`
sequences.

For authoring frontmatter on new layouts, write `follows_not` / `follows_well`
as a YAML list under the layout's frontmatter fence, using the `signal=value`
syntax. Example:

```yaml
---
role: content-columns
follows_not:
  - role=closer
  - role=agenda
follows_well:
  - narrative_act=complication
---
```

Cross-references: `anti-patterns.md` #5 (red-line-break), #11
(layout-monotony) · `narrative-frames.md` (full frame descriptions) ·
`pipeline.md` step 1c (storyline gate that assigns `narrative_act`).
