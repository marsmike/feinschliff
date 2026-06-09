---
name: imagine
description: "Generate an AI image from a prompt. Usage: /imagine <prompt>"
user_invocable: true
---

# /imagine

Generate an image with the `feinbild` CLI:

```bash
feinbild imagine --prompt "<user prompt>" --out "${CLAUDE_PROJECT_DIR:-.}/image.webp"
```

Pass through `--provider`, `--model`, `--aspect-ratio`, `--out` if given. If no
key is set the command prints a clear error and makes no paid call.
