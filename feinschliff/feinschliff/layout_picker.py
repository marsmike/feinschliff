"""Structured layout picker.

Maps a small set of content signals to a ranked list of candidate
toolkit layouts. The signals come from the brief / planner; the scores
come from a static affinity table.

Signals
-------
role            str   data-role enum (title-primary, title-with-visual,
                     chapter-opener, agenda, data-quantity, data-comparison,
                     data-timeline, content-columns, content-with-visual,
                     quote, reference, closer)
concept_count   int   how many parallel concepts the slide carries (1..8)
data_quantity   int   how many data points / cells the slide carries
comparison      bool  is this slide comparing things?
narrative_role  str   optional narrative-role hint (e.g. "so-what",
                     "context", "evidence", "summary") — scored against
                     layouts that declare a matching `narrative_role`
                     affinity in their profile.
narrative_act   str   optional SCR-shape hint (situation | complication |
                     resolution) — populated by the storyline gate per
                     slide. Consumed by lib.verify.deck.narrative_arc
                     and by Phase 4 layouts (recommendation, next-steps).
                     Scored against Phase 4 layouts that declare a
                     `narrative_act` affinity; neutral against legacy
                     layouts (no penalty, no bonus).
time_axis_role  str   optional time-axis hint (strategic | chronological |
                     tactical) — disambiguates gantt vs roadmap vs
                     timeline. Scored against Phase 4 layouts that
                     declare a `time_axis_role` affinity; neutral
                     against legacy layouts.
audience_mode   str   optional deck-level density preference (presentation
                     | discussion). When `presentation`, layouts at the
                     low end of their ideal_count range get a small
                     bonus (sparser fits read better live). When
                     `discussion`, layouts at the high end get the bonus
                     (denser fits are fine in a read-along).
layout_history  list  optional list of recently-used layout IDs (most
                     recent last). Encourages visual variety: the last
                     layout used loses 0.5 points, the second-to-last
                     loses 0.25. Structural layouts (title slides, chapter
                     openers, agenda, end) are exempt — they don't rotate.
"""
from __future__ import annotations

from typing import Literal

# Allowed enum values for the three Phase 3 signals. Validated fail-loud
# in pick_layout so typos surface as ValueError today rather than
# silently failing to score against Phase 4 affinity entries.
_VALID_NARRATIVE_ACTS = frozenset({"situation", "complication", "resolution"})
_VALID_TIME_AXIS_ROLES = frozenset({"strategic", "chronological", "tactical"})
_VALID_AUDIENCE_MODES = frozenset({"presentation", "discussion"})
# diagram_complexity steers the picker between the narrow (`excalidraw-diagram`
# / `svg-infographic`) and full-slide (`*-full`) diagram layouts. `deep`
# prefers the full layouts; `simple|medium` prefer the narrow ones.
_VALID_DIAGRAM_COMPLEXITY = frozenset({"simple", "medium", "deep"})

# Structural layouts that anchor every deck — they don't rotate by content
# and should never be penalised for consecutive use.
_VARIETY_EXEMPT = frozenset({
    "title-orange", "title-ink", "full-bleed-cover",
    "chapter-orange", "chapter-ink", "agenda", "end",
})


