---
name: goal
description: Autonomously improve a feinschliff target (a skill, a DSL template, a deck, or framework code) toward a measurable goal by looping measure -> mutate -> keep/revert -> consolidate. Use when asked to /goal <target> until <condition>.
---

# /goal — autonomous improvement loop

Drive a target to a goal by running the Karpathy loop yourself: measure ->
mutate ONE thing -> measure -> keep or revert -> repeat, consolidating what you
learn. You are the loop runner. No external orchestrator.

Invocation: `/goal <target> until <condition> [budget N]`
- v1 targets: `excalidraw`, `svg` (the diagram skills, graded deterministically).
- `<condition>`: a stop predicate, e.g. "all checks pass", "score >= 0.95".
- `budget N`: max iterations (default 8). For unattended runs the operator
  wraps this in `/loop` so you self-pace via ScheduleWakeup.

## Setup (once per run)

1. Resolve the target's skill dir and evals file:
   - `excalidraw` -> `feinbild/skills/excalidraw`, evals at `evals/evals.json`.
   - `svg` -> `feinbild/skills/svg`.
2. Create an experiment branch: `git checkout -b autoloop/<target>/<timestamp>`.
   ALL kept mutations commit here. Never touch `main`.
3. Working dir: `.autoloop/<target>/` with `results/`, `attempts/`, `notes/`,
   `techniques/` (gitignored). Read any existing `techniques/*.md` first —
   that is accumulated learning from prior runs; do not re-derive it.

## The loop

For each iteration up to budget:

### Measure
Generate fresh artifacts, then grade them.
1. For each test in evals.json, **dispatch a fresh subagent** (Agent tool)
   given ONLY: the current target SKILL.md (+ its references) and the test
   `prompt`. Instruct it to follow the skill to author the DSL and run
   `feinbild <skill> expand <dsl> -o .autoloop/<target>/results/<test-name>.<ext>
   --brand feinschliff` (ext: `.excalidraw` or `.svg`). Using a fresh subagent
   is essential: it isolates the skill text's effect from your own knowledge,
   so the score reflects the SKILL, not you.
2. Grade: `feinschliff-builder eval <skill-dir> --results-dir
   .autoloop/<target>/results --json`. Record the pooled `score`.

### Stop check
If `<condition>` is met (e.g. all checks pass / score >= target), STOP and
emit the residual report (below). Else continue.

### Mutate
Read `references/mutator.md` and follow it: read the failing checks and the
actual generated artifacts, diagnose the root cause in the SKILL, apply exactly
ONE targeted edit. Simplicity bias (prefer deletion/tightening over addition);
never hardcode to a specific eval prompt. Write a reflection note to
`.autoloop/<target>/notes/iter-N.md`.

If the loop has plateaued (2 iterations with no real score gain), read
`references/redirection.md` instead and make a structurally-different change.

### Re-measure + keep/revert
Re-run Measure on the mutated skill. Then decide:
- **Keep** if `delta > 0`, OR simplicity-win (`abs(delta) < 0.005` AND the skill
  got shorter), AND the score is above any floor. -> `git add <skill-dir> &&
  git commit -s`. Advance the rolling baseline to the new score.
- **Revert** otherwise -> `git checkout -- <skill-dir>` (discard the edit). The
  branch only ever accumulates wins.
Append the outcome to `.autoloop/<target>/attempts/iter-N.json`
(`{iter, score, kept, summary}`).

### Consolidate (every 3 kept-or-reverted iterations)
Read `references/consolidator.md` and follow it: distill recurring patterns from
the notes into `.autoloop/<target>/techniques/<name>.md`. 2-iteration minimum —
a pattern seen once is speculation. These persist across runs.

## Stop conditions
- `<condition>` met, OR
- budget exhausted, OR
- plateau persists after a redirection attempt.

## Residual report (always, on every exit)
Write `.autoloop/<target>/RESIDUAL.md`: final score, which checks/tests still
fail and why, what was tried, and whether the cause looks like a skill gap vs a
grader/engine limitation. Be honest — never claim a clean pass the grader did
not confirm. Then summarize to the operator and point at the experiment branch
for review/merge.

## Autonomy rails
- All work on `autoloop/<target>/<ts>`; never `main`.
- Budget-bounded; deterministic grader (no API cost for diagram targets).
- Revert-by-default; honest residual report; operator merges deliberately.
- Long runs: ScheduleWakeup to self-pace; the operator can interrupt anytime.
