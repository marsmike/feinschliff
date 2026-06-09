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

    def ensure_available(self, runner: Runner, version: str) -> tuple[bool, str]:
        if not runner.tool_available("uvx"):
            return (False, "uvx not found — tach requires uv; skipping code engine")
        return (True, "")

    def run(self, runner: Runner, targets: Targets, version: str) -> RawOutput:
        repo_root = targets.repo_root
        # Use a repo-root tach.toml when present; otherwise scaffold one into the
        # gitignored cache region and point tach at it via --project-root.
        if (repo_root / "tach.toml").is_file():
            target_dir = repo_root
        else:
            cache_dir = repo_root / ".feinblick"
            cache_dir.mkdir(parents=True, exist_ok=True)
            toml_path = cache_dir / "tach.toml"
            if not toml_path.is_file():
                toml_path.write_text(scaffold_tach_toml(targets.roots))
            target_dir = cache_dir
        args = ["check", "--output", "json", "--project-root", str(target_dir)]
        argv = runner.uvx("tach", version, args)
        return runner.run_raw(argv, cache_key="tach", cwd=repo_root)

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


ENGINE = TachEngine()
