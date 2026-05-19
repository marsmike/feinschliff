"""Deterministic pre-LLM lint for per-slide speaker-notes budgets.

Complements `notes_coherence.py` (the LLM-judged arc check) with two cheap
structural checks: hook-slide presence and per-slide word-count budget. Runs
before any render budget is burned, alongside `validate_content`.
"""
from __future__ import annotations

from lib.content_validator import ContentDefect


# Per-slide speaker-notes word budgets, keyed by `design_brief.verbosity`.
# Mirrors the table in `skills/deck/references/speaker-notes.md`. The hook
# slide is exempt — its job is the full storyline (capped only by the
# 2000-char schema ceiling on the field itself).
_NOTES_WORD_BUDGET = {
    "concise":   40,
    "standard":  80,
    "text-heavy": 160,
}

# Below this, the hook-slide notes can't be carrying the full red_line
# storyline. The judge will catch semantic drift; this lint catches the
# fast case where the writer left the slot near-empty.
_HOOK_NOTES_MIN_CHARS = 60


def validate_notes(
    notes: str | None,
    *,
    slide_index: int,
    is_hook: bool,
    verbosity: str | None = None,
) -> list[ContentDefect]:
    """Pre-LLM structural lint for per-slide speaker notes.

    Two checks, both deterministic:

    1. **Hook slide presence.** If `is_hook=True` AND the deck has
       opted into speaker notes (``verbosity`` is set), notes that
       are missing / blank / shorter than ``_HOOK_NOTES_MIN_CHARS``
       emit a ``notes-hook-missing`` defect. The verbosity gate
       keeps legacy plans (no notes anywhere) clean while still
       enforcing the hook-storyline rule on briefs that committed
       to authoring notes.
    2. **Per-slide word budget.** For non-hook slides, compare
       ``len(notes.split())`` against the verbosity budget
       (concise: 40 / standard: 80 / text-heavy: 160 words). Emit a
       ``notes-overbudget`` defect when exceeded. ``verbosity=None``
       or an unknown value skips the budget check.

    The LLM-judged ``notes-coherence`` aspect runs separately and
    catches semantic drift / off-arc content. This function is the
    cheap pre-flight.
    """
    out: list[ContentDefect] = []
    text = (notes or "").strip()

    if is_hook:
        # Only fire the hook-missing defect on decks that opted into the
        # feature; otherwise every legacy plan without notes would lint
        # red. `verbosity` being set is the opt-in signal — it comes
        # from `design_brief.verbosity` once the brief is wired through.
        if verbosity is not None and len(text) < _HOOK_NOTES_MIN_CHARS:
            out.append(ContentDefect(
                kind="notes-hook-missing",
                slide_index=slide_index,
                slot="notes",
                message=(
                    f"hook-slide notes are too short to carry the deck's "
                    f"storyline ({len(text)} chars, expected "
                    f"≥{_HOOK_NOTES_MIN_CHARS}). Author the full red_line "
                    "arc into this slide's notes."
                ),
            ))
        # Hook slide is exempt from the per-slide word budget — its
        # length budget is the 2000-char schema ceiling on the field.
        return out

    if not text:
        # Per-slide notes are optional. The notes-coherence verifier may
        # warn the writer about missing notes; structural lint stays out.
        return out

    budget = _NOTES_WORD_BUDGET.get(verbosity) if verbosity else None
    if budget is not None:
        word_count = len(text.split())
        if word_count > budget:
            out.append(ContentDefect(
                kind="notes-overbudget",
                slide_index=slide_index,
                slot="notes",
                message=(
                    f"speaker notes exceed the {verbosity!r} verbosity "
                    f"budget: {word_count} words (max {budget}). Trim to "
                    "the talking points the presenter actually needs."
                ),
            ))

    return out
