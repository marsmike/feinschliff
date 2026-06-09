---
name: excalidraw
description: Generate Excalidraw diagrams from a compact DSL with brand-resolved colors. Use for boxes/arrows flow diagrams.
---

# feinbild — Excalidraw diagrams

`feinbild` is a command on your PATH. Expand a `.exc.dsl` to `.excalidraw`
(brand colors resolved), then render to PNG.

```bash
feinbild excalidraw expand flow.exc.dsl --brand feinschliff   # -> flow.excalidraw
feinbild excalidraw render flow.excalidraw                    # -> flow.png
```

Primitives: `box ellipse diamond dot line zone lane text` and
`arrow <from> -> <to> [label:"…"]`. Set `theme dark` in the DSL for a dark
canvas. `--brand` selects the brand; `render` is brand-agnostic.
