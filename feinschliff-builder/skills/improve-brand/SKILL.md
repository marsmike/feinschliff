---
name: improve-brand
description: Closing the structural fidelity gap between a brand pack scaffold and a source PPTX. Use when a scaffold exists — runs the verify-loop, then fans out one sub-agent per layout above threshold so each slide is analysed and edited in parallel.
---

# improve-brand — fan-out DSL improvement loop

## Quick Start

```
/feinschliff-builder:improve-brand <brand-dir> <source.pptx>
```

See [`references/workflow.md`](references/workflow.md) for examples.

Driven by a verify-map: fans out one sub-agent per layout above `struct_diff_ratio` threshold. Requires a scaffold-stage pack (`brands/<brand>/` with `tokens.json`, `layouts/*.slide.dsl`, `verify-map.yaml`). Not a scaffold tool — use `compile-html` first if the pack doesn't exist yet. Full context: [`references/loop-detail.md`](references/loop-detail.md).

## Checklist

You MUST create a task for each step and complete them in order. Full detail
(commands, dep notes, the process diagram) is in
[`references/loop-detail.md`](references/loop-detail.md).

1. Run `brand_verify_loop.py … --snapshot-baseline` (builds/renders/diffs every layout; locks the before-renders).
2. Read `<output-dir>/diff/report.json` for per-layout `struct_diff_ratio` + overlay paths.
3. Filter to the work set — layouts above `--threshold`.
4. Fan out sub-agents — ONE message, one `Agent` call per layout, **in parallel** (prompt template: [`references/per-slide-prompt.md`](references/per-slide-prompt.md)).
5. Wait for every sub-agent; treat "no change made" as that-layout-plateaued.
6. Re-run the verify loop (no `--snapshot-baseline`) to score the edits.
7. Plateau check — stop early if no layout improved ≥0.5% absolute.
8. Iterate until all ≤ threshold OR `--max-iterations` OR plateau.
9. Final report — one line per layout: start → end → verdict.
10. Produce the before/after PDF with `brand_before_after_pdf.py`.

## Sub-agent rules (non-negotiable)

- **One agent per layout, parallel, in a single message.** Never share an agent across layouts.
- **Strict scope.** Each may edit only its `layouts/<layout>.slide.dsl` (and, with permission, that layout's `tokens.json`). No other layouts, source PPTX, pipeline scripts, or git.
- **No cheating with pictures.** Every drawn element MUST be native DSL primitives; `picture` is for genuine raster art only. Full rationale: [`references/loop-detail.md`](references/loop-detail.md).

## Plateau handling

Switch the prompt on plateau/regression; stop a layout after 2 plateau rounds. Full rules and the redirection prompt: [`references/plateau-handling.md`](references/plateau-handling.md) · [`references/redirection-prompt.md`](references/redirection-prompt.md) · [`references/workflow.md`](references/workflow.md) · [`references/decompile-from-source.md`](references/decompile-from-source.md).
