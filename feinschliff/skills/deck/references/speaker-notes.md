# speaker-notes — what to write per slide

Per-slide `notes` is a deliverable, not a debug field. The presenter
reads it while the slide is up; an absent or noisy `notes` field
weakens the live delivery just like a bad title weakens the page.

This reference is for the **writer step** (step 2 / step 4a of
[`pipeline.md`](pipeline.md)). When you produce `content_plan.json`
or fill the per-slide `content` dict of a `plan.yaml`, also fill
each slide's `notes` field, with the rules below.

## What notes are for

Notes are **listener cues** — what the presenter says while that
slide is up. They are *not* on-slide prose. The slide carries the
claim and the proof; the notes carry the spoken delivery.

Concretely:

- **Bullet points are encouraged.** The presenter scans them; they
  are reminders, not paragraphs. Numbered lists are fine for
  ordered talking points; dashes / dots for unordered ones.
- **Core knowledge points are the unit.** Each bullet is one thing
  the audience needs to grasp while looking at this slide — a
  number, a name, a relationship, a contrast.
- **Notes are out-of-band with the slide.** They never appear in
  the visual. Nothing on the slide should depend on the notes
  being present.

## The hook slide carries the storyline

Index-0 (role: `hook`) is the exception. Its `notes` field carries
the **deck's full storyline arc** — the prose articulation of
`design_brief.red_line`. The presenter walks through it once at the
start so the audience is oriented; subsequent slides expand
individual beats.

A good hook-slide notes block:

- States the deck's `takeaway` in one sentence (top of the pyramid).
- Names the arc: situation → complication → resolution (or whatever
  the `frame` is) in 3–5 beats matching the `red_line`.
- Closes with the transition into slide 1.

Example (sparkline frame, exec audience):

> Storyline: pain → demo → results → what this unlocks.
>
> Five years ago a polished deck took a week of cycles between
> writer, designer, and reviewer. Today the same deck takes 15
> minutes. We'll show the loop end-to-end, then the numbers from
> the last quarter of usage, then where this opens new ground.
>
> Hand off to the live demo at 0:45.

## Per-slide notes (every other slide)

Notes for slides 1..N support that slide's `claim`. They:

- Restate the claim in spoken form (1 short sentence), so the
  presenter has it cued up if they freeze.
- List 2–4 talking points the presenter walks through.
- Optionally include a transition cue ("…then to slide N+1: …").

Length is bounded by `design_brief.verbosity`:

| verbosity | per-slide notes budget (rough) |
|-----------|-------------------------------|
| concise   | ≤ 40 words / ≤ 4 bullets       |
| standard  | ≤ 80 words / ≤ 5 bullets       |
| text-heavy| ≤ 160 words / ≤ 6 bullets      |

The hook slide is exempt from this budget — its job is the full
storyline (up to the schema ceiling of 2000 chars).

## Anti-patterns

- **On-slide repetition.** Notes that duplicate the slide's body
  text are dead weight. If the slide says "Revenue grew 12%", the
  notes shouldn't open with "Revenue grew 12%" — they should say
  *why*, what's downstream, what objection to expect.
- **Off-arc tangents.** Notes that wander off `red_line` confuse
  the presenter and the audience. Every slide's notes must support
  the deck's arc; if you want to make a point that doesn't fit,
  the slide itself is wrong.
- **Slide-as-script.** Notes are not the spoken text verbatim.
  Bullets, not paragraphs. The presenter brings the voice; the
  notes bring the reminders.
- **Notes-only content.** If a fact only appears in the notes and
  not on the slide, the slide is missing its proof. Either add it
  to the slide or cut it.

## How notes flow through the pipeline

1. **Step 1 (design brief)** — `design_brief.json` may seed each
   slide's `notes` field. Optional; the writer step fills any gaps.
2. **Step 2 (writer)** — populates `notes` on every slide entry,
   per the rules above. Length-checked against the verbosity table.
3. **Step 3 (build)** — `plan.yaml` carries `notes:` on each slide;
   `feinschliff deck build` threads it into the PPTX speaker-notes
   pane. See `cli/deck.py:cmd_build`.
4. **Step 4 (verify)** — the red_line coherence verifier judges
   whether the notes track the deck's `red_line`. Structural lint
   (separately) checks length + hook-slide presence.

## Quick checklist (writer)

- [ ] Hook slide notes articulate the full `red_line` arc.
- [ ] Every other slide's notes restate its `claim` + 2–4 bullets.
- [ ] No notes block duplicates its slide's body text.
- [ ] No notes block runs off the deck's arc.
- [ ] Per-slide length within the verbosity budget; hook ≤ 2000 chars.
