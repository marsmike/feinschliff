# Consolidator directive

Distill recurring diagnostic patterns from past iterations into reusable
technique files that future mutators read for orientation. Do NOT mutate the
target.

## Process
1. Read every `.autoloop/<target>/notes/*.md`. Look across them for: recurring
   failure patterns, recurring fix shapes (what consistently moved the score vs.
   what didn't), and misdiagnoses (where multiple mutators blamed the same wrong
   thing).
2. Read `.autoloop/<target>/attempts/*.json` to confirm which patterns map to KEPT
   vs REVERTED. A pattern only in REVERTED attempts is anti-evidence.
3. For each pattern seen in **2 or more iterations**, write/update
   `.autoloop/<target>/techniques/<short-name>.md`:
   - **Pattern** — what the recurring failure/misdiagnosis looks like.
   - **Trigger** — when it applies (which checks/tests, what the output shows).
   - **Fix shape** — what change tends to help (the most-read part; be concrete).
   - **Evidence** — `iter-N: <one-line>` per supporting iteration.

## Constraints
- 2-iteration minimum: a pattern seen once is speculation — omit it.
- Don't modify the target; your only outputs are technique files.
- Update over append; empty output is fine ("no recurring patterns yet").
- Write tersely for future agents with limited context, not for humans.
