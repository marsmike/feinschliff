"""Speaker-notes ↔ red_line coherence contact-sheet + report file format.

Pairs the deck's `red_line` against each slide's `(claim, notes)` so the
orchestrating LLM can judge whether the spoken delivery (notes) tracks
the arc the deck is supposed to tell.

Mirrors the shape of `storyline.py` — same `render_contact_sheet` /
`write_*_report` split, same verdict enum, same suggestions tail. Used
by `feinschliff deck verify-aspect notes-coherence` (and any standalone
caller that wants the contact sheet as a string).

Report shape (parallels storyline_report.md):

    # Notes Coherence Report

    - Verdict: clean | dirty | pending
    - Slides: N
    - Red line: <one-sentence arc>

    ---

    # Notes coherence contact sheet

    [optional brief summary line]

    ## Red line
    <red_line text>

    ## Slide 1 — <role> — <claim>
    <notes block, or _(no notes)_>

    ## Slide 2 — <role> — <claim>
    ...

    ## Suggestions      # only if any
    - <suggestion>
    - ...

The hook slide (index 0) is the exception: its notes are expected to
carry the *full storyline articulation* of `red_line`, not just per-slide
talking points. The LLM judge enforces that distinction; this module
only renders the inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


_MISSING_NOTES = "_(no notes)_"
_MISSING_CLAIM = "_(no claim)_"

Verdict = Literal["clean", "dirty", "pending"]


@dataclass(frozen=True)
class SlideForCoherence:
    """One slide's coherence-relevant data. `index` is 0-based to match
    the design-brief schema; `role` comes from the brief's slide-role
    enum (hook / context / complication / …)."""
    index: int
    role: str
    claim: str
    notes: str | None


def render_contact_sheet(
    red_line: str,
    slides: list[SlideForCoherence],
    *,
    brief_summary: str | None = None,
) -> str:
    """Render the coherence contact-sheet block (no header / verdict).

    Each slide gets a `## Slide N — <role> — <claim>` header followed by
    its notes block, or the `_(no notes)_` sentinel when notes are unset
    / empty. The hook slide (role=`hook`) is rendered first regardless
    of plan order so the reader sees the storyline alongside the
    red_line before scanning per-slide entries. If no slide has role=
    `hook`, slides render in their original `index` order.
    """
    lines: list[str] = ["# Notes coherence contact sheet", ""]
    if brief_summary:
        lines.append(brief_summary.strip())
        lines.append("")
    lines.append("## Red line")
    lines.append("")
    lines.append(red_line.strip() if red_line else "_(no red_line)_")
    lines.append("")

    ordered = sorted(
        slides, key=lambda s: (0 if s.role == "hook" else 1, s.index),
    )

    if not ordered:
        lines.append("_(no slides)_")
        return "\n".join(lines)

    for s in ordered:
        claim = s.claim.strip() if s.claim and s.claim.strip() else _MISSING_CLAIM
        # 1-based slide numbering in the rendered sheet (matches storyline.py).
        lines.append(f"## Slide {s.index + 1} — {s.role} — {claim}")
        lines.append("")
        if s.notes and s.notes.strip():
            lines.append(s.notes.strip())
        else:
            lines.append(_MISSING_NOTES)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_coherence_report(
    path: Path,
    *,
    red_line: str,
    contact_sheet: str,
    verdict: Verdict = "pending",
    suggestions: list[str] | None = None,
) -> None:
    """Write `notes_coherence_report.md` to disk.

    `Slides: N` reflects the number of slides whose notes were judged.
    The judge fills `verdict` and (optionally) `suggestions`; until then
    `verdict='pending'` and no suggestions block is written. The
    `red_line` is surfaced in the header so a reviewer scanning the
    file sees the arc without parsing the contact sheet.
    """
    slide_count = sum(
        1 for line in contact_sheet.splitlines()
        if line.startswith("## Slide ")
    )
    parts: list[str] = [
        "# Notes Coherence Report",
        "",
        f"- Verdict: {verdict}",
        f"- Slides: {slide_count}",
        f"- Red line: {red_line.strip() if red_line else '_(no red_line)_'}",
        "",
        "---",
        "",
        contact_sheet.rstrip(),
    ]
    if suggestions:
        parts.append("")
        parts.append("## Suggestions")
        parts.append("")
        for s in suggestions:
            parts.append(f"- {s}")
    path.write_text("\n".join(parts) + "\n")


def slides_from_design_brief(brief: dict) -> list[SlideForCoherence]:
    """Adapter: pull (index, role, claim, notes) tuples out of a parsed
    design_brief.json. Missing per-slide `notes` becomes None — the
    contact sheet renders it as `_(no notes)_` and the judge flags it."""
    out: list[SlideForCoherence] = []
    for s in brief.get("slides") or []:
        out.append(SlideForCoherence(
            index=int(s.get("index", 0)),
            role=str(s.get("role", "")),
            claim=str(s.get("claim", "")),
            notes=s.get("notes"),
        ))
    return out
