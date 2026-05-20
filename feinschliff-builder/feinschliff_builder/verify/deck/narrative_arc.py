"""Deck-level narrative-arc check.

Deterministic deck-verify class: given the sequence of `narrative_act`
values populated by the storyline gate (one per slide), fire a
narrative-arc-missing defect if the deck contains a Situation and a
Resolution but no Complication.

The SCR (Situation → Complication → Resolution) shape is the universal
consulting deck spine. A deck that establishes a Situation and proposes
a Resolution without naming a Complication leaves the audience asking
"why act now?" — the Complication slide is what justifies action.

The skill orchestrator invokes this at step 4 verify (see
`skills/deck/references/iteration-loop.md` defect class #20).
"""
from __future__ import annotations

from lib.verify.deck.defects import DeckDefect


_VALID_ACTS = frozenset({"situation", "complication", "resolution"})


def check_narrative_arc(narrative_acts: list[str]) -> list[DeckDefect]:
    """Return defects if the SCR arc is broken at the deck level.

    The rule: if both 'situation' and 'resolution' appear in the input,
    'complication' must also appear. Values outside the SCR enum are
    ignored (skipped, not treated as errors).
    """
    present = {act for act in narrative_acts if act in _VALID_ACTS}
    if "situation" in present and "resolution" in present and "complication" not in present:
        return [DeckDefect(
            kind="narrative-arc-missing",
            slide_index=None,
            message=("deck has Situation and Resolution slides but no "
                     "Complication — audience won't know why action is "
                     "needed now"),
            suggestion=("add a Complication slide between Situation and "
                        "Resolution that names the cost of inaction or the "
                        "trigger forcing the decision"),
        )]
    return []
