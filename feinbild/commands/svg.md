---
name: svg
description: "Generate an SVG diagram from a .svg.dsl. Usage: /svg <file.svg.dsl>"
user_invocable: true
---

# /svg

Expand then render the user's `.svg.dsl` with the `feinbild` CLI:

```bash
feinbild svg expand "<file>.svg.dsl" --brand "${FEINSCHLIFF_BRAND:-feinschliff}"
feinbild svg render "<file>.svg"
```

`feinbild` is on PATH — call it as a bare command; never use a file path.
