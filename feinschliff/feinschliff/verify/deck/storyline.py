"""Storyline contact-sheet + report file format.

Used by the new step 1c of the /deck pipeline (see
`skills/deck/references/pipeline.md`). The orchestrating LLM renders the
contact sheet from a planned form, judges the narrative arc, then writes
`out/storyline_report.md` with a verdict and (optionally) suggestions.

Report shape (matches iteration-loop.md's verify_report.md style):

    # Storyline Report

    - Verdict: clean | dirty | pending
    - Slides: N

    ---

    # Storyline contact sheet

    [optional brief summary line]

    1. <title>
    2. <title>
    ...

    ## Suggestions      # only if any
    - <suggestion>
    - ...
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal


_MISSING_TITLE = "_(no title)_"

Verdict = Literal["clean", "dirty", "pending"]


def render_contact_sheet(
    titles: list[str],
    *,
    brief_summary: str | None = None,
) -> str:
    """Render a numbered contact-sheet block (no header / verdict)."""
    lines: list[str] = ["# Storyline contact sheet", ""]
    if brief_summary:
        lines.append(brief_summary.strip())
        lines.append("")
    if not titles:
        lines.append("_(no titles — plan has no slides yet)_")
        return "\n".join(lines)
    for i, title in enumerate(titles, start=1):
        rendered = title.strip() if title and title.strip() else _MISSING_TITLE
        lines.append(f"{i}. {rendered}")
    return "\n".join(lines)


def write_storyline_report(
    path: Path,
    *,
    contact_sheet: str,
    verdict: Verdict = "pending",
    suggestions: list[str] | None = None,
) -> None:
    """Write the full storyline_report.md to disk.

    `Slides: N` reflects the number of *non-empty* titled slides — lines
    rendered as `_(no title)_` are excluded from the count so the header
    surfaces a meaningful narrative length rather than a raw slide count.
    """
    slide_count = sum(
        1 for line in contact_sheet.splitlines()
        if line and line[0].isdigit() and ". " in line
        and _MISSING_TITLE not in line
    )
    parts: list[str] = [
        "# Storyline Report",
        "",
        f"- Verdict: {verdict}",
        f"- Slides: {slide_count}",
        "",
        "---",
        "",
        contact_sheet,
    ]
    if suggestions:
        parts.append("")
        parts.append("## Suggestions")
        parts.append("")
        for s in suggestions:
            parts.append(f"- {s}")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Arc schema lookup (dispatch wiring happens in a separate PR)
# ---------------------------------------------------------------------------

def select_arc_schema(deck_type: str) -> dict | None:
    """Return the arc schema dict for *deck_type*, or None if not found.

    Loads arc schemas via ``feinschliff.storyline.load_all_arcs`` (catches
    ``ImportError`` → returns ``None`` so callers degrade gracefully when the
    module is absent). Returns ``None`` when *deck_type* is not in the
    registry.
    """
    try:
        from feinschliff.storyline import load_all_arcs  # type: ignore[import]
    except ImportError:
        return None
    arcs = load_all_arcs()
    return arcs.get(deck_type)
