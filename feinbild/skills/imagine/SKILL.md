---
name: imagine
description: Generate AI images via Replicate or Gemini. Use to create illustrations, photos, or graphics from a text prompt.
---

# feinbild — AI image generation

`feinbild` is a command on your PATH. Requires a provider key in `~/.env`
(`REPLICATE_API_KEY` or `GEMINI_API_KEY`).

```bash
feinbild imagine --prompt "a calm mountain lake at dawn" --out lake.webp
feinbild imagine --prompt "logo, flat, blue" --provider gemini --aspect-ratio 16:9 --out logo.png
```

Options: `--provider` (`replicate` default, or `gemini`), `--model`
(default `black-forest-labs/flux-schnell` / `gemini-2.5-flash-image`),
`--aspect-ratio` (`1:1` default, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`),
`--out`. Without a key the command prints a clean error and makes no paid call.
