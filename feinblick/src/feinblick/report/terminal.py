"""Terminal reporter — findings grouped by severity, ending on a verdict line.

Colorless by default (TTY color is a future enhancement). The final line always
contains the uppercased verdict token (PASS / WARN / FAIL) so callers and tests
can anchor on it.
"""
from __future__ import annotations

from feinblick.model import Finding, Severity

# Highest severity first.
_ORDER = (Severity.ERROR, Severity.WARNING, Severity.INFO)


def _format_finding(f: Finding) -> str:
    loc = f.location
    where = loc.path
    if loc.line is not None:
        where = f"{where}:{loc.line}"
    rule = f"[{f.rule_id}] " if f.rule_id else ""
    line = f"  {where}  {rule}{f.message}"
    if loc.symbol:
        line += f"  ({loc.symbol})"
    if f.evidence:
        line += f"  — {f.evidence}"
    return line


def render(findings: list[Finding], verdict: str, health: dict, meta: dict) -> str:
    lines: list[str] = []
    lines.append("feinblick report")
    score = health.get("score")
    if score is not None:
        lines.append(f"health: {score}/100")
    engines = meta.get("engines") or []
    unavailable = meta.get("unavailable") or []
    if engines:
        lines.append(f"engines: {', '.join(engines)}")
    if unavailable:
        lines.append(f"unavailable: {', '.join(unavailable)}")
    lines.append("")

    by_sev: dict[Severity, list[Finding]] = {sev: [] for sev in _ORDER}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)

    if not findings:
        lines.append("No findings.")
    else:
        for sev in _ORDER:
            group = by_sev.get(sev) or []
            if not group:
                continue
            lines.append(f"{sev.value.upper()} ({len(group)})")
            for f in group:
                lines.append(_format_finding(f))
            lines.append("")

    token = (verdict or "").strip().upper()
    introduced = meta.get("introduced")
    if token == "FAIL" and introduced:
        lines.append(f"FAIL ({introduced} introduced)")
    else:
        lines.append(token or "PASS")
    return "\n".join(lines)
