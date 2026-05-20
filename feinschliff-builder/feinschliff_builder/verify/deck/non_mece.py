"""Non-MECE breakdown check — McKinsey/BCG hard rule.

A breakdown slide presents a whole decomposed into parts; the parts must be
Mutually Exclusive (no overlap) AND Collectively Exhaustive (no gap). Two
failure modes:

- **Numeric**: explicit values/percentages that don't sum to 100% (±2pp
  tolerance). This module's `check_non_mece` ships the deterministic side.
- **Semantic**: labels that overlap or leave gaps a 100%-sum check can't see
  (e.g. "Enterprise", "Mid-market", "Customer churn" — first two are MECE,
  third overlaps both). The LLM judgment runs at step 4 verify (see
  `skills/deck/references/iteration-loop.md` defect class non-mece-breakdown,
  #22).
"""
from __future__ import annotations

from numbers import Real

from feinschliff_builder.verify.deck.defects import DeckDefect


# Tolerance in percentage points around 100. Items summing to anything in
# [100 - _TOLERANCE_PP, 100 + _TOLERANCE_PP] are accepted as clean — that's
# the typical rounding slack seen on legitimate decks.
_TOLERANCE_PP = 2.0


def _numeric_value(item: object) -> float | None:
    """Return the numeric share of `item` if it carries one, else None.

    Items shaped as `{"value": 30}` or `{"percentage": 30}` are numeric.
    Strings, bare dicts without those fields, or dicts with non-numeric
    values for those fields are treated as non-numeric (LLM territory).
    Booleans are explicitly rejected (they're `Real` in Python but never a
    meaningful percentage).
    """
    if not isinstance(item, dict):
        return None
    for key in ("value", "percentage"):
        if key in item:
            v = item[key]
            if isinstance(v, bool):
                return None
            if isinstance(v, Real):
                return float(v)
    return None


def check_non_mece(
    items: list[dict | str],
    *,
    slide_index: int = 1,
) -> list[DeckDefect]:
    """Check a breakdown slide's items for numeric MECE violation.

    For numeric items (each item is a dict with a numeric `value` or
    `percentage` field), sum the values and fire a defect when the total
    isn't 100 (±2pp tolerance).

    For non-numeric items (each is a string or a dict without numeric
    fields), this function returns []. The semantic-overlap judgment lives
    in the skill's iteration-loop prompt — Python only handles the
    deterministic numeric case.
    """
    if not items:
        return []

    numeric_values = [v for v in (_numeric_value(it) for it in items) if v is not None]
    if not numeric_values:
        return []

    total = sum(numeric_values)
    if abs(total - 100.0) <= _TOLERANCE_PP:
        return []

    direction = "overshoots" if total > 100 else "undershoots"
    return [DeckDefect(
        kind="non-mece-breakdown",
        slide_index=slide_index,
        message=(
            f"breakdown items sum to {total:g}% — {direction} 100% by more "
            f"than the {_TOLERANCE_PP:g}pp tolerance, so the parts are not "
            f"collectively exhaustive"
        ),
        suggestion=(
            "rebalance the breakdown so categories cover the whole (sum to "
            "100%); often easier to refactor as 80/20 — the top 2-3 explicit "
            "buckets plus an 'Other' for the long tail"
        ),
    )]
