# Overlays & Hard Rules — edit

## Hard rules

1. **Every beat needs a `reason`** — one sentence naming the specific claim/noun
   from the transcript this visual serves. "General vibes" → drop the beat. Lint
   enforces presence; the author enforces honesty.

2. **Every beat needs a `speech_anchor`** — the exact phrase the speaker says when
   the visual should appear. Copy verbatim from `words.json` (multi-word, not from
   memory). Alignment snaps timing to the anchor; it may EXTEND `end_sec`, never
   shorten it. Exception: the opening `hook_title` has NO anchor (must sit at
   `start_sec: 0.0`).

3. **`appear_sec` is absolute source-video seconds** — copy timestamps straight out
   of `words.json`. Every `word_pop` item carries its own `appear_sec` so each word
   lands as spoken.

4. **On-screen text uses the speaker's ACTUAL words** — grep `words.json` for the
   phrasing; never paraphrase what the audio says.

5. **Preview-first, always.** Never run `--quality final` until the user has
   explicitly approved a preview in this conversation.

6. **One render at a time.** Never launch parallel renders; for batches write one
   sequential loop. The render lock is a backstop, not the pacing mechanism.

7. **Never edit derived files by hand** — `edit_plan.aligned.json`, `props.*.json`,
   and anything else in the workdir are derived. The authored `edit_plan.json` is
   the only file to write. (Exception: `zoom_plan.json` in the workdir is generated
   once and may be hand-tuned afterwards.)

8. **Text placement:** `word_pop` default `vertical` 0.72, `hook_title` 0.66 —
   lower third, never over the face (`inline_chart` card top defaults to 0.62).
   Lint errors below 0.58 and above 0.9 (`inline_chart`: above 0.74 — the 26%-tall
   card would clip).

9. **When a transcription mishearing surfaces** (brand names especially), the
   durable fix is a new entry in the corrections module — never a hand-edit of
   `words.json`. Tell the user the correction was added.

10. **Takeovers replace the frame; overlays share it.** Consecutive takeovers get an
    automatic coverage underlay (no speaker flicker); never author two image beats
    back-to-back without ≥1.5 s of speaker between them.

## Caption rules

Word-synced captions are generated from `words.json` and on by default. The plan
may only configure them — **never author chunk text**:

```json
"captions": {"enabled": true, "emphasis": ["exact phrase"]}
```

- **Emphasis phrases** are copied verbatim from `words.json` (multi-word, same rule
  as anchors); matched words render accent + heavy weight. Unmatched phrases surface
  as `captions warning:` lines — fix the wording, don't guess.
- **Suppression:** takeovers and lower-third text overlays (`word_pop`, `hook_title`)
  silence captions for their whole window; visual overlays (`image_card`,
  `ratio_dots`, `inline_chart`) keep them unless the chunk shares a meaningful word
  with the beat's text. A ±0.8 s echo pad around every beat drops chunks sharing
  meaningful words with it.
- **Known gap (digit vs word):** "Nine" vs `9 OF 12 FAILED` don't token-match — a
  brief "NINE OF MY" chunk may render under the dots (near-duplication, not overlap;
  "12"/"failed" ARE echo-dropped).

## Image discipline

- **Sourcing priority:** (1) real screenshot / product UI, (2) stock photo,
  (3) generated via `feinbild imagine` with a brand-prefixed prompt — generation
  is the last resort, for abstract concepts only.
- **ONE locked generation style per video.** On the first generation, save the exact
  prompt template to `<workdir>/style.txt` and reuse it verbatim for every further
  generated image in the same video — no style drift.
- **`image_card` is the b-roll default** (speaker stays visible); `static` is
  reserved for hero moments that deserve the full frame.
- **≥1.5 s of speaker breathing room between image beats** — back-to-back images
  read as a slideshow (lint warns).
- **Every `image_path` needs a file extension** — the engine cannot infer a MIME
  type without one (lint errors).
