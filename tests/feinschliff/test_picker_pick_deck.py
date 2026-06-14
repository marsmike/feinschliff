"""Tests for the arc-aware deck-level picker (feinschliff.picker)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_slides(n: int) -> list[dict]:
    """Return a minimal list of n slide signal dicts."""
    slides = []
    for i in range(n):
        role = "cover" if i == 0 else ("closer" if i == n - 1 else "content")
        slides.append({"role": role, "concept_count": 3})
    return slides


def _brand_available() -> bool:
    try:
        from feinschmiede.brand_discovery import find_brand
        find_brand("feinschliff")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _brand_available(), reason="feinschliff brand not found")
def test_pick_deck_returns_report_per_slide():
    from feinschliff.picker import pick_deck

    report = pick_deck(_make_slides(3), brand="feinschliff")
    assert len(report.picks) == 3
    for i, pick in enumerate(report.picks):
        assert pick.slide_index == i + 1
        assert pick.layout
        assert isinstance(pick.score, float)


@pytest.mark.skipif(not _brand_available(), reason="feinschliff brand not found")
def test_pick_deck_first_slide_is_cover_like():
    from feinschliff.picker import pick_deck

    report = pick_deck(_make_slides(3), brand="feinschliff")
    first = report.picks[0]
    layout_lower = first.layout.lower()
    assert "cover" in layout_lower or "title" in layout_lower, (
        f"Expected first slide layout to contain 'cover' or 'title', got: {first.layout!r}"
    )


@pytest.mark.skipif(not _brand_available(), reason="feinschliff brand not found")
def test_pick_deck_last_slide_is_closer_like():
    from feinschliff.picker import pick_deck

    report = pick_deck(_make_slides(3), brand="feinschliff")
    last = report.picks[-1]
    layout_lower = last.layout.lower()
    closer_terms = ("closer", "end", "closing", "cta", "thank")
    assert any(t in layout_lower for t in closer_terms), (
        f"Expected last slide layout to contain a closer term, got: {last.layout!r}"
    )


@pytest.mark.skipif(not _brand_available(), reason="feinschliff brand not found")
def test_pick_deck_runners_up_have_why_not():
    from feinschliff.picker import pick_deck

    report = pick_deck(_make_slides(3), brand="feinschliff", top_k=5)
    for pick in report.picks:
        for runner in pick.runners_up:
            assert runner.get("why_not"), (
                f"Runner-up {runner.get('layout')!r} on slide {pick.slide_index} "
                f"has empty why_not"
            )


@pytest.mark.skipif(not _brand_available(), reason="feinschliff brand not found")
def test_pick_deck_arc_warnings_emitted_for_missing_required_act():
    """deck_type=pitch with 3 generic slides → 'ask' (closing act) not found → warning."""
    from feinschliff.picker import pick_deck

    # Slides with no content hinting at 'ask'
    slides = [
        {"role": "cover", "concept_count": 2},
        {"role": "content", "concept_count": 4},
        {"role": "content", "concept_count": 3},
    ]
    deck_brief = {"deck_type": "pitch"}
    report = pick_deck(slides, brand="feinschliff", deck_brief=deck_brief)

    # The pitch arc has 'shift' (opening) and 'ask' (closing) as required acts.
    # With generic slides the arc warning for at least one should appear.
    assert report.arc_warnings, (
        "Expected at least one arc warning for pitch deck with no matching required acts"
    )
    warnings_text = " ".join(report.arc_warnings).lower()
    assert "shift" in warnings_text or "ask" in warnings_text, (
        f"Expected 'shift' or 'ask' in arc warnings, got: {report.arc_warnings}"
    )


@pytest.mark.skipif(not _brand_available(), reason="feinschliff brand not found")
def test_pick_deck_writes_json(tmp_path: Path):
    from feinschliff.picker import pick_deck
    from feinschliff.picker.report import write_picker_report

    report = pick_deck(_make_slides(2), brand="feinschliff")
    out = tmp_path / "picker_report.json"
    write_picker_report(report, out)

    assert out.is_file()
    data = json.loads(out.read_text())
    assert "picks" in data
    assert "arc_warnings" in data
    assert len(data["picks"]) == 2
    for p in data["picks"]:
        assert "slide_index" in p
        assert "layout" in p
        assert "score" in p
        assert "runners_up" in p
        assert "overrides_applied" in p
