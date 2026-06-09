"""CytoScnPy adapter — dead code, clones, and complexity.

CytoScnPy (``schema_version:"2"``) reports dead code in per-kind arrays with no
severity or rule_id (we synthesize both), reports each clone pair twice
(``is_duplicate`` true on one side, false on the canonical other — we dedupe to
one Finding per pair), and surfaces complexity via ``--quality --max-complexity``
as ``CSP-Q3xx`` rows with ALL-CAPS severities. Secrets/danger/taint arrays are
out of v1 scope and intentionally skipped. The engine exits nonzero with valid
JSON when findings exist, so the orchestrator owns exit-code interpretation; the
parser only inspects ``raw.stdout``.
"""

from __future__ import annotations

import json
import os

from feinblick.adapters.base import RawOutput, Runner, Targets
from feinblick.model import Action, Category, Domain, Finding, Location, Severity

# Per-kind dead-code array name -> synthesized rule_id.
_DEAD_KINDS: dict[str, str] = {
    "unused_functions": "CSP-U001",
    "unused_methods": "CSP-U002",
    "unused_classes": "CSP-U003",
    "unused_imports": "CSP-U004",
    "unused_variables": "CSP-U005",
    "unused_parameters": "CSP-U006",
}

_FIX_CMD = "cytoscnpy <roots> --make-whitelist"


class CytoScnPyEngine:
    name = "cytoscnpy"

    def ensure_available(
        self, runner: Runner, targets: Targets, version: str
    ) -> tuple[bool, str]:
        if not runner.tool_available("uvx"):
            return (False, "uvx not found — cytoscnpy requires uv; skipping code engine")
        return (True, "")

    def run(self, runner: Runner, targets: Targets, version: str) -> RawOutput:
        exclude = sorted({os.path.dirname(g).split("/")[0] for g in targets.test_globs
                          if os.path.dirname(g)})
        args = [
            *targets.roots,
            "--json",
            "--clones",
            "--clone-similarity",
            "0.8",
            "--quality",
            "--max-complexity",
            "10",
        ]
        for folder in exclude:
            args += ["--exclude-folders", folder]
        argv = runner.uvx("cytoscnpy", version, args)
        return runner.run_raw(argv, cache_key="cytoscnpy", cwd=targets.repo_root)

    def parse(self, raw: RawOutput, targets: Targets) -> list[Finding]:
        try:
            data = json.loads(raw.stdout)
        except (ValueError, TypeError):
            return []
        if not isinstance(data, dict):
            return []

        findings: list[Finding] = []
        findings += self._parse_dead_code(data, targets)
        findings += self._parse_clones(data, targets)
        findings += self._parse_quality(data, targets)
        return findings

    def _rel(self, file: str, targets: Targets) -> str:
        try:
            return os.path.relpath(file, targets.repo_root)
        except (ValueError, TypeError):
            return file or ""

    def _parse_dead_code(self, data: dict, targets: Targets) -> list[Finding]:
        out: list[Finding] = []
        for kind, rule_id in _DEAD_KINDS.items():
            for row in data.get(kind, []) or []:
                name = row.get("name")
                confidence = row.get("confidence")
                definite = row.get("category") == "DefinitelyUnused"
                severity = Severity.WARNING if definite else Severity.INFO
                out.append(
                    Finding(
                        domain=Domain.CODE,
                        category=Category.DEAD_CODE,
                        severity=severity,
                        location=Location(
                            path=self._rel(row.get("file", ""), targets),
                            line=row.get("line"),
                            col=row.get("col"),
                            symbol=name,
                        ),
                        message=row.get("message", f"Unused {kind}: {name}"),
                        source_engine=self.name,
                        rule_id=rule_id,
                        evidence=f"confidence={confidence}",
                        actions=[
                            Action(
                                description=f"Remove unused {kind}",
                                auto_fixable=True,
                                engine_fix_cmd=_FIX_CMD,
                            )
                        ],
                    )
                )
        return out

    def _parse_clones(self, data: dict, targets: Targets) -> list[Finding]:
        out: list[Finding] = []
        for row in data.get("clones", []) or []:
            # Dedupe: keep only the canonical `is_duplicate==True` side of each pair.
            if not row.get("is_duplicate"):
                continue
            related = row.get("related_clone") or {}
            related_file = self._rel(related.get("file", ""), targets)
            related_line = related.get("line")
            similarity = row.get("similarity")
            try:
                sim_pct = f"{float(similarity):.0%}"
            except (TypeError, ValueError):
                sim_pct = str(similarity)
            out.append(
                Finding(
                    domain=Domain.CODE,
                    category=Category.DUPLICATION,
                    severity=Severity.from_engine(row.get("severity", "")),
                    location=Location(
                        path=self._rel(row.get("file", ""), targets),
                        line=row.get("line"),
                        col=row.get("col"),
                        symbol=row.get("name"),
                    ),
                    message=row.get("message", "Duplicate code"),
                    source_engine=self.name,
                    rule_id=row.get("rule_id", "CSP-C100"),
                    evidence=f"{sim_pct} similar to {related_file}:{related_line}",
                    actions=[
                        Action(
                            description=row.get(
                                "suggestion", "Remove duplicate, import from original"
                            ),
                            auto_fixable=False,
                        )
                    ],
                )
            )
        return out

    def _parse_quality(self, data: dict, targets: Targets) -> list[Finding]:
        out: list[Finding] = []
        for row in data.get("quality", []) or []:
            rule_id = row.get("rule_id", "")
            # v1 quality focus = complexity (CSP-Q3xx). Skip anything else.
            if not rule_id.startswith("CSP-Q3"):
                continue
            out.append(
                Finding(
                    domain=Domain.CODE,
                    category=Category.COMPLEXITY,
                    severity=Severity.from_engine(row.get("severity", "")),
                    location=Location(
                        path=self._rel(row.get("file", ""), targets),
                        line=row.get("line"),
                        col=row.get("col"),
                    ),
                    message=row.get("message", "Complexity issue"),
                    source_engine=self.name,
                    rule_id=rule_id,
                )
            )
        return out

    def is_error(self, raw: RawOutput) -> str | None:
        # A successful cytoscnpy run always emits the JSON envelope on stdout
        # (even with zero findings). Blank or non-JSON stdout means the tool
        # failed — e.g. a missing scan root exits 1 with empty stdout.
        text = raw.stdout.strip()
        if not text:
            return raw.stderr.strip() or f"cytoscnpy exited {raw.exit_code} with no output"
        try:
            json.loads(text)
        except json.JSONDecodeError:
            detail = raw.stderr.strip()[:200]
            base = f"cytoscnpy emitted non-JSON output (exit {raw.exit_code})"
            return f"{base}: {detail}" if detail else base
        return None


ENGINE = CytoScnPyEngine()
