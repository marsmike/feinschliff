---
name: excalidraw
description: Generate Excalidraw diagrams from a compact DSL with brand-resolved colors. Use for boxes/arrows flow diagrams.
---

# feinbild — Excalidraw diagrams

## Quick Start

```
/excalidraw flow.exc.dsl
```

See [`references/examples.md`](references/examples.md) for examples.

`feinbild` is a command on your PATH. Expand a `.exc.dsl` to `.excalidraw`
(brand colors resolved), then render to PNG.

```bash
feinbild excalidraw expand flow.exc.dsl --brand feinschliff   # -> flow.excalidraw
feinbild excalidraw render flow.excalidraw                    # -> flow.png
feinbild verify flow.excalidraw                               # lint: overflow, overlap, label collision
```

Primitives: `box ellipse diamond dot line zone lane text` and
`arrow <from> -> <to> [label:"…"]`. Set `theme dark` in the DSL for a dark
canvas. `--brand` selects the brand; `render` is brand-agnostic.

## References

- [Methodology](references/methodology.md) — argue-not-display patterns, depth assessment, hierarchy & arrow-routing rules
- [DSL syntax](references/dsl-syntax.md) — full grammar: primitives, zone/lane, arrow flags, ports, colors, text levels
- [Design system](references/design-system.md) — audience-calibrated complexity, visual vocabulary, 10 arrow-discipline principles
- [Examples](references/examples.md) — fan-out / pipeline-with-decision / multi-zoom blueprints
- [Deep examples](references/examples-deep.md) — large layered architectures (MCU/Linux stacks, OTA flows, audience-contrast pairs); source DSL in `examples/`
- Eval fixtures live in `evals/evals.json`; reusable DSL fixtures in `examples/*.exc.dsl`

### Brand override

The default brand is `feinschliff`. Override (highest precedence first): an inline
`@brand <name>` line at the top of the `.exc.dsl`, then `--brand <name>` on
`feinbild excalidraw expand`, then the `FEINSCHLIFF_BRAND` environment variable.
`expand` resolves brand colors; `render` is brand-agnostic.
