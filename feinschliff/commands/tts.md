---
name: tts
description: "Convert text to speech using ElevenLabs and play it. Usage: /tts <text>"
user_invocable: true
---

# /tts

Convert the provided text to speech using ElevenLabs TTS and play it.

## Instructions

Take the user's input text and call the elevenlabs skill:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/tts.sh '{"text": "<user text here>"}'
```

If the user provides additional options (voice_id, model_id, speed, output), include them in the JSON.
If no text is provided, ask what they'd like spoken.
