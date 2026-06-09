---
name: imagine
description: Generate images from text prompts with AI - Use when creating images, memes, or illustrations from descriptions
---

# AI Image Generation

Generate images from text prompts using multiple AI providers.

Requires API keys in `~/.env`: `REPLICATE_API_KEY`, `GEMINI_API_KEY`.

## Quick Start

```bash
${CLAUDE_PLUGIN_ROOT}/skills/imagine/scripts/imagine.sh '{"prompt": "a happy robot painting"}'
```

## Parameters (JSON)

- `prompt` (required) — text description
- `provider` — `replicate` (default), `gemini`
- `model` — provider-specific model (see `references/providers.md`)
- `aspect_ratio` — `1:1` (default), `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`
- `output` — output file path (default: `/tmp/imagine_<timestamp>.webp`)

## Providers

- **Replicate** (default) — Flux models, fast, best text rendering for memes
- **Gemini** — free tier (500/day), great general quality

Full model list, selection guide, and examples: `references/providers.md`

## Brand Design Systems

For images in the visual style of specific companies (Apple, Linear, Stripe, Vercel, etc.), fetch the brand's DESIGN.md from [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) — 76+ design systems as plain markdown.

**URL:** `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/designs/<brand>/DESIGN.md`

Extract the brand's color palette, typography style, and visual language, then weave them into the prompt (e.g., "clean Apple-style design with SF Pro typography, white background, subtle shadows, #007AFF accent blue").
