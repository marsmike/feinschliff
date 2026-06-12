---
name: edit
description: Edit a pre-recorded talking-head video into a finished, brand-themed cut — overlay beats timed to the spoken words, speaker zoom punch-ins, preview/final render ladder. TRIGGER when the user provides recorded footage and asks to edit/enhance/caption it.
---

# Edit — pre-recorded footage pipeline

Takes a finished recording (the user's voice and cut are untouched) and adds
a planned layer of visuals. You author **data** (`edit_plan.json`), never
React code — the shared engine in `edit-engine/` renders it.

## Workflow

1. **Probe** — `ffprobe` aspect + duration (portrait <30s = short; landscape = intro/longform).
2. **Transcribe** — `feinschnitt edit transcribe <video>` → `words.json` in the workdir
   (`feinschnitt edit workdir <video>` prints the path). Read it; it is the timing
   source of truth.
3. **Author the plan** — write `edit_plan.json` next to the video. Schema:
   `skills/edit/schema/edit-plan.schema.json`. The template library:

   | kind | class | required fields | use for / NOT for |
   |---|---|---|---|
   | hook_title | overlay | title | cold-open lockup at 0.0s / never mid-video |
   | word_pop | overlay | items[text+appear_sec] | enumerations + emphasis lines / not card-styled lists |
   | stat_punch | takeover | value, caption | THE hero number / not for every number mentioned |
   | quote_pull | takeover | quote_text | the takeaway line; anchor must cover the spoken quote (cps + 2s dwell are computed) / not for the speaker's own passing remarks |
   | static | takeover, image | image_path | hero screenshots/photos shown full-frame (contain, never cropped) / not the default for b-roll |
   | image_card | overlay, image | image_path | DEFAULT for b-roll images — speaker stays visible / not for text-heavy screenshots that need full-frame |
   | vertical_timeline | takeover, sequence | steps[heading+appear_sec] | 3-6 ordered steps narrated one by one (rail reveals each on its word) / not for unordered lists |
   | ratio_dots | overlay | total, marked, polarity, mark_at | any spoken "X of Y" (≤25 dots reads best) / not for percentages of unstated totals |
   | inline_chart | overlay | title, data | trends/distributions the speaker describes / not for single numbers |
4. **Lint** — `feinschnitt edit lint <video> <plan>`. Fix every error; read every warning.
5. **Preview** — `feinschnitt edit render <video> <plan>` (preview is the default
   quality). Report the output path to the user and STOP.
6. **Final** — ONLY after the user approves the preview:
   `feinschnitt edit render <video> <plan> --quality final --brand <brand-dir>`.

## Hard rules

1. **Every beat needs a `reason`** — one sentence naming the specific claim/noun
   from the transcript this visual serves. "General vibes" = drop the beat. Lint
   enforces presence; you enforce honesty.
2. **Every beat needs a `speech_anchor`** — the exact phrase the speaker says when
   the visual should appear. Copy the wording verbatim from `words.json` (multi-word,
   not from memory). Alignment snaps timing to the anchor; it may EXTEND your
   `end_sec`, never shorten it. Exception: the opening `hook_title` has NO anchor
   (it must sit at `start_sec: 0.0`).
3. **`appear_sec` is absolute source-video seconds** — copy timestamps straight
   out of `words.json`. Every `word_pop` item carries its own `appear_sec` so
   each word lands as it is spoken.
4. **On-screen text uses the speaker's ACTUAL words** — grep `words.json` for the
   phrasing; never paraphrase what the audio says.
5. **Preview-first, always.** Never run `--quality final` until the user has
   explicitly approved a preview in this conversation.
6. **One render at a time.** Never launch parallel renders; for batches write one
   sequential loop. The render lock is a backstop, not the pacing mechanism.
7. **Never edit `edit_plan.aligned.json`, `props.*.json`, or anything in the
   workdir by hand** — they are derived. The authored `edit_plan.json` is the
   only file you write. (One exception: `zoom_plan.json` in the workdir is
   generated once and may be hand-tuned afterwards.)
8. **Text placement:** `word_pop` default `vertical` 0.72, `hook_title` 0.66 —
   lower third, never over the face (`inline_chart` card top defaults to 0.62).
   Lint errors below 0.58 and above 0.9 (`inline_chart`: above 0.74 — the
   26%-tall card would clip).
9. **When a transcription mishearing surfaces** (brand names especially), the
   durable fix is a new entry in `src/feinschnitt/edit/corrections.py` — never a
   hand-edit of `words.json`. Tell the user you added it.
10. **Takeovers replace the frame; overlays share it.** Consecutive takeovers
    get an automatic coverage underlay (no speaker flicker); never author two
    image beats back-to-back without ≥1.5s of speaker between them.

## Image discipline

- **Sourcing priority:** (1) a real screenshot / product UI, (2) a stock
  photo, (3) generated via `feinbild imagine` with a brand-prefixed prompt —
  generation is the last resort, for abstract concepts only.
- **ONE locked generation style per video.** On the first generation, save
  the exact prompt template to `<workdir>/style.txt` and reuse it verbatim
  for every further generated image in the same video — no style drift.
- **`image_card` is the b-roll default** (the speaker stays visible);
  `static` is reserved for hero moments that deserve the full frame.
- **≥1.5s of speaker breathing room between image beats** — back-to-back
  images read as a slideshow (lint warns).
- **Every `image_path` needs a file extension** — the engine cannot infer a
  MIME type without one (lint errors).

## Captions

Word-synced captions are generated from `words.json` and on by default. The
plan may only configure them — **never author chunk text**:

```json
"captions": {"enabled": true, "emphasis": ["exact workflow"]}
```

- **Emphasis phrases** are copied verbatim from `words.json` (multi-word, same
  rule as anchors); matched words render accent + heavy weight. Unmatched
  phrases surface as `captions warning:` lines — fix the wording, don't guess.
- **Suppression:** takeovers and the lower-third text overlays (`word_pop`,
  `hook_title`) silence captions for their whole window; visual overlays
  (`image_card`, `ratio_dots`, `inline_chart`) keep them unless the chunk
  shares a meaningful word with the beat's text. A ±0.8s echo pad around every
  beat drops chunks sharing meaningful words with it.
- **Known gap (digit vs word):** "Nine" spoken vs a `9 OF 12 FAILED` caption
  don't token-match, so a brief "NINE OF MY" chunk renders under the dots —
  near-duplication, not overlap ("12"/"failed" chunks ARE echo-dropped).

## Output contract

- Preview: `<video stem>.preview.mp4` next to the source.
- Final: `<video stem>.enhanced.mp4` next to the source — voice track is
  bit-identical to the input (verify enforces this).
