---
name: feinblick
description: Audit a repo for dead code, cycles, complexity, and broken Claude skills, then read the findings. Use when verifying code or skill health in CI or an agent loop.
---

# feinblick — codebase intelligence

`feinblick` is a command on your PATH. It unifies Python static analysis
(CytoScnPy, Tach) and Claude-skill validation into one finding model, an audit
gate, and a health score. Call it as a bare command — never a file path or `cd`.

In CI or an agent loop, gate on findings introduced since the base branch and
read the machine output:

```bash
feinblick audit --changed-since origin/main --format json
```

Each entry in `findings[]` carries `actions[]` with an `auto_fixable` flag and,
when available, an `engine_fix_cmd` — act on those first.

For a full, un-gated report over code, skills, or both:

```bash
feinblick check code      # or: feinblick check skills | feinblick check all
```

For just the 0-100 health score and its hotspots:

```bash
feinblick health
```

`audit` exits non-zero only when the gate fails, so it is safe to wire directly
into a pipeline step.
