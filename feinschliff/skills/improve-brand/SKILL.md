---
name: improve-brand
description: Iteratively improve a brand pack's `.slide.dsl` layouts to match a source PPTX. Runs the verify-loop, then fans out one sub-agent per layout above threshold so each slide is analysed and edited in parallel.
---

# improve-brand — fan-out DSL improvement loop

Driven by a verify-map. For each layout whose `struct_diff_ratio` exceeds a
threshold after a verify-loop run, dispatch **one sub-agent per layout** in
parallel. Each sub-agent gets the per-slide diff overlay, the current DSL,
and a tight instruction set; it edits the DSL only; the parent re-runs the
loop and reports plateau-vs-progress.

## When to use

- You have a brand pack (`brands/<brand>/` with `tokens.json`,
  `layouts/*.slide.dsl`, `verify-map.yaml`) and a source PPTX deck to
  match.
- The brand pack is past the initial scaffold stage (every layout
  already has a `.slide.dsl` that builds and renders something
  recognisable).
- You want to drive every layout's `struct_diff_ratio` to ≤5% or
  another threshold.

If the brand pack doesn't exist yet, start with `compile-html` and a
hand-derived first pass — improve-brand is a polishing loop, not a
scaffold tool.

## Inputs

| Argument            | Required | Default                                   |
| ------------------- | -------- | ----------------------------------------- |
| `--brand-pack`      | yes      | —                                         |
| `--source-pptx`     | yes      | —                                         |
| `--threshold`       | no       | `0.05` (struct_diff_ratio)                |
| `--max-iterations`  | no       | `3`                                       |
| `--only`            | no       | all layouts in `verify-map.yaml`          |
| `--output-dir`      | no       | `out/<brand>/verify-loop`                 |

## Process

```dot
digraph improve {
    "run brand_verify_loop.py" [shape=box];
    "read report.json" [shape=box];
    "filter layouts > threshold" [shape=box];
    "any to fix?" [shape=diamond];
    "DONE — all green" [shape=doublecircle];
    "fan out: one sub-agent per layout (parallel)" [shape=box];
    "wait for all sub-agents" [shape=box];
    "compare scores: progress vs plateau" [shape=box];
    "iteration < max?" [shape=diamond];
    "DONE — plateau or budget exhausted" [shape=doublecircle];

    "run brand_verify_loop.py" -> "read report.json";
    "read report.json" -> "filter layouts > threshold";
    "filter layouts > threshold" -> "any to fix?";
    "any to fix?" -> "DONE — all green" [label="no"];
    "any to fix?" -> "fan out: one sub-agent per layout (parallel)" [label="yes"];
    "fan out: one sub-agent per layout (parallel)" -> "wait for all sub-agents";
    "wait for all sub-agents" -> "run brand_verify_loop.py" [label="re-render"];
    "wait for all sub-agents" -> "compare scores: progress vs plateau";
    "compare scores: progress vs plateau" -> "iteration < max?";
    "iteration < max?" -> "run brand_verify_loop.py" [label="yes"];
    "iteration < max?" -> "DONE — plateau or budget exhausted" [label="no"];
}
```

## Checklist

You MUST create a task for each of these items and complete them in order:

1. **Run the verify loop with `--snapshot-baseline`** —
   `uv run python scripts/brand_verify_loop.py --brand-pack <path>
   --source-pptx <path> --snapshot-baseline`.
   This builds, renders, and diffs every layout in `verify-map.yaml`,
   AND copies the first-iteration renders into `render-png.before/`
   so step 10 can compose a before/after PDF.
2. **Read `<output-dir>/diff/report.json`** to get per-layout
   `struct_diff_ratio`, `picture_coverage`, and overlay paths.
3. **Filter to the work set** — layouts whose `struct_diff_ratio`
   exceeds `--threshold`.
4. **Fan out sub-agents** — issue ONE message containing one `Agent`
   tool call per layout in the work set so they run **in parallel**.
   Each sub-agent's prompt MUST be self-contained (see the per-slide
   prompt template in `references/per-slide-prompt.md`).
5. **Wait for every sub-agent to return.** Treat any sub-agent that
   says "no change made" as that-layout-plateaued for this round.
6. **Re-run the verify loop** to score the new edits (no
   `--snapshot-baseline` — the baseline is already locked in).
7. **Plateau check** — if no layout's score improved by ≥ 0.5%
   absolute since last iteration, stop early.
8. **Iterate** until all layouts ≤ threshold OR
   `--max-iterations` exhausted OR plateau detected.
9. **Final report** — print one line per layout: starting score →
   ending score → verdict (green / improved / plateau / regressed).
10. **Produce the before/after PDF** —
    `uv run python scripts/brand_before_after_pdf.py --brand-pack <path>`.
    Writes `<output-dir>/before-after.pdf` — one page per layout with
    the source, baseline render, and final render side-by-side, plus
    the score delta in the header. This is the artifact a reviewer
    opens to judge whether the iteration was worth running.

### Image carry-over for pipeline-optimization runs

When iterating to evaluate **the pipeline itself** (e.g. driving the
hybrid decompiler / verify loop's structural fidelity), pass
`--carry-images` to the **initial** `brand_decompile_all.py` call:

```bash
uv run python scripts/brand_decompile_all.py \
    --brand-pack <path> --source-pptx <path> --carry-images
```

This extracts every `<p:pic>` binary from the source slide into
`<brand-pack>/assets/decompile/<layout>/imageN.<ext>` and rewires the
DSL's `default:` slot to point at it. The render then uses the *real*
source picture, so `total_diff_ratio` becomes meaningful (no
picture_coverage masking needed) and the visual diff measures shape +
text fidelity alone.

Use carry-images for self-test runs. Don't use it when authoring a
brand-neutral template — the genericised brand pack should default to
the brand's own placeholder.

## Sub-agent dispatch rules

- **One agent per layout.** Never share an agent across layouts —
  contexts collide and edits step on each other.
- **Parallel by default.** Send all `Agent` tool calls in a SINGLE
  assistant message. The runtime fans them out concurrently; serial
  dispatch wastes wall time and doubles cache misses.
- **Read-only context.** Each sub-agent gets file paths in its prompt;
  do not paste DSL or PNG bytes inline. Sub-agents read what they need.
- **Strict scope.** Each sub-agent may only edit
  `<brand>/layouts/<layout>.slide.dsl` (and, with explicit permission,
  `<brand>/tokens.json` for that layout's style overrides). It MUST
  NOT touch other layouts, the source PPTX, or pipeline scripts.
- **No git side effects.** Sub-agents edit files only; the user controls
  commits.

See [`references/per-slide-prompt.md`](references/per-slide-prompt.md)
for the prompt template that goes into each `Agent` tool call.

## Detailed workflow

See [`references/workflow.md`](references/workflow.md) for the full
loop with example invocations, plateau-handling, and how to extend the
sub-agent prompt with brand-specific style guidance.
