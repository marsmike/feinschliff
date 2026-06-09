"""agnix adapter — Claude-skill / repo-config linting via the JSON envelope.

agnix (a Node CLI) supports ``--format json`` and emits
``{version, files_checked, diagnostics[], summary}``. Severity is driven directly
off each diagnostic's ``level`` (already ``error``/``warning``/``info``); the
:class:`~feinblick.model.Category` is derived from the rule-code prefix via
:func:`category_for_rule`. agnix needs Node/``npx``, which is frequently absent;
:meth:`AgnixEngine.ensure_available` degrades cleanly to ``unavailable`` so
feinblick's native skill rules carry skill validation in its place.
"""

from __future__ import annotations

import json

from feinblick.adapters.base import RawOutput, Runner, Targets
from feinblick.model import Action, Category, Domain, Finding, Location, Severity

# AS-* (agent-skill) rule codes whose category is FRONTMATTER.
_AS_FRONTMATTER = {"001", "002", "003", "004", "005", "006", "011", "016", "017"}
# AS-* rule codes whose category is DESCRIPTION.
_AS_DESCRIPTION = {"008", "009"}
# AS-* rule codes whose category is PROGRESSIVE_DISCLOSURE.
_AS_PROGRESSIVE = {"012", "013", "015"}
# CC-MEM-* rule codes whose category is PROGRESSIVE_DISCLOSURE.
_MEM_PROGRESSIVE = {"003", "008", "009", "010", "014"}
# CC-SK-* rule codes whose category is HOOK (the rest map to FRONTMATTER).
_SK_HOOK = {"006", "007"}


def category_for_rule(code: str) -> Category:
    """Map an agnix rule code to a feinblick :class:`Category` by its prefix."""
    code = (code or "").strip()
    if code.startswith("AS-"):
        num = code[3:]
        if num in _AS_FRONTMATTER:
            return Category.FRONTMATTER
        if num in _AS_DESCRIPTION:
            return Category.DESCRIPTION
        if num in _AS_PROGRESSIVE:
            return Category.PROGRESSIVE_DISCLOSURE
        return Category.PROGRESSIVE_DISCLOSURE
    if code.startswith("CC-MEM-"):
        num = code[len("CC-MEM-"):]
        if num == "005":
            return Category.DESCRIPTION
        if num in _MEM_PROGRESSIVE:
            return Category.PROGRESSIVE_DISCLOSURE
        return Category.PROGRESSIVE_DISCLOSURE
    if code.startswith("CC-HK-"):
        return Category.HOOK
    if code.startswith("CC-SK-"):
        num = code[len("CC-SK-"):]
        if num in _SK_HOOK:
            return Category.HOOK
        return Category.FRONTMATTER
    if code.startswith("MCP-"):
        return Category.MCP
    if code.startswith("PE-"):
        return Category.DESCRIPTION
    return Category.PROGRESSIVE_DISCLOSURE


class AgnixEngine:
    name = "agnix"

    def ensure_available(self, runner: Runner, version: str) -> tuple[bool, str]:
        if not runner.tool_available("npx"):
            return (False, "npx not found — agnix requires Node.js; skipping skill engine")
        return (True, "")

    def run(self, runner: Runner, targets: Targets, version: str) -> RawOutput:
        args = ["--format", "json", "--target", "claude-code", *targets.roots]
        argv = runner.npx("agnix", version, args)
        return runner.run_raw(argv, cache_key="agnix", cwd=targets.repo_root)

    def parse(self, raw: RawOutput, targets: Targets) -> list[Finding]:
        if not raw.stdout.strip():
            return []
        try:
            data = json.loads(raw.stdout)
        except (ValueError, TypeError):
            return []
        if not isinstance(data, dict):
            return []

        findings: list[Finding] = []
        for diag in data.get("diagnostics", []) or []:
            rule = diag.get("rule")
            suggestion = diag.get("suggestion")
            actions = (
                [Action(description=suggestion, auto_fixable=False)] if suggestion else []
            )
            findings.append(
                Finding(
                    domain=Domain.SKILL,
                    category=category_for_rule(rule),
                    severity=Severity(diag.get("level")),
                    location=Location(
                        path=diag.get("file", ""),
                        line=diag.get("line"),
                        col=diag.get("column"),
                    ),
                    message=diag.get("message", ""),
                    source_engine=self.name,
                    rule_id=rule,
                    evidence=suggestion,
                    actions=actions,
                )
            )
        return findings


ENGINE = AgnixEngine()
