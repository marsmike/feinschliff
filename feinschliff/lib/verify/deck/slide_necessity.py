"""Slide-necessity context helper — BCG devil's-advocate critique signal.

For each slide, ask "if you removed this, would the deck still cohere?" — and
recommend cuts where the answer is yes. Surfaces only in `/deck critique`
mode (not regular verify), since "remove a slide" isn't a fix mid-build.

Python doesn't have a deterministic check here — this is pure LLM judgment
territory. This module materializes the *context* for the judgment: for
slide N, the title of slide N along with the titles immediately before and
after, so the LLM can judge necessity in narrative context.

The skill orchestrator invokes this at step 4 verify in critique mode (see
`skills/deck/references/iteration-loop.md` defect class slide-necessity,
#24, critique-only).
"""
from __future__ import annotations


def materialize_necessity_context(
    titles: list[str],
    slide_index: int,
) -> dict[str, str | None]:
    """Return {prev_title, current_title, next_title} for the judgment context.

    1-based `slide_index`. `prev_title` / `next_title` are None at the
    deck boundaries (first and last slide respectively). Raises IndexError
    when `slide_index` is outside `[1, len(titles)]`.
    """
    if not 1 <= slide_index <= len(titles):
        raise IndexError(
            f"slide_index {slide_index} out of range "
            f"(deck has {len(titles)} slide(s))"
        )
    idx = slide_index - 1
    prev_title = titles[idx - 1] if idx - 1 >= 0 else None
    current_title = titles[idx]
    next_title = titles[idx + 1] if idx + 1 < len(titles) else None
    return {
        "prev_title": prev_title,
        "current_title": current_title,
        "next_title": next_title,
    }
