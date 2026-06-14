"""Ghost-deck title-strip check.

The "McKinsey ghost deck" test: read slide titles in order and judge
whether they tell a coherent argument — without reading body content.

Works from a list of title strings (pre-render or post-extract).

Usage
-----
From the pipeline (step 1d):

    from feinschliff_builder.verify.deck.ghost_deck import judge_ghost_deck, write_ghost_deck_report

    result = judge_ghost_deck(titles)
    write_ghost_deck_report(result, out_path)

CLI:

    feinschliff deck ghost-deck plan.yaml -o ghost_deck_report.md [--offline]

See skills/deck/references/pipeline.md §Step 1d.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from feinschliff_builder.verify.llm.rubric import _judge  # noqa: F401  (re-exported for patch targets)


# ---------------------------------------------------------------------------
# Public data class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GhostDeckResult:
    """Result of a ghost-deck narrative coherence check."""

    verdict: str                          # "pass" | "warn" | "fail"
    issues: list[dict] = field(default_factory=list)    # [{slide, issue, suggested}, ...]
    titles: list[str] = field(default_factory=list)     # The titles judged (for the report)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_VALID_VERDICTS = frozenset({"pass", "warn", "fail"})


def _build_prompt(titles: list[str]) -> str:
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
    return (
        "Below is a sequence of slide titles. Without reading any body content,\n"
        "judge whether they tell a coherent argument.\n"
        "\n"
        "Specifically:\n"
        "- Are there gaps in the logic (a title that doesn't follow from the prior one)?\n"
        "- Any topic-label titles (no verb, no claim — e.g. \"Market Overview\" vs "
        "\"The market is shifting from on-prem to cloud\")?\n"
        "- Any title containing \"and\" that should be two slides?\n"
        "- Does the sequence end with an explicit conclusion or ask?\n"
        "\n"
        "Titles:\n"
        f"{numbered}\n"
        "\n"
        'Return strict JSON: {"verdict": "pass|warn|fail", '
        '"issues": [{"slide": N, "issue": "...", "suggested": "..."}]}'
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def judge_ghost_deck(
    titles: list[str],
    *,
    offline: bool = False,
    model: str = "claude-haiku-4-5-20251001",
) -> GhostDeckResult:
    """Judge a sequence of slide titles for narrative coherence.

    When *offline* is ``True``, returns a pass result with no LLM call —
    suitable for CI environments without API keys.
    """
    if offline:
        return GhostDeckResult(verdict="pass", issues=[], titles=list(titles))

    prompt = _build_prompt(titles)
    raw = _judge(prompt, model=model)

    # Error sentinel from _judge: {"status": "fail", "reason": "..."}
    if "verdict" not in raw and raw.get("status") == "fail":
        reason = raw.get("reason", "unknown error")
        return GhostDeckResult(
            verdict="warn",
            issues=[{"slide": 0, "issue": f"LLM call failed: {reason}", "suggested": ""}],
            titles=list(titles),
        )

    # Normalize verdict
    raw_verdict = str(raw.get("verdict", "")).lower()
    verdict = raw_verdict if raw_verdict in _VALID_VERDICTS else "warn"

    # Normalize issues
    raw_issues = raw.get("issues")
    issues: list[dict] = list(raw_issues) if isinstance(raw_issues, list) else []

    return GhostDeckResult(verdict=verdict, issues=issues, titles=list(titles))


def write_ghost_deck_report(result: GhostDeckResult, path: Path) -> None:
    """Write a markdown ghost-deck report to *path*."""
    n = len(result.titles)
    parts: list[str] = [
        f"# Ghost Deck Verdict — {n} titles",
        "",
        f"**Verdict:** {result.verdict}",
        "",
        "## Titles",
        "",
    ]
    for i, title in enumerate(result.titles, start=1):
        parts.append(f"{i}. {title}")

    parts.append("")
    parts.append("## Issues")
    parts.append("")

    if not result.issues or result.verdict == "pass":
        parts.append("_No issues._")
    else:
        for issue in result.issues:
            slide = issue.get("slide", "?")
            text = issue.get("issue", "")
            suggested = issue.get("suggested", "")
            line = f"- **Slide {slide}** — {text}."
            if suggested:
                line += f" Suggested: {suggested}."
            parts.append(line)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")
