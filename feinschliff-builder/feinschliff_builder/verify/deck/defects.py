"""Deck-level defect dataclass + formatter."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeckDefect:
    kind: str               # e.g. "title-story-spine", "title-body-coherence"
    slide_index: int | None # 1-based; None for deck-level defects
    message: str            # what's wrong (one line)
    suggestion: str         # how to fix it (one line)

    def __str__(self) -> str:
        head = f"[{self.kind}]"
        if self.slide_index is not None:
            head = f"slide {self.slide_index} {head}"
        return f"{head} {self.message}"


def format_deck_defects(defects: list[DeckDefect]) -> str:
    """Human-readable summary for printing after deck-verify."""
    if not defects:
        return "deck verify: clean — no deck-level defects."
    lines = [f"deck verify: {len(defects)} defect(s)"]
    for d in defects:
        lines.append(f"  {d}")
        lines.append(f"    fix: {d.suggestion}")
    return "\n".join(lines)
