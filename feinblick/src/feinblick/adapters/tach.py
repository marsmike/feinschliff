"""Tach adapter — module boundary violations + circular dependencies.

``tach check --output json`` emits **two disjoint shapes**: a JSON **array** of
``{"Located": {...}}`` rows for boundary violations, versus a flat
``{"error", "dependencies"}`` **object** when a cycle is detected. Config/fatal
errors (e.g. a missing ``tach.toml``) print **text on stderr** with empty
stdout, so an empty stdout always means "no findings" here. ``tach init/mod`` is
interactive, so feinblick hand-writes a ``tach.toml`` via
:func:`scaffold_tach_toml` rather than shelling out to it.
"""

from __future__ import annotations

import json

from feinblick.adapters.base import RawOutput, Runner, Targets
from feinblick.model import Category, Domain, Finding, Location, Severity


def scaffold_tach_toml(roots: list[str]) -> str:
    """Render a minimal, zero-config ``tach.toml`` from the scan roots.

    Cycle detection works zero-config, so ``forbid_circular_dependencies`` is on
    by default. Boundary enforcement needs an authored dependency map, so each
    root is declared as a module with ``depends_on = []`` left for the operator
    to fill in.
    """
    lines: list[str] = []
    root_list = ", ".join(f'"{r}"' for r in roots)
    lines.append(f"source_roots = [{root_list}]")
    lines.append("forbid_circular_dependencies = true")
    lines.append("")
    for r in roots:
        lines.append("[[modules]]")
        lines.append(f'path = "{r}"')
        lines.append("depends_on = []")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class TachEngine:
    name = "tach"

    def ensure_available(
        self, runner: Runner, targets: Targets, version: str
    ) -> tuple[bool, str]:
        if not runner.tool_available("uvx"):
            return (False, "uvx not found — tach requires uv; skipping code engine")
        # tach needs an authored module map (tach.toml at the repo root) to do
        # meaningful boundary/circular analysis; with only source_roots it emits
        # config warnings, not findings. Treat a missing tach.toml as "not
        # applicable to this repo" rather than running it for noise.
        if not (targets.repo_root / "tach.toml").is_file():
            return (
                False,
                "no tach.toml at repo root — run `feinblick init` to scaffold one "
                "(declare modules to enable boundary/circular checks)",
            )
        return (True, "")

    def run(self, runner: Runner, targets: Targets, version: str) -> RawOutput:
        # ensure_available guarantees a repo-root tach.toml. tach discovers it
        # from the cwd (it has no project-root flag), so run with cwd=repo_root.
        args = ["check", "--output", "json"]
        argv = runner.uvx("tach", version, args)
        return runner.run_raw(argv, cache_key="tach", cwd=targets.repo_root)

    def parse(self, raw: RawOutput, targets: Targets) -> list[Finding]:
        if not raw.stdout.strip():
            # Config/fatal errors go to stderr; empty stdout == no findings.
            return []
        try:
            data = json.loads(raw.stdout)
        except (ValueError, TypeError):
            return []

        if isinstance(data, dict) and "error" in data:
            return self._parse_circular(data, targets)
        if isinstance(data, list):
            return self._parse_boundary(data, targets)
        return []

    def _parse_circular(self, data: dict, targets: Targets) -> list[Finding]:
        deps = data.get("dependencies") or []
        chain = " -> ".join(str(d) for d in deps)
        root = targets.roots[0] if targets.roots else "."
        return [
            Finding(
                domain=Domain.CODE,
                category=Category.CIRCULAR_DEP,
                severity=Severity.ERROR,
                location=Location(path=root),
                message=f"Circular dependency: {chain}",
                source_engine=self.name,
                rule_id="TACH-CYCLE",
            )
        ]

    def _parse_boundary(self, data: list, targets: Targets) -> list[Finding]:
        out: list[Finding] = []
        for row in data:
            located = (row or {}).get("Located") or {}
            code = (located.get("details") or {}).get("Code") or {}
            if not code:
                continue
            variant, payload = next(iter(code.items()))
            payload = payload or {}
            dependency = payload.get("dependency", "")
            usage = payload.get("usage_module", "")
            definition = payload.get("definition_module", "")
            message = (
                f"Module '{usage}' cannot depend on '{definition}' "
                f"(uses '{dependency}')"
            )
            out.append(
                Finding(
                    domain=Domain.CODE,
                    category=Category.BOUNDARY,
                    severity=Severity.from_engine(located.get("severity", "")),
                    location=Location(
                        path=located.get("file_path", ""),
                        line=located.get("line_number"),
                        symbol=dependency or None,
                    ),
                    message=message,
                    source_engine=self.name,
                    rule_id=f"TACH-{variant}",
                )
            )
        return out

    def is_error(self, raw: RawOutput) -> str | None:
        # A clean tach run emits "[]"; a violation emits JSON; a config/fatal
        # error emits empty stdout with a plain-text message on stderr. So blank
        # stdout means tach failed, not "no findings".
        if not raw.stdout.strip():
            return raw.stderr.strip() or f"tach exited {raw.exit_code} with no output"
        return None


ENGINE = TachEngine()
