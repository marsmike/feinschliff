---
name: improve-brand
description: Use when a brand pack scaffold exists and you need to close the structural fidelity gap against a source PPTX — runs the verify-loop, then fans out one sub-agent per layout above threshold so each slide is analysed and edited in parallel.
---

# improve-brand — fan-out DSL improvement loop

Driven by a verify-map. For each layout whose `struct_diff_ratio` exceeds a
threshold after a verify-loop run, dispatch **one sub-agent per layout** in
parallel. Each sub-agent gets the per-slide diff overlay, the current DSL, and a
tight instruction set; it edits the DSL only; the parent re-runs the loop and
reports plateau-vs-progress.

## When to use

- You have a brand pack (`brands/<brand>/` with `tokens.json`, `layouts/*.slide.dsl`, `verify-map.yaml`) and a source PPTX deck to match.
- The pack is past the scaffold stage (every layout already builds and renders something recognisable). If it doesn't exist yet, start with `compile-html` — improve-brand is a polishing loop, not a scaffold tool.
- You want to drive every layout's `struct_diff_ratio` to ≤5% (or `--threshold`).

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
- **No cheating with pictures.** Every drawn element (text, shapes, lines, callouts, chart bars, icons) MUST be native DSL primitives. `picture` is reserved for genuine `<p:pic>` source elements (raster art, photos, logo). Substituting a bitmap invalidates the test.

Full rationale + the read-only-context rule: [`references/loop-detail.md`](references/loop-detail.md).

## Plateau handling (read before iteration 2)

On plateau/regression, **switch the prompt** — don't re-dispatch the standard
one. Log each iteration to `<output-dir>/attempts/<layout>.jsonl` for
failure-context; deletion is a legitimate redirection move; stop a layout after
2 plateau rounds. Rules: [`references/plateau-handling.md`](references/plateau-handling.md);
redirection prompt: [`references/redirection-prompt.md`](references/redirection-prompt.md).

Also see [`references/workflow.md`](references/workflow.md) (full loop with example invocations) and [`references/decompile-from-source.md`](references/decompile-from-source.md) (image carry-over background).
