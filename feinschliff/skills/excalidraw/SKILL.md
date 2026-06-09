---
name: excalidraw
description: Use when visualizing systems, architectures, or concept flows — brand-aware Excalidraw authoring via compact DSL
---

# Excalidraw Diagram Authoring

Generate brand-perfect concept diagrams (boxes, arrows, flows, architectures) in editable Excalidraw JSON. Colors resolve against the active feinschliff brand pack.

## Use when

The user wants to visualize a system, architecture, request flow, or any concept where the relationship between things matters more than quantitative data. Output is editable in the Excalidraw app.

## Quick start

1. Author a `.exc.dsl` file — see `references/dsl-syntax.md`.
2. Expand DSL → Excalidraw JSON, then render to PNG.
3. Look at the rendered PNG once. Adjust if needed. One fix loop.

```bash
cd /path/to/feinschliff
uv run python -m feinschmiede.diagrams.excalidraw_expand flow.exc.dsl
uv run python -m feinschmiede.diagrams.render flow.excalidraw
```

## Brand override

The default brand is `feinschliff`; override via `--brand <name>`, `FEINSCHLIFF_BRAND=<name>`, or an inline `@brand <name>` directive at the top of the DSL. (Same precedence as `/svg`.)

## References

- [Methodology](references/methodology.md) — argue not display: patterns, depth assessment, hierarchy rules
- [DSL syntax](references/dsl-syntax.md)
- [Examples](references/examples.md)
- [Design system](references/design-system.md) — visual-argument methodology
