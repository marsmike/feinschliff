"""feinblick CLI — argparse dispatch for the codebase-intelligence surface.

Subcommands (each handler returns a process exit code):

* ``audit`` — run the gated pipeline over code + skills; exit ``1`` on a failing
  verdict, ``0`` otherwise.
* ``check`` — run the pipeline un-gated over a domain (``code``/``skills``/``all``)
  and print the report (always exit ``0`` unless a ``--strict`` tooling error).
* ``health`` — print the synthesized 0-100 score plus the finding hotspots.
* ``baseline save`` — write the current findings' fingerprints as the baseline.
* ``skill emit`` — materialize the shipped agent-skill + slash commands.
* ``init`` — scaffold a starter ``feinblick.toml`` (idempotent).
* ``explain`` — look up a finding by fingerprint or rule id and print its detail.

``main`` resolves the repo root by walking up from the cwd for a ``.git`` marker
and wires each subparser's handler via ``set_defaults(_handler=...)``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from feinblick import __version__, baseline
from feinblick.config import load_config
from feinblick.orchestrator import run_pipeline
from feinblick.report import render
from feinblick.runner import Runner

# Starter config written by ``init`` — the baked feinschliff defaults as TOML.
STARTER_TOML = """\
# feinblick configuration — see `feinblick --help`. All keys are optional;
# anything omitted falls back to the baked feinschliff defaults.

[code]
roots = ["feinschliff/lib"]
test_globs = ["**/tests/**", "**/test_*.py"]
engines = ["cytoscnpy", "tach"]

[skills]
roots = ["."]
engines = ["agnix"]
skill_md_max_lines = 500

[gate]
fail_on = ["error"]
warn_on = ["warning"]
baseline = ".feinblick/baseline.json"
tolerance = 0

[engines.cytoscnpy]
version = "1.2.23"

