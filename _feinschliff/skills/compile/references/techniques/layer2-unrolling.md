# Layer-2 unrolling for tabular content

## Pattern
A layout that hard-codes N rows (e.g. `timeline-gantt` with 3 task rows,
`table` with 3 body rows, `pie-trio` with 3 pies) will silently truncate
content that exceeds N. The DSL's slot interpolation does NOT auto-expand
arrays into primitives — `{{ tasks[7].label }}` will just be empty if
the layout only authored rows 0..2.

## Trigger
Production content has more rows than the layout author imagined. Source
slides actually have 10 task rows, your layout has 3. The first 3 render
correctly; the next 7 vanish.

## Fix shape
Two options:

**Short-term (within one layout):** author 10 rows up front with `if:{{
items[N] }}` gates so unused rows are suppressed. Works but bloats the
DSL and caps at whatever N you picked.

**Long-term (toolkit feature):** Layer-2 unrolling at compose time. The
layout author writes ONE primitive template with a `for-each:` directive,
the expander unrolls it into N primitives based on the content array.
Example:
```
for-each tasks: task at y={{ 290 + index * 56 }}:
  text 75,{{ y }} style:body "{{ task.label }}"
  line 567,{{ y+6 }} 1810,{{ y+6 }} stroke:{{ task.tint }}
```

## For `feinschliff:compile`
Detect tabular content patterns in the source (>5 repeating rows of
similar primitives). Emit `for-each:` blocks instead of hand-unrolled
rows. Until Layer-2 lands upstream, scaffolder should at minimum author
the max-row variant (e.g. 12 rows with `if:` gates) so production
content of any size up to 12 renders correctly.

## Evidence
- timeline-gantt scaffold pass 1: 3 hard-coded rows. Source had 10
  rows. 7 rows vanished in production. Diff: 14%.
- Manual expansion to 10 rows with `if:` gates closed the visible
  truncation. Diff: same 14% (the rest is font + bar-position drift,
  category (c)/(b)).
- `pie-trio` and `table` have the same hardcoded-N pattern. Layer-2
  unrolling would fix all three at once.