# Per-layout affinity profile. Each layout has:
#   role            : the canonical data-role it serves
#   ideal_count     : sweet spot for concept_count (range, inclusive)
#   data_band       : "none" | "kpi" | "table" | "chart"
#   comparison      : True if the layout is built for comparison
#   narrative_role  : optional — preferred narrative role string. Matches
#                     contribute +2 when the caller passes the same role.
#   narrative_act   : optional — preferred SCR act (situation |
#                     complication | resolution). +1 when matched.
#   time_axis_role  : optional — preferred time-axis (strategic |
#                     chronological | tactical). +1 when matched.
#
# Score is computed as the sum of:
#   role match            +3
#   concept_count in band +2
#   concept_count near    +1 (one off)
#   data band match       +2
#   comparison flag match +1
#   narrative_role match  +2 (Phase 4 layouts only)
#   narrative_act match   +1 (Phase 4 layouts only)
#   time_axis_role match  +1 (Phase 4 layouts only)
#   audience_mode bonus   +0.5 (sparser fit when presentation, denser
#                                when discussion; any layout, scaled
#                                against its ideal_count range)
# Negative if role mismatched.
_LAYOUTS: dict[str, dict] = {
    "title-orange":       {"role": "title-primary", "ideal_count": (1, 1), "data": "none",  "comp": False},
    "title-ink":          {"role": "title-primary", "ideal_count": (1, 1), "data": "none",  "comp": False},
    "full-bleed-cover":   {"role": "title-with-visual", "ideal_count": (1, 1), "data": "none", "comp": False},
    "text-picture":       {"role": "content-with-visual", "ideal_count": (1, 2), "data": "none", "comp": False},
    "chapter-orange":     {"role": "chapter-opener", "ideal_count": (1, 1), "data": "none", "comp": False},
    "chapter-ink":        {"role": "chapter-opener", "ideal_count": (1, 1), "data": "none", "comp": False},
    "agenda":             {"role": "agenda", "ideal_count": (3, 8), "data": "none", "comp": False},
    "two-column-cards":   {"role": "content-columns", "ideal_count": (2, 2), "data": "none", "comp": True},
    "three-column":       {"role": "content-columns", "ideal_count": (3, 3), "data": "none", "comp": True},
    "four-column-cards":  {"role": "content-columns", "ideal_count": (4, 4), "data": "none", "comp": False},
    "kpi-grid":           {"role": "data-quantity",  "ideal_count": (2, 4), "data": "kpi",  "comp": False},
    "action-title":       {"role": "title-primary",  "ideal_count": (1, 2), "data": "kpi",  "comp": False},
    "key-takeaways":      {"role": "closer",         "ideal_count": (2, 4), "data": "none", "comp": False},
    "executive-summary":  {"role": "content-columns","ideal_count": (3, 5), "data": "kpi",  "comp": False},
    "horizontal-bullets": {"role": "content-columns","ideal_count": (3, 3), "data": "none", "comp": True},
    "vertical-bullets":   {"role": "content-columns","ideal_count": (3, 6), "data": "none", "comp": False},
    "pyramid":            {"role": "content-columns","ideal_count": (3, 3), "data": "none", "comp": False},
    "process-flow":       {"role": "data-timeline",  "ideal_count": (3, 7), "data": "none", "comp": False},
    "2x2-matrix":         {"role": "data-comparison","ideal_count": (4, 4), "data": "table","comp": True},
    "bar-chart":          {"role": "data-comparison","ideal_count": (3, 6), "data": "chart","comp": True},
    "line-chart":         {"role": "data-timeline",  "ideal_count": (3, 8), "data": "chart","comp": False},
    "stacked-bar":        {"role": "data-comparison","ideal_count": (3, 5), "data": "chart","comp": True},
    "scorecard":          {"role": "data-comparison","ideal_count": (3, 5), "data": "table","comp": True},
    "gantt":              {"role": "data-timeline",  "ideal_count": (3, 6), "data": "table","comp": False},
    "funnel":             {"role": "data-comparison","ideal_count": (3, 6), "data": "chart","comp": False},
    "venn":               {"role": "data-comparison","ideal_count": (3, 3), "data": "none","comp": True},
    "waterfall":          {"role": "data-timeline",  "ideal_count": (3, 9), "data": "chart","comp": False},
    "table":              {"role": "reference",      "ideal_count": (3, 8), "data": "table","comp": True},
    "graphical":          {"role": "data-comparison","ideal_count": (3, 6), "data": "chart","comp": True},
    "components-showcase":{"role": "reference",      "ideal_count": (1, 4), "data": "none", "comp": False},
    "quote":              {"role": "quote",          "ideal_count": (1, 1), "data": "none", "comp": False},
    "end":                {"role": "closer",         "ideal_count": (1, 1), "data": "none", "comp": False},
    # --- Phase 4 layouts: C-suite narrative slides ---
    # `narrative_role`, `narrative_act`, `time_axis_role` are picker
    # fingerprints unique to Phase 4 — the scoring loop reads them only
    # when present, so legacy entries above remain neutral against the
    # new signals.
    "recommendation":     {"role": "content-columns", "ideal_count": (2, 3), "data": "none", "comp": False,
                           "narrative_role": "recommendation", "narrative_act": "resolution"},
    "next-steps":         {"role": "closer",         "ideal_count": (3, 7), "data": "none", "comp": False,
                           "narrative_role": "close-action", "narrative_act": "resolution"},
    "risk-register":      {"role": "reference",      "ideal_count": (4, 8), "data": "table", "comp": False,
                           "narrative_role": "risk"},
    "risk-matrix":        {"role": "data-comparison","ideal_count": (4, 10), "data": "none", "comp": True,
                           "narrative_role": "risk"},
    "roadmap":            {"role": "data-timeline",  "ideal_count": (3, 8), "data": "none", "comp": True,
                           "narrative_role": "plan", "time_axis_role": "strategic"},
    "timeline":           {"role": "data-timeline",  "ideal_count": (3, 8), "data": "none", "comp": False,
                           "narrative_role": "history", "time_axis_role": "chronological"},
    # --- Phase 5 layouts: diagram/viz types ---
    # Narrow band (1720x480 slot): for simple/medium concept diagrams up to
    # 8 nodes, where a horizontal flow reads well in a third of the slide.
    "excalidraw-diagram": {"role": "concept-diagram", "ideal_count": (2, 8), "data": "none", "comp": False,
                           "narrative_role": "system", "diagram_complexity": "simple"},
    "svg-infographic":    {"role": "data-comparison", "ideal_count": (3, 12), "data": "chart", "comp": True,
                           "narrative_role": "custom-viz", "diagram_complexity": "simple"},
    # Full-slide band (1720x720 slot, virtual 6880x2880 canvas): for deep
    # architecture diagrams with zones, typed arrows, and 10-20+ nodes.
    # Picked when the model passes `diagram_complexity=deep` OR when the
    # concept_count exceeds the narrow band's ideal range. The 4× virtual
    # canvas gives the author 16× more pixel area before crowding.
    "excalidraw-diagram-full": {"role": "concept-diagram", "ideal_count": (8, 20), "data": "none", "comp": False,
                                "narrative_role": "system", "diagram_complexity": "deep"},
    "svg-infographic-full":    {"role": "data-comparison", "ideal_count": (8, 24), "data": "chart", "comp": True,
                                "narrative_role": "custom-viz", "diagram_complexity": "deep"},
}


