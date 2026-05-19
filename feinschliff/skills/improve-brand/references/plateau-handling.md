# Plateau handling

What to do when the verify loop stops improving — distilled from the
[[Graduation-Pattern]] (vault) and the autoresearch
[[redirection.md]] directive that drives autonomous mutator agents
out of local minima.

## The three invariants every iteration loop needs

The Graduation Pattern says any "self-improving" loop is a wheel
spinning blindly unless it has all three:

1. **Measurable signal** — `struct_diff_ratio` per layout. ✓ present.
2. **Failure-context feedback** — what the *previous* attempt tried
   and whether it was kept or reverted must reach the *next*
   attempt's prompt. Without it, every iteration re-invents from
   scratch and burns the same wrong moves. The improve-brand loop
   logs this to `attempts/<layout>/iter-N.json` (see "Attempt log"
   below) and threads it into the redirection prompt.
3. **Freeze on plateau** — the winning DSL is the `.slide.dsl` file
   itself (no separate freeze step needed). The plateau decision is
   what gets frozen: stop dispatching the layout. ✓ present.

The current loop is strong on (1) and (3); the missing piece is (2),
which is what every redirection round below is fixing.

## When to redirect vs. iterate again

After re-verifying, compare per layout against the previous round:

| Δ struct_diff_ratio | Verdict      | Action                                                                                            |
| ------------------- | ------------ | ------------------------------------------------------------------------------------------------- |
| `Δ > +0.005`        | improved     | Re-dispatch with the standard prompt — momentum is real.                                          |
| `−0.005 ≤ Δ ≤ +0.005` | **plateau** | **Re-dispatch with the redirection prompt** (`references/redirection-prompt.md`). Same-direction nudging is what put us here. |
| `Δ < −0.005`        | **regressed** | **Revert the DSL** to the previous iteration (or to baseline if no prior version) AND re-dispatch with the redirection prompt, noting the reverted attempt in the prior-attempts section. Do not let a wrong move accumulate. |

Stop the layout entirely when:
- It has plateaued for 2 consecutive rounds (the redirection didn't
  help either), OR
- A regression repeated after a revert + retry (the agent has no
  better hypothesis), OR
- `--max-iterations` exhausted.

## The redirection prompt

The standard `per-slide-prompt.md` says "look at the diff and improve
the DSL." That works once. On plateau it doesn't — the agent
re-derives the same hypothesis from the same evidence and proposes
the same kind of change. The redirection prompt
(`references/redirection-prompt.md`) tells the agent:

- **Step back, reassess.** Don't re-read the diff first; read the
  attempts log first.
- **Look for the category of change that has NOT been tried.**
  Concrete redirection moves (from the autoresearch directive):

  | Past mutators did this … | Try this instead              |
  | ------------------------ | ----------------------------- |
  | Added clarifications     | **Deletion** — which existing primitive is redundant or contradicts the source? |
  | Tightened existing wording | **Restructuring** — new section order, different framing (group by reading order instead of geometry, or vice versa). |
  | Focused on one failure type (e.g. text positions) | **Address a different one** — fills, strokes, missing chrome, or the master-inherited footer. |
  | All read the same way    | **Different theory of what's wrong** — maybe the issue isn't *what* primitive, it's *which* style-bundle token. |

- **Anti-bloat warnings** (also from the directive):
  - Don't combine multiple small changes into one big change to seem
    different. That's still incrementalism with more risk.
  - Don't add length. Plateau often comes from accumulated bloat —
    **deletion is a legitimate redirection move**.
  - Don't gut the DSL. The current version still scores at the
    plateau level — there's signal in it. Pivot the angle, don't
    burn the artifact.

## Attempt log structure

After each iteration (whether improved, plateaued, or regressed),
the parent appends one JSON line per layout to
`<output-dir>/attempts/<layout>.jsonl`:

```json
{"iter": 2, "ts": "2026-05-19T20:14:00Z", "score_before": 0.218, "score_after": 0.324, "verdict": "regressed", "kept": false, "summary": "replaced 10 bbox-rects with concentric ovals; recolored sectors to accent + fog"}
```

Fields:

- `iter` — 1-indexed iteration number.
- `ts` — UTC ISO timestamp.
- `score_before`/`score_after` — the layout's `struct_diff_ratio`
  before and after this iteration's edits.
- `verdict` — `improved` / `plateau` / `regressed` per the table
  above.
- `kept` — `true` if the edits stayed in the DSL after the parent
  re-verified, `false` if the parent reverted (regressed case).
- `summary` — the one-line summary the sub-agent returned. This is
  the *failure context* the next iteration's prompt threads in.

When dispatching the next iteration's sub-agent for that layout, the
parent reads the last 3-5 attempts and pastes them verbatim into the
prompt's `PRIOR ATTEMPTS` section so the agent doesn't re-try a
move that was already reverted.

## Why this matters

The ring-diagrams layout in the 2026-05-19 VDE-ETG smoke test
regressed from 21.76% to 32.39% in one round because the dispatched
sub-agent treated thin-stroked ring outlines as solid donuts. The
parent reverted and dispatched a second agent with hard-coded
guidance about why the first approach was wrong — but only because
a human (Mike) was in the loop. With this attempt log in place, the
second agent reads the first's failed summary directly and the
human stays out of the inner loop. That's the difference between
"the harness has a self-improvement claim" and "the harness
actually self-improves."

## Related vault notes

- [[Graduation-Pattern]] — the three invariants this skill borrows
- [[Feedback-Loop]] — signal lag, observability, polarity
- [[Harness-Loop-Pattern]] — the four harness components (input,
  output, signal, bounded action space) — improve-brand's bounded
  action space is "edit one .slide.dsl file"
- [[Mode-Collapse]] — why "most likely fix" thinking on plateau is a
  failure mode; redirection is the structural countermeasure
- autoresearch `skills/autoresearch/references/redirection.md` —
  the directive this distillation is derived from
