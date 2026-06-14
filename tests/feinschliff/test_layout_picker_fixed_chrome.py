"""fixed_chrome guard + description rationale in pick_layout.

Decompiled brand-pack layouts may declare `fixed_chrome: true` (decoration
carried verbatim from the source deck) and a `description` of what the
chrome depicts. The picker sinks fixed-chrome layouts for content/data
roles (-6, "fixed-chrome-guard") and surfaces the description in the
rationale so a planning LLM sees what's on the slide.
"""
from __future__ import annotations

import pytest

from feinschliff.layout_picker import _FIXED_CHROME_GUARD_ROLES, pick_layout

_DESC = "Three overlapping workshop illustrations on the left half"

_FAKE = {
    "brand-moment": {
        "role": "content-columns", "ideal_count": (2, 4),
        "data": "none", "comp": False,
        "fixed_chrome": True,
        "description": _DESC,
    },
    "plain-columns": {
        "role": "content-columns", "ideal_count": (2, 4),
        "data": "none", "comp": False,
    },
    "brand-chapter": {
        "role": "chapter-opener", "ideal_count": (1, 2),
        "data": "none", "comp": False,
        "fixed_chrome": True,
    },
    "baked-chevrons": {
        "role": "content-columns", "ideal_count": (2, 4),
        "data": "none", "comp": False,
        "chrome_text": True,
    },
    "baked-divider": {
        "role": "chapter-opener", "ideal_count": (1, 2),
        "data": "none", "comp": False,
        "chrome_text": True,
    },
}


def _entry(cands, layout_id):
    for c in cands:
        if c["layout"] == layout_id:
            return c
    return None


def test_fixed_chrome_layout_sinks_for_content_role():
    """Same profile shape, but fixed_chrome → exactly 6 points lower, with
    the guard tag in the rationale — sunk below the plain twin."""
    ranked = pick_layout(
        role="content-columns", concept_count=3, top_k=10, profiles=_FAKE,
    )
    plain = _entry(ranked, "plain-columns")
    gated = _entry(ranked, "brand-moment")
    assert plain is not None and gated is not None
    assert gated["score"] == plain["score"] - 6.0
    assert ranked[0]["layout"] == "plain-columns"
    assert "fixed-chrome-guard" in gated["rationale"]
    assert "fixed-chrome-guard" not in plain["rationale"]


@pytest.mark.parametrize("role", sorted(_FIXED_CHROME_GUARD_ROLES))
def test_guard_fires_for_every_content_role(role):
    """The guard keys on the *caller's* role signal, for all five content
    roles — even when the layout's own role doesn't match the request."""
    ranked = pick_layout(role=role, concept_count=3, top_k=10, profiles=_FAKE)
    gated = _entry(ranked, "brand-moment")
    # Guard-hit layouts stay visible (like when_not_to_use hits) so the
    # planner can read the demotion rationale even at a negative score.
    assert gated is not None
    assert "fixed-chrome-guard" in gated["rationale"]


def test_chrome_text_layout_sinks_for_content_role():
    """Chrome with baked <a:t> labels (`chrome_text: true`) cannot host
    rebindable text — same -6 sink as fixed_chrome, own rationale tag, so
    a planner sees WHY the layout sank (worldcup v4 slide-29 lesson)."""
    ranked = pick_layout(
        role="content-columns", concept_count=3, top_k=10, profiles=_FAKE,
    )
    plain = _entry(ranked, "plain-columns")
    baked = _entry(ranked, "baked-chevrons")
    assert plain is not None and baked is not None
    assert baked["score"] == plain["score"] - 6.0
    assert "baked-text-guard" in baked["rationale"]
    assert "baked-text-guard" not in plain["rationale"]


def test_chrome_text_guard_inert_for_framing_roles():
    """Framing picks are unaffected — baked text on a divider is fine."""
    ranked = pick_layout(
        role="chapter-opener", concept_count=1, top_k=10, profiles=_FAKE,
    )
    baked = _entry(ranked, "baked-divider")
    assert baked is not None
    assert baked["score"] == 5.0  # role +3, count-in-band +2 — no guard
    assert "baked-text-guard" not in baked["rationale"]


def test_guard_inert_for_framing_roles():
    """A fixed-chrome chapter opener is exactly the brand moment the flag
    exists for — title/framing picks are unaffected."""
    ranked = pick_layout(
        role="chapter-opener", concept_count=1, top_k=10, profiles=_FAKE,
    )
    chapter = _entry(ranked, "brand-chapter")
    assert chapter is not None
    assert chapter["score"] == 5.0  # role +3, count-in-band +2 — no guard
    assert "fixed-chrome-guard" not in chapter["rationale"]


def test_guard_inert_without_role_signal():
    """No caller role → nothing to guard against."""
    ranked = pick_layout(concept_count=3, top_k=10, profiles=_FAKE)
    gated = _entry(ranked, "brand-moment")
    assert gated is not None
    assert "fixed-chrome-guard" not in gated["rationale"]


def test_description_shows_in_rationale():
    ranked = pick_layout(
        role="content-columns", concept_count=3, top_k=10, profiles=_FAKE,
    )
    gated = _entry(ranked, "brand-moment")
    assert f"desc:{_DESC}" in gated["rationale"]
    # Layouts without a description don't grow a desc part.
    plain = _entry(ranked, "plain-columns")
    assert not any(p.startswith("desc:") for p in plain["rationale"])


def test_when_to_use_shows_in_rationale():
    """Positive selection guidance rides next to desc: — a planner reading
    pick output sees when the layout is meant to be used."""
    profiles = {
        "guided": {
            "role": "content-columns", "ideal_count": (2, 4),
            "data": "none", "comp": False,
            "when_to_use": "KPI walls for quarterly reviews",
        },
        "unguided": {
            "role": "content-columns", "ideal_count": (2, 4),
            "data": "none", "comp": False,
        },
    }
    ranked = pick_layout(
        role="content-columns", concept_count=3, top_k=5, profiles=profiles,
    )
    guided = _entry(ranked, "guided")
    assert "use:KPI walls for quarterly reviews" in guided["rationale"]
    unguided = _entry(ranked, "unguided")
    assert not any(p.startswith("use:") for p in unguided["rationale"])


def test_description_truncated_to_80_chars():
    long_desc = "x" * 200
    profiles = {
        "verbose": {
            "role": "content-columns", "ideal_count": (2, 4),
            "data": "none", "comp": False,
            "description": long_desc,
        },
    }
    ranked = pick_layout(
        role="content-columns", concept_count=3, top_k=5, profiles=profiles,
    )
    desc_parts = [p for p in ranked[0]["rationale"] if p.startswith("desc:")]
    assert desc_parts == [f"desc:{'x' * 80}"]
