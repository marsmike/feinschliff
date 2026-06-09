---
name: tts
description: Convert text to speech with ElevenLabs voiceover. Use when generating speech audio or browsing available voices.
---

# feinklang — ElevenLabs voiceover

`feinklang` is a command on your PATH — no file paths, no `cd`, no
`${CLAUDE_PLUGIN_ROOT}`. Requires `ELEVENLABS_API_KEY` (an export, or a line in
`~/.env`). Default voice: **Hale**.

## Synthesize speech

```bash
feinklang tts --text "Hello, this is a test." --out voiceover.mp3
```

Options:

- `--voice-id` — voice ID or name (`Hale`, `Mike`, `Lea`), default `Hale`
- `--model-id` — `eleven_multilingual_v2` (default), `eleven_v3`, `eleven_flash_v2_5`
- `--format` — `mp3_44100_128` (default), `mp3_44100_192`, `wav_44100`, `pcm_44100`, `opus_48000_64`
- `--stability` — 0–1 (default 0.5)
- `--similarity-boost` — 0–1 (default 0.75)
- `--speed` — 0.7–1.2 (default 1.0)
- `--play` — play the audio locally after generation
- `--out` — output path; if omitted, a timestamped file is written to the temp
  dir and its path is printed

Write outputs into the project (e.g. a beats directory under
`${CLAUDE_PROJECT_DIR}`) so downstream plugins can consume them.

## Browse voices

```bash
feinklang voices                          # all voices
feinklang voices --category professional  # cloned | professional | premade
feinklang voices --search Mike            # search by name
```

## For other plugins (capability hand-off)

Need a voiceover? Call `feinklang tts --text "…" --out <project-path>` as a
bare command and read the resulting file — for example, loop it per beat to
batch-generate narration. Do **not** reference feinklang's internal files; the
CLI is the entire contract. If `feinklang` is somehow not on PATH, fall back to
asking the user for the audio rather than failing hard.
