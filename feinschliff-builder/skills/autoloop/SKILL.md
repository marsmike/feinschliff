---
name: autoloop
description: Deterministically improve a feinschliff diagram skill (and later DSL templates / decks / framework code) by looping measure -> mutate ONE thing -> keep/revert -> consolidate, scoring GENERATED output with `feinschliff-builder eval`. Pairs with Claude Code's built-in /goal for cross-turn persistence. Use when asked to autoloop / iteratively improve a target against its evals.
---

# autoloop — deterministic improvement loop for skills

Drive a target to a measurable goal by running the Karpathy loop yourself:
measure -> mutate ONE thing -> measure -> keep or revert -> repeat, consolidating
what you learn. You are the loop runner. No external orchestrator.

Invoke as **`/feinschliff-builder:autoloop <target>`** — NOT bare `/goal`, which
is Claude Code's *built-in* loop command (a generic, fast-model-judged
"keep going until a condition" primitive — a different thing this skill rides,
not replaces).
- v1 targets: `excalidraw`, `svg` (the diagram skills, graded deterministically).
- `budget N`: max iterations (default 8) — an internal safety cap.
- **Cross-turn persistence:** for long unattended runs, pair this with the
  built-in `/goal "<condition>"` (e.g. `/goal feinschliff-builder eval on the
  excalidraw skill exits 0`). The built-in keeps Claude working across turns
  until the condition holds; this skill is the per-iteration body it runs. Do
  NOT hand-roll scheduling — the built-in owns continuation.

## Setup (once per run)

1. Resolve the target's skill dir and evals file:
   - `excalidraw` -> `feinbild/skills/excalidraw`, evals at `evals/evals.json`.
   - `svg` -> `feinbild/skills/svg`.
2. Create an experiment branch: `git checkout -b autoloop/<target>/<timestamp>`.
   ALL kept mutations commit here. Never touch `main`.
3. Create the working dir (gitignored) — `feinbild expand -o` does NOT create
   parent dirs, so make them up front:
   `mkdir -p .autoloop/<target>/{results,attempts,notes,techniques}`.
   Then read any existing `.autoloop/<target>/techniques/*.md` first — that is
   accumulated learning from prior runs; do not re-derive it.

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
If the goal is reached (all checks pass, or score >= the target you were given),
STOP and emit the residual report (below). Else continue. When driven by the
built-in `/goal`, it independently re-checks your stated condition each turn —
your job is simply to do the next useful iteration.

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
- goal reached (all checks pass / score >= target), OR
- budget exhausted, OR
- plateau persists after a redirection attempt.

Under the built-in `/goal`, its condition is the outer authority; these are your
internal safety stops.

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
- Cross-turn persistence comes from the built-in `/goal`, not hand-rolled
  scheduling; the operator can interrupt anytime.
