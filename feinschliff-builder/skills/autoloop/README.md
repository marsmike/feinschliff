# `autoloop` — deterministic improvement loop for skills

> **Loops are the new prompts.** Instead of one-shot prompting, you run a
> self-terminating improvement loop that drives a target toward a measurable
> goal — generating output, scoring it, and keeping only the changes that help.

`autoloop` makes **Claude Code itself** the loop runner. It runs the Karpathy
loop — `measure → mutate one thing → keep or revert → consolidate → (redirect on
plateau)` — over a target, scored by a deterministic grader
(`feinschliff-builder eval`). The only new *code* is that grader; the loop is
prose in [`SKILL.md`](SKILL.md), which is the canonical, executable source of
truth (this README is the human intro).

## `autoloop` vs the built-in `/goal`

Claude Code has a **built-in `/goal`** command: a generic "keep working across
turns until a stated condition is met, judged each turn by a fast model." Bare
`/goal` always invokes that built-in — **not** this skill.

`autoloop` is the *domain method*: the deterministic grader + the
mutate / keep-revert / consolidate recipe for feinschliff skills. It **rides**
the built-in rather than reinventing it:

- **Run the method:** `/feinschliff-builder:autoloop <target>` (namespaced — it
  can't collide with the built-in `/goal`).
- **Persist across turns (unattended):** pair it with the built-in
  `/goal "<condition>"`. The built-in owns continuation; `autoloop` is the
  per-iteration body it runs. We deliberately do **not** hand-roll scheduling.

```
# one session, runs to its own stop/budget:
/feinschliff-builder:autoloop excalidraw

# unattended, the built-in keeps it going until the condition holds:
/goal the feinschliff-builder eval on the excalidraw skill exits 0
```

v1 targets are the diagram skills `excalidraw` and `svg` (graded
deterministically — no LLM, no render, no API cost).

## How it works (one screen)

Each iteration:

1. **Measure** — for every test in the target skill's `evals/evals.json`, a
   *fresh subagent* (given only the skill + the test prompt) generates an
   artifact via `feinbild <skill> expand …`. Then the grader scores them:
   `feinschliff-builder eval <skill-dir> --results-dir .autoloop/<target>/results`.
   Fresh subagents are deliberate — they isolate the *skill text's* effect from
   the controller's own knowledge, so the score reflects the skill, not Claude.
2. **Mutate** — read the failing checks + the real artifacts, apply **one**
   targeted edit to the skill (simplicity bias, anti-overfitting).
3. **Keep / revert** — score up (or a simplicity-win) → `git commit`; else
   `git checkout --`. The experiment branch only accumulates wins.
4. **Consolidate** (every few iterations) — distil recurring patterns into
   `techniques/*.md`. This is the loop's *learning*: it persists across runs
   with no model training.

The per-role directives live in [`references/`](references/)
(`mutator.md`, `redirection.md`, `consolidator.md`). See [`SKILL.md`](SKILL.md)
for the exact thresholds and stop conditions.

## The grader: `feinschliff-builder eval`

The grader is the deterministic half — it scores **already-generated** artifacts
(it never calls an LLM). Run `feinschliff-builder eval --help` for usage. It maps
each test to `<results-dir>/<test-name>.<ext>` and runs that test's `checks`,
returning a pooled `score` and writing `grades.json`. Exit codes: `0` all pass,
`1` some fail, `2` malformed `evals.json`.

## Adding a target

A target is anything with a `evals/evals.json` and a way to grade its generated
output. To add a diagram-style skill:

1. Write `<skill>/evals/evals.json` (see `feinbild/skills/excalidraw/evals/`):
   ```json
   { "skill": "excalidraw", "version": 1,
     "tests": [ { "name": "five-box-flow", "prompt": "…",
                  "checks": ["valid-excalidraw-json", "rectangles==5",
                             "arrows==4", "uses-semantic-colors"] } ] }
   ```
2. Use the **check mini-language** the grader understands:
   - Named: `valid-excalidraw-json`, `valid-svg`, `has-viewBox`,
     `uses-semantic-colors`.
   - Count: `<element><op><int>` where element ∈ {`rectangles`, `ellipses`,
     `diamonds`, `arrows`, `text`, `lines`} and op ∈ {`==`, `>=`, `<=`, `>`,
     `<`} — e.g. `rectangles==5`, `arrows>=4`.

New check kinds live in
[`feinschliff_builder/eval/checks.py`](../../feinschliff_builder/eval/checks.py);
new target *graders* (deck, DSL template, framework code) plug in next to it.

## Safety / autonomy model

- **Branch-isolated** — all work happens on `autoloop/<target>/<timestamp>`,
  never `main`. The operator reviews the branch and merges deliberately.
- **Revert-by-default** — any non-improving edit is discarded, so the branch
  only accumulates wins.
- **Budget-bounded** — a hard iteration cap; stops on plateau-after-redirect.
- **Honest residual report** — every run writes `RESIDUAL.md` accounting for
  what is still unresolved. Never claims a clean pass the grader did not confirm.
- **Gitignored working state** — `.autoloop/<target>/{results,attempts,notes,
  techniques}/` (the kept mutations are the real artifact, committed to the
  branch).

## Status

- **v1 (now):** deterministic diagram grader + the loop, on `excalidraw`/`svg`.
- **Next (follow-on plans):** DSL-template target (`brand_visual_diff`), deck
  target (`deck verify-collate`), framework-code target (brief-corpus
  build-clean + `feinblick health`) — all reuse this same loop machinery,
  grading on **generated** results.