[engines.tach]
version = "0.35.0"
"""


def _find_repo_root(start: Path) -> Path:
    """Walk up from ``start`` for a ``.git`` marker; fall back to ``start``."""
    start = Path(start).resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


def _runner(repo_root: Path) -> Runner:
    return Runner(repo_root=repo_root, cache=False)


# --------------------------------------------------------------------------- #
# handlers
# --------------------------------------------------------------------------- #


def _handle_audit(args) -> int:
    repo_root = _find_repo_root(Path.cwd())
    config = load_config(repo_root)
    result = run_pipeline(
        repo_root,
        config,
        domains={"code", "skills"},
        runner=_runner(repo_root),
        gate=args.gate,
        since_ref=args.changed_since,
        diff_file=args.diff_file,
        strict=args.strict,
    )
    if args.baseline:
        # informational override applied by the operator via flag is honored at
        # the config layer; nothing further to do here for v1.
        pass
    print(render(args.format, result.findings, result.verdict, result.health, result.meta))
    return 1 if result.verdict == "fail" else 0


def _handle_check(args) -> int:
    repo_root = _find_repo_root(Path.cwd())
    config = load_config(repo_root)
    domains = {"code", "skills"} if args.domain == "all" else {args.domain}
    result = run_pipeline(
        repo_root,
        config,
        domains=domains,
        runner=_runner(repo_root),
        gate=None,
        strict=args.strict,
    )
    print(render(args.format, result.findings, result.verdict, result.health, result.meta))
    return 0


def _handle_health(args) -> int:
    repo_root = _find_repo_root(Path.cwd())
    config = load_config(repo_root)
    result = run_pipeline(
        repo_root, config, domains={"code", "skills"}, runner=_runner(repo_root), gate=None
    )
    health = result.health
    print(f"Health: {health['score']}/100")
    hotspots = health.get("hotspots", [])
    if hotspots:
        print("Hotspots:")
        for h in hotspots:
            print(f"  {h['path']}  ({h['findings']} findings)")
    else:
        print("No hotspots.")
    return 0


def _handle_baseline_save(args) -> int:
    repo_root = _find_repo_root(Path.cwd())
    config = load_config(repo_root)
    result = run_pipeline(
        repo_root, config, domains={"code", "skills"}, runner=_runner(repo_root), gate=None
    )
    path = config.gate.baseline
    if not path.is_absolute():
        path = repo_root / path
    baseline.save(path, result.findings)
    count = len({f.fingerprint for f in result.findings})
    print(f"Baseline saved: {count} fingerprints -> {path}")
    return 0


def _handle_skill_emit(args) -> int:
    # skillgen lands in a later task; import lazily so the CLI imports without it.
    from feinblick import skillgen

    out = Path(args.out) if args.out else _default_skill_out()
    skillgen.emit(out)
    print(f"Emitted agent-skill + commands -> {out}")
    return 0


def _default_skill_out() -> Path:
    """The feinblick plugin directory (two levels up from this module's package)."""
    return Path(__file__).resolve().parents[2]


def _handle_init(args) -> int:
    repo_root = _find_repo_root(Path.cwd())
    wrote: list[str] = []

    path = repo_root / "feinblick.toml"
    if path.exists():
        print(f"feinblick.toml already exists: {path}")
    else:
        path.write_text(STARTER_TOML)
        wrote.append(str(path))

    # Scaffold a starter tach.toml too: tach needs an authored module map at the
    # repo root to do boundary/circular analysis (with only source_roots it just
    # warns). Seed source_roots from the configured code roots; leave [[modules]]
    # for the operator to declare.
    from feinblick.adapters.tach import scaffold_tach_toml

    config = load_config(repo_root)
    tach_path = repo_root / "tach.toml"
    if tach_path.exists():
        print(f"tach.toml already exists: {tach_path}")
    else:
        tach_path.write_text(scaffold_tach_toml(config.code.roots))
        wrote.append(str(tach_path))

    for p in wrote:
        print(f"Wrote {p}")
    return 0


def _handle_explain(args) -> int:
    repo_root = _find_repo_root(Path.cwd())
    config = load_config(repo_root)
    result = run_pipeline(
        repo_root, config, domains={"code", "skills"}, runner=_runner(repo_root), gate=None
    )
    key = args.key
    match = next(
        (f for f in result.findings if f.fingerprint == key or f.rule_id == key),
        None,
    )
    if match is None:
        print(f"No finding matches {key!r} (try a fingerprint or rule id).")
        return 0
    print(f"{match.rule_id or '(no rule)'}  [{match.severity.value}]  {match.fingerprint}")
    print(f"  {match.location.path}"
          + (f":{match.location.line}" if match.location.line else ""))
    print(f"  {match.message}")
    if match.evidence:
        print(f"  evidence: {match.evidence}")
    for action in match.actions:
        fix = f"  ($ {action.engine_fix_cmd})" if action.engine_fix_cmd else ""
        print(f"  action: {action.description}{fix}")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="feinblick", description="Codebase intelligence: Python + Claude skills."
    )
    p.add_argument("--version", action="version", version=f"feinblick {__version__}")
    p.set_defaults(_handler=None)
    sub = p.add_subparsers(dest="command")

    audit = sub.add_parser("audit", help="Gated audit over code + skills.")
    src = audit.add_mutually_exclusive_group()
    src.add_argument("--changed-since", metavar="REF", default=None,
                     help="Attribute introduced findings to changes since this git ref.")
    src.add_argument("--diff-file", metavar="PATH", default=None,
                     help="Attribute introduced findings from a unified diff file.")
    audit.add_argument("--gate", choices=["introduced", "all"], default="introduced")
    audit.add_argument("--format", choices=["terminal", "json", "sarif", "markdown"],
                       default="terminal")
    audit.add_argument("--baseline", metavar="PATH", default=None)
    audit.add_argument("--strict", action="store_true")
    audit.set_defaults(_handler=_handle_audit)

    check = sub.add_parser("check", help="Un-gated report over a domain.")
    check.add_argument("domain", nargs="?", choices=["code", "skills", "all"], default="all")
    check.add_argument("--format", choices=["terminal", "json", "sarif", "markdown"],
                       default="terminal")
    check.add_argument("--strict", action="store_true")
    check.set_defaults(_handler=_handle_check)

    health = sub.add_parser("health", help="Print the 0-100 health score + hotspots.")
    health.add_argument("--format", choices=["terminal", "json", "sarif", "markdown"],
                        default="terminal")
    health.set_defaults(_handler=_handle_health)

    bl = sub.add_parser("baseline", help="Manage the accepted-finding baseline.")
    bl_sub = bl.add_subparsers(dest="baseline_command")
    bl_save = bl_sub.add_parser("save", help="Write the current findings as the baseline.")
    bl_save.add_argument("--gate", choices=["all"], default="all")
    bl_save.set_defaults(_handler=_handle_baseline_save)

    skill = sub.add_parser("skill", help="Agent-skill tooling.")
    skill_sub = skill.add_subparsers(dest="skill_command")
    skill_emit = skill_sub.add_parser("emit", help="Emit the shipped agent-skill + commands.")
    skill_emit.add_argument("--out", metavar="DIR", default=None)
    skill_emit.set_defaults(_handler=_handle_skill_emit)

    init = sub.add_parser("init", help="Scaffold a starter feinblick.toml.")
    init.set_defaults(_handler=_handle_init)

    explain = sub.add_parser("explain", help="Explain a finding by fingerprint or rule id.")
    explain.add_argument("key")
    explain.set_defaults(_handler=_handle_explain)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
