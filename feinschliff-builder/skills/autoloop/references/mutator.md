# Mutator directive

You are mutating a target to fix eval failures. Analyze, diagnose, apply ONE fix.

## Process
1. Skim `.autoloop/<target>/notes/` and `.autoloop/<target>/techniques/` first —
   prior iterations recorded what they tried and the patterns they found. Do not
   re-discover.
2. Read the grader output (`.autoloop/<target>/results/grades.json`) — find which
   checks failed, on which tests.
3. Read the ACTUAL failing artifacts in `.autoloop/<target>/results/<name>.<ext>`.
   Look at the output yourself; diagnose what the skill produced wrong.
4. Read the target SKILL.md (+ references) to find the instruction that produced
   the failure.
5. Identify ONE specific improvement addressing the biggest failure pattern.
6. Apply it to the SKILL file(s).
7. Write `.autoloop/<target>/notes/iter-N.md`:
   - **What I tried** — one line.
   - **Failure pattern observed** — 2-3 lines, drawn from the artifacts.
   - **Hypothesis for next iteration** — 1-2 lines.

## Constraints
- ONE logical change per iteration.
- Anti-overfitting: improve the skill's GENERAL quality. If you write "when asked
  about X, do Y" you are overfitting — find the general principle the skill lacks.
- Simplicity bias: prefer deleting confusing/contradictory instructions over
  adding new ones; fewer lines at equal score wins; no speculative additions.
  Every line is a line the generating agent must process — bloated skills degrade.
