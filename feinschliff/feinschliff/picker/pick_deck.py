"""Arc-aware deck-level layout picker.

Wraps the per-slide ``pick_layout`` scorer with a post-hoc rebalance pass
that enforces first-slide / last-slide role conventions and emits arc
warnings for missing required acts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

# Roles that satisfy the "cover" / "opener" constraint on slide 1.
_COVER_ROLES = frozenset({"cover", "title-primary", "title", "title-cover", "opening"})
# Roles that satisfy the "closer" constraint on the last slide.
_CLOSER_ROLES = frozenset({"closer", "end", "closing", "cta", "call-to-action", "thank-you"})


def _role_matches_cover(layout_name: str) -> bool:
    n = layout_name.lower()
    return any(r in n for r in ("cover", "title"))


def _role_matches_closer(layout_name: str) -> bool:
    n = layout_name.lower()
    return any(r in n for r in ("closer", "end", "cta", "closing", "thank"))


@dataclass(frozen=True)
class LayoutPick:
    slide_index: int  # 1-based
    layout: str       # chosen layout name (without .slide.dsl)
    score: float
    runners_up: list[dict]       # [{"layout": ..., "score": ..., "why_not": ...}]
    overrides_applied: list[str]  # e.g. "arc-aware-first-slide-swap"


@dataclass(frozen=True)
class PickerReport:
    picks: list[LayoutPick]
    arc_warnings: list[str]  # one-line warnings about arc position misses


def _build_why_not(winner_score: float, candidate: dict) -> str:
    """Derive a human-readable reason why this candidate lost to the winner."""
    gap = round(winner_score - candidate["score"], 2)
    rationale = candidate.get("rationale", "")
    if gap > 0:
        base = f"score gap {gap:.1f} below winner"
        if rationale:
            return f"{base}; {rationale}"
        return base
    # Tied or floating-point noise — surface rationale if available.
    if rationale:
        return rationale
    return "lower score"


def _extract_signals(slide: dict) -> dict:
    """Pull pick_layout keyword args from a slide dict."""
    known = {
        "role",
        "concept_count",
        "data_quantity",
        "comparison",
        "narrative_role",
        "narrative_act",
        "time_axis_role",
        "audience_mode",
        "diagram_kind",
        "diagram_complexity",
        "slot_lengths",
    }
    return {k: v for k, v in slide.items() if k in known}


def pick_deck(
    slides: list[dict],
    brand: str,
    deck_brief: dict | None = None,
    *,
    top_k: int = 5,
) -> PickerReport:
    """Run the arc-aware deck-level picker over *slides*.

    Parameters
    ----------
    slides:
        List of slide dicts.  Each may contain any subset of the
        ``pick_layout`` signal keys (role, concept_count, etc.).
    brand:
        Brand name passed to ``find_brand`` for profile loading.
    deck_brief:
        Optional deck brief dict.  When ``deck_type`` is present the
        matching arc schema is loaded and arc warnings are computed.
    top_k:
        How many candidates to request from ``pick_layout`` per slide.
    """
    from feinschliff.layout_picker import pick_layout

    # Load brand profiles (best-effort — non-fatal if brand not found).
    profiles: dict | None = None
    try:
        from feinschmiede.brand_discovery import find_brand
        bp = find_brand(brand)
        profiles = getattr(bp, "layout_profiles", None)
    except Exception:
        pass  # picker still works without profiles

    # Per-slide scoring.
    raw_picks: list[list[dict]] = []  # index → top_k candidates
    for slide in slides:
        signals = _extract_signals(slide)
        candidates = pick_layout(**signals, top_k=top_k, profiles=profiles)
        raw_picks.append(candidates)

    # Build LayoutPick objects before arc rebalance.
    picks: list[LayoutPick] = []
    for i, candidates in enumerate(raw_picks):
        if not candidates:
            # Degenerate: no candidates — emit a placeholder.
            picks.append(LayoutPick(
                slide_index=i + 1,
                layout="unknown",
                score=0.0,
                runners_up=[],
                overrides_applied=[],
            ))
            continue
        winner = candidates[0]
        runners_up = [
            {
                "layout": c["layout"],
                "score": c["score"],
                "why_not": _build_why_not(winner["score"], c),
            }
            for c in candidates[1:]
        ]
        picks.append(LayoutPick(
            slide_index=i + 1,
            layout=winner["layout"],
            score=winner["score"],
            runners_up=runners_up,
            overrides_applied=[],
        ))

    arc_warnings: list[str] = []
    deck_type: str | None = (deck_brief or {}).get("deck_type")

    # Arc schema for position warnings.
    arc_schema: dict | None = None
    if deck_type:
        try:
            from feinschliff.storyline import load_all_arcs
            arcs = load_all_arcs()
            arc_schema = arcs.get(deck_type)
        except Exception:
            pass

    # ── First-slide swap ──────────────────────────────────────────────────────
    if picks and not _role_matches_cover(picks[0].layout):
        # Search raw_picks[0] for a cover-like candidate first.
        candidates_0 = raw_picks[0] if raw_picks else []
        swap_candidate = next(
            (c for c in candidates_0 if _role_matches_cover(c["layout"])),
            None,
        )
        # If not in top-k, explicitly request a title-primary layout so the
        # first slide always resolves to a cover-like choice.
        if swap_candidate is None:
            fallback = pick_layout(role="title-primary", top_k=1, profiles=profiles)
            if fallback:
                swap_candidate = fallback[0]
        if swap_candidate:
            old_pick = picks[0]
            log.info(
                "arc-aware picker: slide 1 swap %s → %s",
                old_pick.layout,
                swap_candidate["layout"],
            )
            # Rebuild runners_up: old winner + remaining candidates minus new winner.
            new_runners_up = [
                {
                    "layout": c["layout"],
                    "score": c["score"],
                    "why_not": _build_why_not(swap_candidate["score"], c),
                }
                for c in candidates_0
                if c["layout"] != swap_candidate["layout"]
            ]
            picks[0] = LayoutPick(
                slide_index=1,
                layout=swap_candidate["layout"],
                score=swap_candidate["score"],
                runners_up=new_runners_up,
                overrides_applied=["arc-aware-first-slide-swap"],
            )

    # ── Last-slide swap ───────────────────────────────────────────────────────
    if len(picks) > 1 and not _role_matches_closer(picks[-1].layout):
        last_i = len(picks) - 1
        candidates_last = raw_picks[last_i] if last_i < len(raw_picks) else []
        swap_candidate = next(
            (c for c in candidates_last if _role_matches_closer(c["layout"])),
            None,
        )
        # If not in top-k, explicitly request a closer layout.
        if swap_candidate is None:
            fallback = pick_layout(role="closer", top_k=1, profiles=profiles)
            if fallback:
                swap_candidate = fallback[0]
        if swap_candidate:
            log.info(
                "arc-aware picker: slide %d (last) swap %s → %s",
                last_i + 1,
                picks[-1].layout,
                swap_candidate["layout"],
            )
            new_runners_up = [
                {
                    "layout": c["layout"],
                    "score": c["score"],
                    "why_not": _build_why_not(swap_candidate["score"], c),
                }
                for c in candidates_last
                if c["layout"] != swap_candidate["layout"]
            ]
            picks[-1] = LayoutPick(
                slide_index=last_i + 1,
                layout=swap_candidate["layout"],
                score=swap_candidate["score"],
                runners_up=new_runners_up,
                overrides_applied=["arc-aware-last-slide-swap"],
            )

    # ── Arc position warnings ─────────────────────────────────────────────────
    if arc_schema and picks:
        n = len(picks)
        opening_band = max(1, round(n * 0.25))  # first 25%
        closing_band = max(1, round(n * 0.25))  # last 25%

        for act in arc_schema.get("acts", []):
            if not act.get("required"):
                continue
            position = act.get("position", "any")
            act_name = act.get("name", "")
            if position == "any" or not act_name:
                continue

            if position == "opening":
                band_picks = picks[:opening_band]
            elif position == "closing":
                band_picks = picks[n - closing_band:]
            else:
                # middle / late — skip for this PR
                continue

            matched = any(
                act_name.lower() in p.layout.lower() for p in band_picks
            )
            if not matched:
                arc_warnings.append(
                    f"No '{act_name}' act detected in {position} band "
                    f"for deck_type={deck_type}"
                )

    return PickerReport(picks=picks, arc_warnings=arc_warnings)
