---
name: tts
description: "Convert text to speech using ElevenLabs and optionally play it. Usage: /tts <text>"
user_invocable: true
---

# /tts

Convert the user's text to speech with the `feinklang` CLI.

## Instructions

Run (substituting the user's text):

```bash
feinklang tts --text "<user text>" --out "${CLAUDE_PROJECT_DIR:-.}/voiceover.mp3"
```

Pass through any options the user provides (`--voice-id`, `--model-id`,
`--speed`, `--format`, `--play`, `--out`). If no text is given, ask what to
speak. `feinklang` is on PATH — call it as a bare command; never use a file
path. If `ELEVENLABS_API_KEY` is unset the command prints a clear error with a
link to obtain a key.
