"""Emit feinblick's shipped agent-skill and slash commands from in-code templates.

:func:`emit` writes ``<out>/skills/feinblick/SKILL.md`` plus
``<out>/commands/{audit,check,health}.md`` from the static templates below and
returns the written paths. It is idempotent: the templates carry no timestamps
or other moving parts, so re-emitting is byte-for-byte identical.

The ``SKILL.md`` is deliberately authored to pass feinblick's *own* native skill
rules (:func:`feinblick.rules.skills.check_skills`) — its frontmatter has exactly
``name`` + ``description``, ``name`` equals the ``skills/feinblick/`` directory,
the description carries a ``Use when ...`` trigger and is free of angle brackets,
and the body stays well under the progressive-disclosure budget. Commands mirror
feinbild's format: frontmatter ``name`` + quoted ``description`` +
``user_invocable: true``, then a ``# /<cmd>`` heading, one line, and a bash block
invoking the bare ``feinblick`` command (never a file path or ``cd``).
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# templates (static — keep the SKILL.md command-first and <= 50 lines)
# --------------------------------------------------------------------------- #

# The frontmatter ``description`` must be one physical output line (the parser
# splits on the first colon, per line). Built via implicit string concatenation
# so no *source* line exceeds the lint line-length.
_DESCRIPTION = (
    "Audit a repo for dead code, cycles, complexity, and broken Claude skills, "
    "then read the findings. Use when verifying code or skill health in CI or an agent loop."
)

SKILL_MD = f"""\
---
name: feinblick
description: {_DESCRIPTION}
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
"""

# Each command: (name, quoted description, one-line summary, bash invocation).
_COMMANDS = {
    "audit": (
        '"Gate a repo on newly introduced findings. Usage: /audit [--changed-since <ref>]"',
        "Run the gated audit and emit machine-readable findings:",
        "feinblick audit --changed-since origin/main --format json",
    ),
    "check": (
        '"Report code + skill findings without gating. Usage: /check [code|skills|all]"',
        "Run the full un-gated report over a domain:",
        "feinblick check all",
    ),
    "health": (
        '"Print the 0-100 codebase health score and hotspots. Usage: /health"',
        "Print the synthesized health score and its hotspots:",
        "feinblick health",
    ),
}


def _command_md(name: str) -> str:
    description, summary, invocation = _COMMANDS[name]
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "user_invocable: true\n"
        "---\n"
        "\n"
        f"# /{name}\n"
        "\n"
        f"{summary}\n"
        "\n"
        "```bash\n"
        f"{invocation}\n"
        "```\n"
    )


def emit(out_dir: Path | str) -> list[Path]:
    """Write the agent-skill + slash commands under ``out_dir``; return the paths.

    Creates ``skills/feinblick/SKILL.md`` and ``commands/{audit,check,health}.md``
    relative to ``out_dir``, making parent directories as needed. Idempotent.
    """
    out_dir = Path(out_dir)
    written: list[Path] = []

    skill_md = out_dir / "skills" / "feinblick" / "SKILL.md"
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text(SKILL_MD, encoding="utf-8")
    written.append(skill_md)

    commands_dir = out_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    for name in ("audit", "check", "health"):
        path = commands_dir / f"{name}.md"
        path.write_text(_command_md(name), encoding="utf-8")
        written.append(path)

    return written
