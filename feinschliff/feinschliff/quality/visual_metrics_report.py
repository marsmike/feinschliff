from __future__ import annotations

from pathlib import Path

from .visual_metrics import VisualMetricsResult


def write_visual_metrics_report(result: VisualMetricsResult, path: Path) -> None:
    """Write a Markdown visual metrics report to *path*."""
    lines: list[str] = []
    lines.append("# Visual Metrics Report")
    lines.append("")
    lines.append(f"**Verdict:** {result.verdict}")
    lines.append("")
    lines.append("| Slide | Whitespace | Balance | Collision pairs |")
    lines.append("|---|---|---|---|")
    for slide_idx in sorted(result.per_slide):
        m = result.per_slide[slide_idx]
        ws = m.get("whitespace", 0.0)
        bal = m.get("balance", 0.0)
        col = int(m.get("collision_pairs", 0))
        lines.append(f"| {slide_idx} | {ws:.2f} | {bal:.3f} | {col} |")

    if result.issues:
        lines.append("")
        lines.append("## Issues")
        lines.append("")
        for issue in result.issues:
            lines.append(
                f"- **Slide {issue.slide} — {issue.metric} [{issue.severity}]**"
                f" — {issue.message}"
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
