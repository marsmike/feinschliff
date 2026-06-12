# Template picker — what the speaker is doing → which kind

Operational lookup for step 3 of [SKILL.md](../SKILL.md). Walk `words.json`
top to bottom; at each candidate moment, ask what the speaker is DOING;
the matching row gives the kind. Whether the moment deserves a beat at all is the
placement test in [editing-doctrine.md](editing-doctrine.md) §2; for
explanation-heavy stretches run
[concept-visualization.md](concept-visualization.md) BEFORE this table — it
catches teaching moments this table would under-serve with a text card.

## The table

| Speaker is doing | kind | class | Required fields | Do NOT use when |
|---|---|---|---|---|
| Opening the video (always) | `hook_title` | overlay | `title` (+`kicker` for setup/stats) | anywhere past the cold open; never give it a `speech_anchor` — it sits at 0.0s |
| Landing an emphasis line, or rapid-firing short phrases | `word_pop` | overlay | `items[]`, each `text` + `appear_sec` | the phrases are ordered steps with substance (timeline); a bare opinion the face already carries |
| Dropping THE hero number | `stat_punch` | takeover | `value`, `caption` | every number mentioned; numbers that are really an X-of-Y (dots) or a trend (chart) |
| Saying the quotable takeaway line | `quote_pull` | takeover | `quote_text` + anchor covering the spoken quote | passing remarks; more than ~1 per short — a second quote dilutes the first |
| Showing a hero screenshot/photo that IS the moment | `static` | takeover | `image_path` (with extension) | default b-roll (that's `image_card`); when the speaker should stay visible |
| Referencing something an image supports while they keep talking | `image_card` | overlay | `image_path` (with extension) | text-dense screenshots that need the full frame (`static`) |
| Walking through 3–6 ordered steps, one by one | `vertical_timeline` | takeover | `steps[]`, each `heading` + `appear_sec` | unordered lists; >6 steps (lint warns — split instead) |
| Stating an "X of Y" ratio | `ratio_dots` | overlay | `total`, `marked`, `polarity`, `mark_at` | percentages with no stated total; totals >25 read small (lint warns), >100 errors |
| Describing a trend or distribution over time | `inline_chart` | overlay | `title`, `data` (≥2 points) | a single number; data the speaker never stated — never fabricate points |
| Asserting an opinion / emotional read / the face carries it | **no beat** | — | — | always: "I think this is huge" gets nothing — captions cover it, the speaker is the show |

Tie-breakers when two rows fit:

- A number inside an X-of-Y → `ratio_dots` outranks `stat_punch`; inside a
  trend → `inline_chart` outranks it. The hero number stands alone.
- Ordered steps narrated with substance → `vertical_timeline`; rapid-fire
  labels with no substance per item → `word_pop`.
- An image while the speaker keeps talking → `image_card`; an image that IS
  the moment → `static`.
- Per-item timing is mandatory either way: every `appear_sec` is absolute
  source-video seconds copied from `words.json` (SKILL.md hard rule 3), so
  each item lands as the speaker says it — never dumped at beat start.

## Class consequences — what overlay vs takeover commits you to

Picking the kind also picks its class, and the class has rules:

- **Takeovers** replace the frame. The first takeover may not start before
  1.5s of speaker face-time (lint errors; `FIRST_TAKEOVER_FLOOR` — overlays
  are exempt, which is why the hook can sit at 0.0s). Consecutive takeovers
  get an automatic coverage underlay, so never plan around the speaker
  "flashing through" between them. Captions are suppressed for the whole
  takeover window — the takeover's own text carries the moment.
- **Overlays** share the frame with the speaker. Text overlays
  (`hook_title`, `word_pop`) live in the lower third — `vertical` defaults
  are safe, and lint errors below 0.58 (never over the face). Text overlays
  also suppress captions; the visual overlays (`image_card`, `ratio_dots`,
  `inline_chart`) keep captions running unless a chunk echoes the beat's
  own words (see SKILL.md Captions).
- Class is fixed per kind — there is no flag to flip an overlay into a
  takeover. If the moment needs the full frame, pick a takeover kind.

## Worked classification — one transcript stretch

"So I ran this on fourteen videos. Eleven of them failed. The three that
worked all did one thing: they cut the intro. First you trim the silence,
then you drop the filler, then you tighten the gaps. I think that's huge."

1. "fourteen videos… eleven failed" → spoken X-of-Y → `ratio_dots`
   (total 14, marked 11, `polarity: "negative"`, `mark_at` on "failed").
2. "the three that worked all did one thing" → setup, the face carries the
   reveal → no beat; captions cover it.
3. "first… then… then…" → 3 ordered steps narrated one by one →
   `vertical_timeline`, one step per spoken step, `appear_sec` from
   `words.json`.
4. "I think that's huge" → bare opinion → **no beat**.

## Density-conflict drop order

When the rolling cap trips (lint: `DENSITY_WINDOW`/`DENSITY_CAP` — ≤4 beats
per 12s window), drop in this order until the warning clears:

1. **Decorative images** — the `image_card`/`static` whose `reason` is the
   weakest under the meaning gate (doctrine §1).
2. **Repeated kinds** — the second of two same-kind beats in the stretch;
   variety carries more than repetition.
3. **Connectives** — overlay garnish (`word_pop` emphasis lines first).

Never drop the `hook_title` or the takeaway `quote_pull` — they are the
spine of the edit. If the conflict involves them, move or trim a neighbor
instead.

## Image sourcing

Before authoring any `image_card`/`static` beat, apply SKILL.md "Image
discipline" in full: real screenshot > stock > generated (last resort,
brand-prefixed prompt, ONE locked style per video via `style.txt`). Image
beats also carry the strongest rhythm constraint — ≥1.5s of speaker between
them (doctrine §4; lint `IMAGE_BREATH`) — so budget image beats sparingly
before the density table fills up.
