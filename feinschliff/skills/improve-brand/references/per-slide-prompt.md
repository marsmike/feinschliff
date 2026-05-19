# Per-slide sub-agent prompt template

Each sub-agent dispatched by `improve-brand` receives one of these
prompts via the `Agent` tool. The parent fills in the `{{placeholders}}`.

## Template

```text
You are improving ONE layout in a feinschliff brand pack so its rendered
output matches a source PPTX more closely. You operate on file paths
only — read what you need, don't ask for context.

LAYOUT:                {{layout_name}}
BRAND PACK:            {{brand_pack_path}}
SOURCE PPTX:           {{source_pptx_path}} (slide {{source_slide_no}})

DSL FILE (your only edit target):
  {{brand_pack_path}}/layouts/{{layout_name}}.slide.dsl

BRAND TOKENS (read for token names; only edit with explicit user signoff):
  {{brand_pack_path}}/tokens.json

EVIDENCE (read these for visual diff context):
  source:  {{output_dir}}/source-png/slide-{{source_slide_no_padded}}.png
  render:  {{output_dir}}/render-png/{{layout_name}}.png
  overlay: {{output_dir}}/diff/slide-{{source_slide_no_padded}}_{{layout_name}}_overlay.png

CURRENT METRICS:
  struct_diff_ratio:   {{struct_diff_pct}}%
  picture_coverage:    {{picture_coverage_pct}}%
  target_threshold:    {{threshold_pct}}%

YOUR JOB
1. Read the source PNG, render PNG, and overlay PNG. The overlay is a
   3-panel image: source | render | red-mask diff. Red pixels are where
   render differs from source by more than 30/255.
2. Read the current DSL. Identify the primitives that most plausibly
   cause the red regions:
   - text positioning / size / weight / color (style: token mismatches)
   - rect/oval/line positions, fills, strokes
   - missing chrome (footer fields, page numbers, brand wordmark)
   - oversized or undersized typography (most diffs trace back here)
3. Edit ONLY the DSL file. Do not add new layouts, do not refactor
   unrelated primitives, do not introduce new compounds unless the
   brand pack already defines them under `{{brand_pack_path}}/compounds/`.
4. Keep edits CONSERVATIVE. Prefer adjusting an existing primitive over
   adding a new one. Diff iteration is cheaper when each round changes
   3–5 primitives, not 30.

CONSTRAINTS
- Picture regions are masked when scoring, so do not try to alter
  picture placeholders to match the source illustration.
- Use only style tokens that exist in tokens.json. Look up unknown
  tokens before guessing.
- Preserve all `{{ slot | default:'…' }}` slot expressions.
- Do not modify the source PPTX, the verify-map.yaml, or any script.

OUTPUT
- After editing, print a one-line summary of what you changed
  (e.g. "moved title to 76,76; switched body to style:body-sm").
- If nothing safe to change, print "no change made" and the reason.
- Do NOT re-render or re-verify — the parent does that.
```

## Filling the placeholders

The parent computes these from `report.json` + `verify-map.yaml`:

| Placeholder                  | Source                                           |
| ---------------------------- | ------------------------------------------------ |
| `{{layout_name}}`            | report.json key                                  |
| `{{brand_pack_path}}`        | `--brand-pack` arg (absolute)                    |
| `{{source_pptx_path}}`       | `--source-pptx` arg (absolute)                   |
| `{{source_slide_no}}`        | `report.json[layout].slide`                      |
| `{{source_slide_no_padded}}` | `f"{source_slide_no:02d}"`                       |
| `{{output_dir}}`             | resolved `--output-dir`                          |
| `{{struct_diff_pct}}`        | `report.json[layout].struct_diff_ratio * 100`    |
| `{{picture_coverage_pct}}`   | `report.json[layout].picture_coverage * 100`     |
| `{{threshold_pct}}`          | `--threshold * 100`                              |

## Dispatch shape

The parent sends ONE message containing N `Agent` tool calls (one per
layout in the work set). Example with two layouts:

```text
Agent({
  description: "Improve cover-orange DSL",
  subagent_type: "general-purpose",
  prompt: <filled template for cover-orange>
})
Agent({
  description: "Improve timeline-gantt DSL",
  subagent_type: "general-purpose",
  prompt: <filled template for timeline-gantt>
})
```

Both calls go out in a single assistant turn so they execute in
parallel. Sub-agents return when they have finished editing or have
decided not to edit; the parent collects all results, then re-runs the
verify loop.

## Why one agent per layout

- **Scope isolation** — a sub-agent reasoning about one slide can hold
  all the relevant primitives in attention. Multi-slide sub-agents
  conflate signals from unrelated layouts and edit imprecisely.
- **Parallelism** — fanning out one-per-layout uses the runtime's
  parallel-tool dispatch; serial loops scale linearly with slide count.
- **Context cost** — each sub-agent loads only the three PNGs and one
  DSL it needs; the parent never carries that payload.
- **Blast radius** — a confused sub-agent edits exactly one DSL file.
  The parent re-verifies before the next round, so regressions are
  caught at the layout level.