# Layouts that came in with Phase 4 — used by tests + docs to draw the
# line between "legacy scoring" (inert against new signals) and "Phase 4
# scoring" (affinity-driven by narrative_role / narrative_act /
# time_axis_role). The list lives in source-of-truth here so callers
# don't drift.
_PHASE4_LAYOUTS = frozenset({
    "recommendation",
    "next-steps",
    "risk-register",
    "risk-matrix",
    "roadmap",
    "timeline",
    "excalidraw-diagram",
})


def _classify_data(data_quantity: int | None) -> str:
    if data_quantity is None or data_quantity == 0:
        return "none"
    if data_quantity <= 4:
        return "kpi"
    if data_quantity <= 25:
        return "table"
    return "chart"


def pick_layout(
    role: str | None = None,
    concept_count: int | None = None,
    data_quantity: int | None = None,
    comparison: bool | None = None,
    narrative_role: str | None = None,
    *,
    narrative_act: str | None = None,
    time_axis_role: str | None = None,
    audience_mode: str | None = None,
    diagram_kind: Literal["concept", "chart"] | None = None,
    diagram_complexity: Literal["simple", "medium", "deep"] | None = None,
    layout_history: list | None = None,
    top_k: int = 3,
) -> list[dict]:
    """Return up to `top_k` candidate layouts ranked by affinity score.

    Each entry is a dict {layout, score, rationale}.

    `narrative_act`, `time_axis_role`, and `audience_mode` are now
    active scoring inputs:
    - `narrative_act` / `time_axis_role` contribute +1 each when they
      match a Phase 4 layout's declared affinity. Legacy layouts don't
      declare these fields, so they remain neutral against the signals
      (no bonus, no penalty).
    - `audience_mode` shifts the concept_count preference: +0.5 to
      layouts whose ideal_count low end is within 1 of `concept_count`
      when `presentation` (sparser), or whose high end is within 1
      when `discussion` (denser).

    `narrative_role` (the legacy signal) also gets a +2 affinity bonus
    when it matches a Phase 4 layout's declared `narrative_role`.
    Layouts without a declared `narrative_role` stay neutral against it.

    `layout_history` is an optional list of recently-used layout IDs
    (most recent last). It applies a small variety penalty so the same
    layout is not picked on consecutive slides: the immediately preceding
    layout loses 0.5 points, the one before that loses 0.25. Structural
    layouts (title slides, chapter openers, agenda, end) are exempt
    from this penalty since they never rotate. The penalty never
    eliminates a layout — it only breaks ties in favour of variety.
    """
    if narrative_act is not None and narrative_act not in _VALID_NARRATIVE_ACTS:
        raise ValueError(
            f"narrative_act: {narrative_act!r} not in "
            f"{sorted(_VALID_NARRATIVE_ACTS)}"
        )
    if time_axis_role is not None and time_axis_role not in _VALID_TIME_AXIS_ROLES:
        raise ValueError(
            f"time_axis_role: {time_axis_role!r} not in "
            f"{sorted(_VALID_TIME_AXIS_ROLES)}"
        )
    if audience_mode is not None and audience_mode not in _VALID_AUDIENCE_MODES:
        raise ValueError(
            f"audience_mode: {audience_mode!r} not in "
            f"{sorted(_VALID_AUDIENCE_MODES)}"
        )
    if diagram_complexity is not None and diagram_complexity not in _VALID_DIAGRAM_COMPLEXITY:
        raise ValueError(
            f"diagram_complexity: {diagram_complexity!r} not in "
            f"{sorted(_VALID_DIAGRAM_COMPLEXITY)}"
        )

    # Inference: if the caller didn't pass `diagram_complexity` but
    # `concept_count` is high enough to suggest a dense diagram, set
    # complexity=deep so the full-slide layouts get the affinity bonus.
    # This keeps the existing narrow `excalidraw-diagram` favored for the
    # 2-8 node case and steers naturally toward `excalidraw-diagram-full`
    # for richer architectures.
    if diagram_complexity is None and concept_count is not None and concept_count >= 8:
        diagram_complexity = "deep"

    data_band = _classify_data(data_quantity)
    cc = concept_count or 0

    scored: list[dict] = []
    for layout_id, profile in _LAYOUTS.items():
        score = 0.0
        rationale_parts: list[str] = []

        if role and profile["role"] == role:
            score += 3
            rationale_parts.append("role")
        elif role:
            score -= 1

        lo, hi = profile["ideal_count"]
        if cc:
            if lo <= cc <= hi:
                score += 2
                rationale_parts.append(f"count={cc}∈[{lo},{hi}]")
            elif lo - 1 <= cc <= hi + 1:
                score += 1
                rationale_parts.append(f"count={cc}~[{lo},{hi}]")

        if data_band != "none" and profile["data"] == data_band:
            score += 2
            rationale_parts.append(f"data={data_band}")

        if comparison is not None and profile["comp"] == comparison:
            score += 1
            rationale_parts.append("comp")

        # Phase 4 affinity scoring: a layout that declares one of these
        # optional fields gets a bonus when the caller's signal matches.
        # Layouts without the field (legacy) silently skip — no penalty,
        # so the existing scoring contract holds for them.
        if narrative_role and profile.get("narrative_role") == narrative_role:
            score += 2
            rationale_parts.append(f"narr-role={narrative_role}")
        if narrative_act and profile.get("narrative_act") == narrative_act:
            score += 1
            rationale_parts.append(f"narr-act={narrative_act}")
        if time_axis_role and profile.get("time_axis_role") == time_axis_role:
            score += 1
            rationale_parts.append(f"time-axis={time_axis_role}")

        # audience_mode bonus: nudges sparser layouts in presentation
        # mode, denser in discussion. Applied to ALL layouts (legacy +
        # Phase 4), keyed on the layout's ideal_count range vs the
        # caller's concept_count — no per-layout schema field needed.
        # Only fires when both concept_count and audience_mode are set.
        if audience_mode and cc:
            if audience_mode == "presentation" and lo - 1 <= cc <= lo + 1:
                score += 0.5
                rationale_parts.append("audience=presentation/sparser")
            elif audience_mode == "discussion" and hi - 1 <= cc <= hi + 1:
                score += 0.5
                rationale_parts.append("audience=discussion/denser")

        # Programmatic when_not_to_use enforcement. Each entry in
        # profile["when_not_to_use"] is "<signal_name>=<value>" (e.g.
        # "narrative_role=closing"). Any matching signal subtracts 3 points,
        # enough to fall below an otherwise-equal candidate. Penalty is
        # additive across multiple matches.
        neg_rules = profile.get("when_not_to_use", []) or []
        caller_signals = {
            "role": role,
            "concept_count": concept_count,
            "data_quantity": data_quantity,
            "comparison": comparison,
            "narrative_role": narrative_role,
            "narrative_act": narrative_act,
            "time_axis_role": time_axis_role,
            "audience_mode": audience_mode,
            "diagram_kind": diagram_kind,
        }
        neg_hits = []
        caller_signals["diagram_complexity"] = diagram_complexity
        for rule in neg_rules:
            if "=" not in rule:
                continue
            sig, expected = rule.split("=", 1)
            actual = caller_signals.get(sig.strip())
            if str(actual).lower() == expected.strip().lower():
                score -= 3
                neg_hits.append(rule)
        if neg_hits:
            rationale_parts.append(f"negative-guidance:{','.join(neg_hits)}")

        # Variety penalty: nudge recently-used layouts down so the deck
        # avoids visual monotony (Presenton principle: adjacent slides
        # should differ unless necessary). Structural layouts are exempt.
        if layout_history and layout_id not in _VARIETY_EXEMPT:
            if len(layout_history) >= 1 and layout_history[-1] == layout_id:
                score -= 0.5
                rationale_parts.append("variety-penalty(last)")
            elif len(layout_history) >= 2 and layout_history[-2] == layout_id:
                score -= 0.25
                rationale_parts.append("variety-penalty(prev)")

        # diagram_kind affinity: steers toward the canonical diagram layout
        # for the requested kind. Applied after existing scoring so it
        # overrides ties without disturbing the base signals.
        if diagram_kind == "concept":
            if layout_id in ("excalidraw-diagram", "excalidraw-diagram-full"):
                score += 3
                rationale_parts.append("diagram_kind=concept")
            elif profile["data"] == "chart":
                score -= 2
                rationale_parts.append("diagram_kind=concept/anti-chart")
        elif diagram_kind == "chart":
            if layout_id in ("svg-infographic", "svg-infographic-full"):
                score += 2
                rationale_parts.append("diagram_kind=chart")

        # diagram_complexity affinity: +2 when the layout's declared
        # complexity matches the caller's signal (deep → -full layouts,
        # simple/medium → narrow layouts). Layouts without a declared
        # complexity field stay neutral.
        if diagram_complexity and profile.get("diagram_complexity") == diagram_complexity:
            score += 2
            rationale_parts.append(f"diagram_complexity={diagram_complexity}")
        elif diagram_complexity == "deep" and profile.get("diagram_complexity") == "simple":
            # Explicit deep request actively *demotes* the narrow layouts so
            # the picker doesn't fall back to them when the user asked for
            # depth and the ideal_count is borderline.
            score -= 1
            rationale_parts.append("diagram_complexity=deep/anti-narrow")

        # Include layouts with positive score, OR layouts that received a
        # when_not_to_use penalty (so the planning agent can read the
        # negative-guidance rationale even though the layout ranked low).
        if score > 0 or neg_hits:
            scored.append({
                "layout": layout_id,
                "score": score,
                "rationale": rationale_parts if rationale_parts else ["—"],
            })

    scored.sort(key=lambda c: (-c["score"], c["layout"]))
    return scored[:top_k]
