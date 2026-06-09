# Providers & Models

## Replicate (default)

- `black-forest-labs/flux-schnell` — **default**, fastest (~0.5s), $0.003/img, good quality
- `black-forest-labs/flux-2-pro` — high quality (~3-5s), ~$0.03/img, 8 ref images
- `black-forest-labs/flux-1.1-pro-ultra` — best quality, 4MP, ~$0.06/img
- `black-forest-labs/flux-kontext-pro` — excellent text rendering, great for memes

## Gemini (Nano Banana)

- `gemini-2.5-flash-image` — **default**, fast, free tier (500 img/day)
- `gemini-3.1-flash-image-preview` — faster, newer
- `gemini-3-pro-image-preview` — highest quality (Nano Banana Pro)

## Provider Selection Guide

| Need | Best Provider | Why |
|------|--------------|-----|
| Speed | Replicate (flux-schnell) | 0.5s generation |
| Free | Gemini | 500 free images/day |
| Meme text | Replicate (flux-kontext) | Best text rendering |
| Photo realism | Replicate (flux-2-pro) | Best photorealism |
| General quality | Gemini (nano-banana-pro) | Great all-rounder |

## Meme Tips

For memes, craft the prompt to include text and visual elements:
- Be specific about text placement: "text at top says 'WHEN THE CODE WORKS' and text at bottom says 'ON THE FIRST TRY'"
- Use `flux-kontext-pro` for best text rendering
- Use `1:1` aspect ratio for social media memes
- Describe the meme format: "Drake meme format", "distracted boyfriend meme style"

## Examples

```bash
# Fast meme
feinbild imagine --prompt "a cat looking confused at a computer screen, meme style, text says DEBUG MODE" --provider replicate --model black-forest-labs/flux-kontext-pro --out meme.png

# Free high-quality image via Gemini
feinbild imagine --prompt "beautiful mountain landscape at golden hour" --provider gemini --model gemini-3-pro-image-preview --out landscape.png

# Wide cinematic shot via Gemini
feinbild imagine --prompt "cyberpunk city at night, neon lights, rain" --provider gemini --aspect-ratio 16:9 --out city.png

# Quick iteration with default provider
feinbild imagine --prompt "logo for a coffee shop called Bean There" --out logo.webp
```
