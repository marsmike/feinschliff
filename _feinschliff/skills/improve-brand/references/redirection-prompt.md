# Redirection sub-agent prompt template

Use this template (instead of `per-slide-prompt.md`) when a layout
has plateaued or regressed for 1+ rounds. The parent fills in the
`{{placeholders}}` *and* the `PRIOR ATTEMPTS` block from
`<output-dir>/attempts/<layout>.jsonl`.

See [`plateau-handling.md`](plateau-handling.md) for when to switch
to this prompt and which redirection moves to try.

## Template

```text
You are improving ONE layout in a feinschliff brand pack so its rendered
output matches a source PPTX more closely. THIS IS A REDIRECTION ROUND
— the layout has plateaued or regressed. Prior incremental tweaks
are no longer producing wins. Step back, reassess, and propose a
**structurally different** change.

LAYOUT:                {{layout_name}}
BRAND PACK:            {{brand_pack_path}}
SOURCE PPTX:           {{source_pptx_path}} (slide {{source_slide_no}})

DSL FILE (your only edit target):
  {{brand_pack_path}}/layouts/{{layout_name}}.slide.dsl

EVIDENCE:
  source:  {{output_dir}}/source-png/slide-{{source_slide_no_padded}}.png
  render:  {{output_dir}}/render-png/{{layout_name}}.png
  overlay: {{output_dir}}/diff/slide-{{source_slide_no_padded}}_{{layout_name}}_overlay.png

CURRENT METRICS:
  struct_diff_ratio:   {{struct_diff_pct}}%   (target ≤ {{threshold_pct}}%)
  iterations elapsed:  {{iteration_count}}
  best score so far:   {{best_score_pct}}%   (at iter {{best_iter}})

PRIOR ATTEMPTS  (last 5, newest first — read these BEFORE the diff)
{{prior_attempts_block}}

PROCESS  (do these in order)

1. **Read PRIOR ATTEMPTS first.** What categories of change have
   been tried? What was kept vs reverted? Where did past sub-agents
   think the next angle was?
2. **Read the source / render / overlay PNGs** to confirm the
   current visual gap.
3. **Read the current DSL.** It still scores at the plateau level,
   so it has signal. Find what to PIVOT, not what to gut.
4. **Pick a category of change that has NOT been tried.** Examples:

   | If past attempts did this …               | Try this instead |
   | ----------------------------------------- | ---------------- |
   | Added new primitives (clarifications)     | DELETION — which existing primitive is redundant or contradicts the source? |
   | Tightened existing primitive positions    | RESTRUCTURING — re-emit primitives in source-reading order, or change which primitives carry which text |
   | Focused on text (positions, sizes, colors) | SHAPES — fills, strokes, missing chrome (footer fields, page numbers, brand wordmark) |
   | Focused on shapes                          | TYPOGRAPHY — which `style:` token is wrong? which `color:` override is missing? |
   | All read the same way                      | DIFFERENT THEORY — maybe the issue isn't *what* primitive exists, it's *which style bundle* it uses. Read brands/feinschliff/tokens.json and pick a closer-fitting style. |

5. **Edit the DSL.** ONE logical change. No combining multiple small
   changes into one big change to "seem different" — that is still
   incrementalism with more risk.

CONSTRAINTS — READ CAREFULLY
- **NO CHEATING WITH PICTURE STATEMENTS.** Every drawn visual
  element MUST be a native DSL primitive (`rect`, `shape`, `line`,
  `text`). The `picture` primitive is reserved for genuine `<p:pic>`
  source elements. See `per-slide-prompt.md` for the full rule.
- **Don't add length.** Plateau often comes from accumulated bloat
  — DELETION is a legitimate redirection move.
- **Don't gut the DSL.** The current version still scores; there's
  signal in it. Pivot the angle.
- Use only style tokens that exist in tokens.json (child or
  parent).
- Preserve all `{{ slot | default("…") }}` slot expressions.
- Do not modify the source PPTX, the verify-map.yaml, tokens.json,
  or any script.

OUTPUT
- One-line summary of what you changed and which **category** of
  redirection move you chose (deletion / restructuring / different
  primitive type / different style token / different theory).
- If after reading the attempts log you genuinely cannot find a
  pivot direction, print "no change made — plateau is structural;
  the bbox-from-custGeom decompiler limitation is the binding
  constraint here" (or similar diagnostic). Stopping is a valid
  answer — better than a wrong move.
- Do NOT re-render or re-verify — the parent does that.
```

## Filling the PRIOR ATTEMPTS block

Read the last 5 lines of `<output-dir>/attempts/<layout_name>.jsonl`,
newest first, and format each as:

```text
iter {{iter}}  {{verdict}}  ({{score_before_pct}}% → {{score_after_pct}}%)  [{{"KEPT" if kept else "REVERTED"}}]
  {{summary}}
```

Example block:

```text
iter 2  regressed  (21.76% → 32.39%)  [REVERTED]
  replaced 10 bbox-rects with concentric ovals; recolored sectors to accent + fog
iter 1  plateau    (21.76% → 21.80%)  [REVERTED]
  shifted text labels by 5px; no shape changes
```

If there are no prior attempts (first redirection round), emit:

```text
(no prior attempts logged — this is the first redirection round.
Start by asking: which category of change is the OBVIOUS one to try?
Then explicitly choose a DIFFERENT category.)
```

## Why one redirection round instead of "just iterate harder"

[[Mode-Collapse]] from the vault: when an agent re-derives the
"most likely fix" from the same evidence, it picks the most typical
move. The fixes that move the score live in the tails of the
distribution — exactly the moves the agent suppresses by default.
The redirection prompt is a [[Verbalized-Sampling]]-style
intervention: it explicitly steers the agent toward a category of
change it would not have picked on its own.
