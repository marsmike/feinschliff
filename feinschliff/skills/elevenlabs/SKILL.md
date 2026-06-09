---
name: elevenlabs
description: Convert text to speech with ElevenLabs. Use when generating speech audio or browsing voices.
---

# ElevenLabs Text-to-Speech

Requires `ELEVENLABS_API_KEY`. Default voice: Hale (`wWWn96OtTHu1sn8SRGEr`).

## Quick Start

```bash
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/tts.sh '{"text": "Hello, this is a test."}'
```

## Modes

### Speak (default)

Generate speech audio from text. See `references/parameters.md` for full JSON options.

```bash
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/tts.sh '<json>'
```

Key parameters: `text` (required), `voice_id`, `model_id`, `output`, `play`.

### Voices

List or search available ElevenLabs voices to find voice IDs.

```bash
# List all voices
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/voices.sh

# Filter by category (cloned, professional, premade)
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/voices.sh professional

# Search by name
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/voices.sh search "Mike"
```
