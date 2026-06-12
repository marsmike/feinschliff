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
   `skills/edit/schema/edit-plan.schema.json`. M1 kinds: `hook_title`,
   `word_pop`, `stat_punch`.
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
   lower third, never over the face. Lint errors below 0.58 and above 0.9.
9. **When a transcription mishearing surfaces** (brand names especially), the
   durable fix is a new entry in `src/feinschnitt/edit/corrections.py` — never a
   hand-edit of `words.json`. Tell the user you added it.

## Output contract

- Preview: `<video stem>.preview.mp4` next to the source.
- Final: `<video stem>.enhanced.mp4` next to the source — voice track is
  bit-identical to the input (verify enforces this).
