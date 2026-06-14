---
name: autoloop
description: Iteratively improve a feinschliff diagram skill: loop measure, mutate one thing, keep or revert, consolidate, scoring generated output with `feinschliff-builder eval`. Rides the built-in /goal. Use when asked to autoloop against its evals.
---

# autoloop — deterministic improvement loop for skills

## Quick Start

```
/feinschliff-builder:autoloop <skill-dir>
```

See [`references/loop.md`](references/loop.md) for examples.

Drive a target to a measurable goal by running the Karpathy loop yourself: measure → mutate ONE thing → measure → keep or revert → repeat, consolidating what you learn. You are the loop runner; there is no external orchestrator.

Invoke as **`/feinschliff-builder:autoloop <target>`** — NOT bare `/goal`, which is Claude Code's *built-in* loop command (a generic "keep going until a condition" primitive this skill rides, not replaces).

- v1 targets: `excalidraw`, `svg` (the diagram skills, graded deterministically).
- `budget N`: max iterations (default 8) — internal safety cap.
- **Cross-turn persistence:** pair with the built-in `/goal "<condition>"` (e.g. `/goal feinschliff-builder eval on the excalidraw skill exits 0`). The built-in keeps Claude working across turns until the condition holds; this skill is the per-iteration body it runs. Don't hand-roll scheduling.

## The loop (per iteration, up to budget)

Full per-phase procedure — setup, the measure/grade commands, the keep/revert rule, consolidation — is in [`references/loop.md`](references/loop.md). In short:

1. **Measure** — for each eval test, dispatch a FRESH subagent given only the target SKILL.md (+ refs) and the test prompt; it authors DSL and runs `feinbild <skill> expand`. Grade with `feinschliff-builder eval … --json` and record the pooled score.
2. **Mutate** — follow [`references/mutator.md`](references/mutator.md): diagnose the failing checks, apply exactly ONE targeted edit (simplicity bias; never hardcode to an eval prompt). On plateau, switch to [`references/redirection.md`](references/redirection.md).
3. **Keep / revert** — re-measure. Keep if `delta > 0` (or a simplicity-win with the skill shorter) and commit to the experiment branch; else `git checkout --` the edit. The branch only accumulates wins.
4. **Consolidate** — every 3 iterations, follow [`references/consolidator.md`](references/consolidator.md): distill recurring patterns into `.autoloop/<target>/techniques/`.

## Stop conditions

Goal reached (all checks pass / score ≥ target), budget exhausted, or plateau persists after a redirection attempt. Under `/goal`, its condition is the outer authority; these are internal safety stops.

## Autonomy rails

- All work on branch `autoloop/<target>/<ts>`; never `main`. Budget-bounded; deterministic grader (no API cost for diagram targets). Revert-by-default.
- Always write `.autoloop/<target>/RESIDUAL.md` on exit (final score, what still fails + why, skill-gap vs grader limitation — be honest, never claim a pass the grader didn't confirm), then point the operator at the branch. Detail: [`references/loop.md`](references/loop.md).
