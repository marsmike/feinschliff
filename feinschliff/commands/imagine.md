---
name: imagine
description: "Generate an image from a text prompt using AI. Usage: /imagine <prompt> [--provider replicate|gemini] [--model <model>] [--aspect <ratio>]"
user_invocable: true
---

# /imagine

Generate an image from a text prompt using AI image generation.

## Instructions

1. Take the user's prompt text and any flags provided.
2. Call the imagine script with the appropriate JSON parameters:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/imagine/scripts/imagine.sh '<json>'
```

**JSON parameters:**
- `prompt` (required) — the image description
- `provider` — `replicate` (default) or `gemini`
- `model` — provider-specific model (see defaults below)
- `aspect_ratio` — e.g. `1:1`, `16:9`, `9:16`, `4:3`, `3:2`
- `output` — output file path (default: auto-generated in /tmp)

**Default models per provider:**
- replicate: `black-forest-labs/flux-schnell` (fastest, $0.003/img)
- gemini: `gemini-2.5-flash-image` (free tier, fast)

3. After generation, show the user the generated image file path.

**Examples:**

```bash
${CLAUDE_PLUGIN_ROOT}/skills/imagine/scripts/imagine.sh '{"prompt": "a cat astronaut"}'
${CLAUDE_PLUGIN_ROOT}/skills/imagine/scripts/imagine.sh '{"prompt": "sunset over mountains", "provider": "gemini"}'
```

If no prompt is provided, ask what they'd like to generate.
