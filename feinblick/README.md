# feinblick

Codebase intelligence for the feinschmiede plugin family. feinblick orchestrates
real static-analysis engines (CytoScnPy, Tach, agnix) plus native repo/skill
rules into one normalized `Finding` model, an audit gate with changed-code
attribution and baselines, and an agent-consumable report — so an AI contributor
gets Python code health and Claude-skill health in a single pass.

feinblick is a standalone, stdlib-only plugin: it exposes the clean `feinblick`
CLI and never asks callers to reach into its files.

## Usage

```bash
feinblick audit     # gate: run every engine + native rule, apply the baseline, emit a verdict
feinblick check     # report findings without failing the build
feinblick health    # 0–100 codebase + skills health score
```
