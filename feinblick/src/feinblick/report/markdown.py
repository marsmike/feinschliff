"""Markdown reporter — a dated, Obsidian-friendly report.

Layout: an H1 with today's date, a health-score line, one section + table per
category present in the findings, then a verdict line.
"""
from __future__ import annotations

import datetime

from feinblick.model import Category, Finding

# Stable display order; any category not listed falls to the end alphabetically.
_CATEGORY_ORDER = list(Category)


def _title_case(category: Category) -> str:
    return category.value.replace("_", " ").title()


def _escape_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def _category_order_key(category: Category) -> tuple[int, str]:
    try:
        return (_CATEGORY_ORDER.index(category), category.value)
    except ValueError:
        return (len(_CATEGORY_ORDER), category.value)


def _table(findings: list[Finding]) -> list[str]:
    rows = [
        "| Severity | Location | Rule | Message |",
        "| --- | --- | --- | --- |",
    ]
    for f in findings:
        loc = f.location.path
        if f.location.line is not None:
            loc = f"{loc}:{f.location.line}"
        rows.append(
            "| {sev} | {loc} | {rule} | {msg} |".format(
                sev=f.severity.value,
                loc=_escape_cell(loc),
                rule=_escape_cell(f.rule_id or ""),
                msg=_escape_cell(f.message),
            )
        )
    return rows


def render(findings: list[Finding], verdict: str, health: dict, meta: dict) -> str:
    today = datetime.date.today().isoformat()
    lines: list[str] = [f"# feinblick report — {today}", ""]

    score = health.get("score")
    if score is not None:
        lines.append(f"**Health score:** {score}/100")
    engines = meta.get("engines") or []
    unavailable = meta.get("unavailable") or []
    if engines:
        lines.append(f"**Engines:** {', '.join(engines)}")
    if unavailable:
        lines.append(f"**Unavailable:** {', '.join(unavailable)}")
    lines.append(f"**Findings:** {len(findings)}")
    lines.append("")

    grouped: dict[Category, list[Finding]] = {}
    for f in findings:
        grouped.setdefault(f.category, []).append(f)

    if not findings:
        lines.append("No findings.")
        lines.append("")
    else:
        for category in sorted(grouped, key=_category_order_key):
            group = grouped[category]
            lines.append(f"## {_title_case(category)} ({len(group)})")
            lines.append("")
            lines.extend(_table(group))
            lines.append("")

    token = (verdict or "").strip().upper()
    introduced = meta.get("introduced")
    if token == "FAIL" and introduced:
        lines.append(f"**Verdict:** FAIL ({introduced} introduced)")
    else:
        lines.append(f"**Verdict:** {token or 'PASS'}")
    lines.append("")
    return "\n".join(lines)
