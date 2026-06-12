# Editing doctrine — whether, how many, when

Judgment layer for authoring `edit_plan.json`. This doc decides *whether a
moment gets a beat, how many beats a video gets, and how they breathe*.
Which kind a beat gets is [template-picker.md](template-picker.md); for
explanation-heavy stretches run
[concept-visualization.md](concept-visualization.md) first (lands with the
concept-visualization doc; until present, classify explanation stretches with
the picker's shape rows directly). Mechanics and
hard rules live in [SKILL.md](../SKILL.md). Where a number below is
enforced, the lint constant is named — retune in
`src/feinschnitt/edit/lint.py`, never by editing this doc alone.

## 1. The meaning gate

- A beat exists because of one specific claim, noun, or number in
  `words.json` — and its `reason` names it. Lint enforces that `reason` is
  present; you enforce that it is honest. "Adds energy" or "the topic is
  technical" are not reasons; they are the absence of one.
- **Four-word test for image subjects:** the subject must fit in roughly
  four words and be identifiable by a muted viewer in half a second.
  "a padlock", "a whiteboard covered in sticky notes", "a chart climbing"
  pass. "a small figure confronting a huge glowing machine of many moving
  parts" fails — the viewer decodes instead of understands.
- Concrete-and-immediate beats abstract-and-clever, every time. A clever
  metaphor pulls attention away from the speaker to decode itself.
- The visual must match what is spoken INSIDE the beat window. If the phrase
  it illustrates first occurs after `end_sec`, the beat is mistimed: move it
  onto the phrase, or choose a subject that matches the words actually under
  it. Never illustrate a later punchline early — that spends the payoff.

## 2. Density — how many beats, in what mix

Totals include the hook. Heroes = takeovers (`stat_punch`, `quote_pull`,
`static`, `vertical_timeline`); connectives = overlays (`word_pop`,
`image_card`, `ratio_dots`, `inline_chart`).

| Duration | Total beats | Heroes | Distinct hero kinds | Connectives |
|---|---|---|---|---|
| 15–25s | 4–6 | 2–3 | ≥2 | 1–2 |
| 25–45s | 7–9 | 4–5 | ≥3 | 2–3 |
| 45–60s | 9–12 | 5–7 | ≥3 | 3–4 |
| longform >60s | ≥1 per 60s | per chapter | rotate kinds | per chapter |

- Rolling cap at every duration: ≤4 beats in any 12s window (lint warns;
  enforced as `DENSITY_WINDOW`/`DENSITY_CAP`). Above that threshold each
  beat competes with the one before it — none land cleanly.
- ≥3 distinct hero kinds in any 7+ beat plan — a run of the same takeover
  reads as one trick repeated, not an edit.
- **Placement test, per candidate beat:** *who owns this moment — the face
  or the frame?* A visual earns its place only when the line is one of:
  - a **named thing** — a number, product, person, or tool;
  - a **pivot or contrast** — the argument turns here;
  - the **takeaway or CTA** — the line the viewer should keep;
  - an **enumeration** — structure the ear can't hold alone.
- Banned: carpet-bombing every sentence; defaulting to one kind; decoration
  without a semantic reason. A stretch of bare speaker is pacing, not a gap
  to fill.

## 3. Hook doctrine

- Every edit opens on a composed `hook_title`, visible within ~0.5s — the
  scroll decision is made before the first sentence ends. `start_sec: 0.0`,
  never a `speech_anchor` (alignment would push it off frame zero). Lint
  warns when it is missing or late (`HOOK_DEADLINE`; constant value: 0.6s).
- **Kicker carries the setup, title carries the punchline.** Stats, context,
  and framing go in `kicker`; `title` is the short blow — ≤16 characters as
  guidance, because a long title swallows the frame and reads as a
  paragraph, not a punch.
- **Open-loop rule:** any text overlay in the first third POSES the
  question, never prints the conclusion. If the line could serve as the
  video's answer, it belongs in the back half — turn it into the question
  that holds the gap open, and give the payoff its own beat where the
  speaker delivers it. When the speaker's own opening line already states
  the conclusion, the actual-words rule wins (the hook may echo it — the
  speaker already spoiled it); open-loop applies when the payoff lands
  LATER than the hook.
- On-screen hook text uses the speaker's ACTUAL words (SKILL.md hard
  rule 4). The hook and the audio must never show two different words for
  the same idea — the viewer hears one and reads the other.

## 4. Dwell + rhythm

- **Alignment owns timing.** The `speech_anchor` snaps `start_sec`;
  `end_sec` is only ever EXTENDED, never shortened; `quote_pull`'s
  typewriter speed and post-typing dwell are computed from the spoken span
  (`QUOTE_DWELL_MIN` in `align.py`). Do not inflate `end_sec` to "make sure
  it stays up" — author the honest window and let the pipeline do the math.
- A beat ends before the speaker pivots topics. A visual lingering into the
  next idea is semantic noise: the screen argues one thing while the voice
  argues another.
- Image beats need ≥1.5s of pure speaker between them (lint warns;
  `IMAGE_BREATH`). Back-to-back images read as a slideshow; a speaker gap
  between them closes the previous beat and lets the next one open fresh.
- **Reading time is math, not feel.** For text takeovers
  (`READING_TIME_KINDS`: `stat_punch`, `quote_pull`) lint warns in both
  directions around `max(3.5s, chars/12 + 1.5s)` (`READ_FLOOR`/`READ_CPS`/
  `READ_DWELL`); `vertical_timeline` is exempt (per-step pacing governs it
  instead). Trust the warning over your gut: too short and the viewer can't
  finish reading; too long and the frame goes dead.

## 5. Endings

- The close is a strong CTA or a loop back into the opening frame — never a
  soft trail-off. The last second should land with the same intent as the
  first.
- The LAST caption-emphasis phrase is silent by design: the score suppresses
  its SFX, so marking the closer as emphasis gives it typographic weight
  with no sting under it. Use that — closers want silence.
- The closing beat earns accent treatment. It is the one late moment that
  may lean on the brand accent (an accent-flagged `word_pop` item or a
  `{...}` span) as its anchor.

## 6. Accent discipline

- **One accent element per frame.** Two accents split the eye and both
  lose.
- Every template already declares its own accent internally (the dots'
  marked state, the chart's leading edge, the hook's rule). Never author a
  plan that needs two accent moments at once — e.g. an accent-flagged
  `word_pop` overlapping a `ratio_dots` beat at its `mark_at`.
- Stay brand-agnostic: plans and reasons never name colors. "The accent"
  and "the brand's display face" resolve per brand pack at render time.
