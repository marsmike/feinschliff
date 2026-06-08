"""LayoutPicker — OO wrapper around :func:`feinschliff.layout_picker.pick_layout`.

Provides a class-based interface for layout selection, keeping the existing
:func:`~feinschliff.layout_picker.pick_layout` function as the scoring engine.

Usage::

    from feinschliff.brand.pack import BrandPack
    from feinschliff.deck.picker import LayoutPicker, LayoutMatch

    pack = BrandPack.load(Path("brands/feinschliff"))
    picker = LayoutPicker(brand=pack)

    match = picker.pick({"role": "content-columns", "concept_count": 3})
    print(match.layout_name, match.score, match.reason)

    candidates = picker.candidates({"role": "data-timeline"})
    for c in candidates:
        print(c.layout_name, c.score, c.reason)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from feinschliff.layout_picker import pick_layout


# ── LayoutMatch ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LayoutMatch:
    """A single layout candidate returned by :class:`LayoutPicker`.

    Attributes
    ----------
    layout_name:
        The bare layout identifier, e.g. ``"title-orange"``.
    layout_path:
        Full path to the ``*.slide.dsl`` file, or ``None`` when the
        layout hasn't been resolved against a brand root yet.
    score:
        Numeric affinity score (higher is better).
    reason:
        Human-readable rationale string listing the signals that
        contributed to the score.
    """
    layout_name: str
    layout_path: Path | None
    score: float
    reason: str


# ── LayoutPicker ─────────────────────────────────────────────────────────────

class LayoutPicker:
    """Typed layout picker backed by :func:`feinschliff.layout_picker.pick_layout`.

    Parameters
    ----------
    brand:
        The :class:`~feinschliff.brand.pack.BrandPack` whose layout pool is
        searched when resolving :attr:`LayoutMatch.layout_path`.  When
        ``None``, ``layout_path`` in returned matches will also be ``None``.
    top_k:
        Default number of candidates returned by :meth:`candidates`.
    """

    def __init__(self, brand: Any = None, *, top_k: int = 3) -> None:
        self.brand = brand
        self.top_k = top_k
        self._profile_table_cache: dict[str, dict] | None = None

    # ── helpers ───────────────────────────────────────────────────────────

    def _profile_table(self) -> dict[str, dict] | None:
        """Affinity profiles for this brand's full layout universe.

        Built from ``BrandPack.layout_table()`` (toolkit ∪ brand overrides ∪
        brand-only layouts) so brand-only layouts are *ranked*, not merely
        resolvable by name. Cached per instance. Returns ``None`` when there
        is no brand — :func:`pick_layout` then falls back to its cached
        toolkit-only default table.
        """
        if self.brand is None:
            return None
        if self._profile_table_cache is None:
            from feinschliff.layout_profile import build_profile_table

            self._profile_table_cache = build_profile_table(
                self.brand.layout_table(), strict=False
            )
        return self._profile_table_cache

    def _resolve_path(self, layout_name: str) -> Path | None:
        """Return the filesystem path for *layout_name*.

        Checks the brand's local layouts first, then the toolkit pool.
        Returns ``None`` when not found anywhere.
        """
        if self.brand is None:
            return None
        # BrandPack.find_layout() covers both brand-local and toolkit pool.
        found = self.brand.find_layout(layout_name)
        if found is not None:
            return found.path
        return None

    @staticmethod
    def _to_match(candidate: dict, layout_path: Path | None) -> LayoutMatch:
        reason_raw = candidate.get("rationale") or ["—"]
        if isinstance(reason_raw, list):
            reason = ", ".join(reason_raw)
        else:
            reason = str(reason_raw)
        return LayoutMatch(
            layout_name=candidate["layout"],
            layout_path=layout_path,
            score=float(candidate.get("score", 0.0)),
            reason=reason,
        )

    # ── public API ────────────────────────────────────────────────────────

    def candidates(
        self,
        slot_hint: dict[str, Any],
        *,
        top_k: int | None = None,
    ) -> list[LayoutMatch]:
        """Return up to *top_k* ranked :class:`LayoutMatch` instances.

        *slot_hint* is the same signal dict accepted by
        :func:`feinschliff.layout_picker.pick_layout`:

        .. code-block:: python

            {
                "role": "content-columns",
                "concept_count": 3,
                "data_quantity": None,
                "comparison": False,
                "narrative_role": "so-what",
                "narrative_act": "resolution",
                "time_axis_role": None,
                "audience_mode": "presentation",
                "diagram_kind": None,
                "diagram_complexity": None,
                "layout_history": ["title-orange", "two-column-cards"],
            }
        """
        k = top_k if top_k is not None else self.top_k
        raw = pick_layout(
            role=slot_hint.get("role"),
            concept_count=slot_hint.get("concept_count"),
            data_quantity=slot_hint.get("data_quantity"),
            comparison=slot_hint.get("comparison"),
            narrative_role=slot_hint.get("narrative_role"),
            narrative_act=slot_hint.get("narrative_act"),
            time_axis_role=slot_hint.get("time_axis_role"),
            audience_mode=slot_hint.get("audience_mode"),
            diagram_kind=slot_hint.get("diagram_kind"),
            diagram_complexity=slot_hint.get("diagram_complexity"),
            layout_history=slot_hint.get("layout_history"),
            top_k=k,
            profiles=self._profile_table(),
        )
        return [
            self._to_match(c, self._resolve_path(c["layout"]))
            for c in raw
        ]

    def pick(self, slot_hint: dict[str, Any]) -> LayoutMatch:
        """Return the best :class:`LayoutMatch` for *slot_hint*.

        Equivalent to ``candidates(slot_hint, top_k=1)[0]``.

        Raises :exc:`ValueError` when no layout scores positively (rare —
        usually indicates a badly-formed slot_hint without a valid ``role``).
        """
        candidates = self.candidates(slot_hint, top_k=1)
        if not candidates:
            raise ValueError(
                f"LayoutPicker.pick: no layout matched signals {slot_hint!r}"
            )
        return candidates[0]
