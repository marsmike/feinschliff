# feinblick

Codebase intelligence for the feinschmiede plugin family. feinblick orchestrates
real static-analysis engines (CytoScnPy, Tach, agnix) plus native repo/skill
rules into one normalized `Finding` model, an audit gate with changed-code
attribution and baselines, and an agent-consumable report — so an AI contributor
gets Python code health and Claude-skill health in a single pass.

feinblick is a standalone, stdlib-only plugin: it exposes the clean `feinblick`
CLI and never asks callers to reach into its files. Engines are *invoked* (via
`uvx`/`npx`), never vendored.

## Install

```bash
/plugin marketplace add marsmike/feinschmiede   # once per machine
/plugin install feinblick@feinschmiede
```

## Usage

```bash
feinblick audit     # gate: run every engine + native rule, apply the baseline, emit a verdict
feinblick check     # report findings without failing the build
feinblick health    # 0–100 codebase + skills health score
```

`check` takes a domain (`code` / `skills` / `all`) and a `--format`; `audit`
adds the gate flags below.

## What it looks at

Two domains, pooled into one `Finding` model:

- **Code** — dead/unused code, duplication, complexity (CytoScnPy); circular
  dependencies and module-boundary violations (Tach).
- **Skills** — `SKILL.md` frontmatter, progressive-disclosure budget, and
  description/trigger quality (agnix when available, plus feinblick's own
  native rules), and the `feinschliff/examples/` repo-discipline allowlist.

## The four reporters

Every command renders through one of four reporters (`--format`):

| Format     | What it is                                                            |
| ---------- | -------------------------------------------------------------------- |
| `terminal` | Human-readable, grouped by severity, ending in the verdict line.     |
| `json`     | Agent-consumable — every finding with its `actions[]` + `auto_fixable`, plus the health score, verdict, and run metadata. |
| `sarif`    | SARIF 2.1.0 (`runs[0].tool.driver.name == "feinblick"`) for code-scanning / CI upload. Synthesized natively — neither engine emits feinblick-shaped SARIF. |
| `markdown` | A dated, Obsidian-friendly report (health score + a table per category + verdict). |

## The audit gate + baselines

`feinblick audit` turns findings into a build verdict — `pass` / `warn` /
`fail`:

- `--gate all` gates the full deduped finding set; `--gate introduced` gates
  only findings attributed to changed code (`--changed-since <ref>` or
  `--diff-file <path>`).
- A **baseline** (`.feinblick/baseline.json`, a set of finding fingerprints) lets
  you accept pre-existing debt so only *newly introduced* findings can fail the
  build. Write one with `feinblick baseline save`. Fingerprints are stable
  across unrelated edits — they exclude absolute line numbers and anchor on the
  symbol, so moving code around doesn't re-flag it.
- `gate.fail_on` / `gate.warn_on` (severities) and `gate.tolerance` (an allowed
  count) are configured in `feinblick.toml`. `audit` exits `0` for pass/warn and
  `1` for fail.

## Configuration

Zero-config first run uses baked feinschliff defaults. An optional
`feinblick.toml` at the repo root overrides code/skill roots, the engine lists,
the skill line budget, the gate, and pinned engine versions.

## Pinned engine versions

feinblick pins the engines it shells out to, so results are reproducible:

| Engine      | Pinned version | Invoked via    |
| ----------- | -------------- | -------------- |
| CytoScnPy   | `1.2.23`       | `uvx`          |
| Tach        | `0.35.0`       | `uvx`          |
| agnix       | `latest`       | `npx -y`       |

Override any of them under `[engines.<name>]` in `feinblick.toml`
(`version = "…"`).

## The Node / npx caveat

agnix is a Node tool, invoked via `npx`. **If Node is not installed, the agnix
adapter degrades gracefully**: feinblick records the engine as unavailable
(with a reason), keeps going, and produces a partial report — it never crashes.
**Skill validation still works without Node**, because feinblick's *native* skill
rules (frontmatter, progressive-disclosure budget, description/trigger quality)
mirror the agnix checks and run with the Python stdlib alone. So on a no-Node
machine you still get skill findings; agnix only adds its extra rule coverage
when Node is present.
