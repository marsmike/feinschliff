---
name: excalidraw
description: "Generate an Excalidraw diagram from a .exc.dsl. Usage: /excalidraw <file.exc.dsl>"
user_invocable: true
---

# /excalidraw

Expand then render the user's `.exc.dsl` with the `feinbild` CLI:

```bash
feinbild excalidraw expand "<file>.exc.dsl" --brand "${FEINBILD_BRAND:-feinschliff}"
feinbild excalidraw render "<file>.excalidraw"
```

`feinbild` is on PATH — call it as a bare command; never use a file path.
