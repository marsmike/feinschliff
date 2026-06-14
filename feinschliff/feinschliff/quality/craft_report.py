"""Write a CraftReport to a Markdown file."""
from __future__ import annotations

from pathlib import Path

from .craft_rules import CraftReport


def write_craft_report(report: CraftReport, path: Path) -> None:
    """Write *report* as Markdown to *path* (creates parent dirs as needed)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# Craft Rules Report",
        "",
        f"**Verdict:** {report.verdict}",
        f"**Issues:** {len(report.issues)}",
        "",
        "---",
        "",
    ]

    for issue in report.issues:
        slide_label = f"Slide {issue.slide}" if issue.slide > 0 else "Deck"
        lines.append(
            f"## {slide_label} — rule: {issue.rule} [{issue.severity}]"
        )
        lines.append("")
        lines.append(issue.message)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
