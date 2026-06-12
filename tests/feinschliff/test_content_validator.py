"""Unit tests for lib/content_validator — pre-render content lints."""
from __future__ import annotations

from feinschliff.content_validator import (
    ContentDefect,
    validate_content,
    format_defects,
)


def test_empty_content_is_clean():
    """No content keys → no defects."""
    defects = validate_content({}, slide_index=1)
    assert defects == []


def test_validate_content_returns_list_of_defects():
    """Return shape is always list[ContentDefect]."""
    defects = validate_content({"title": "a b c"}, slide_index=1)
    assert isinstance(defects, list)
    assert all(isinstance(d, ContentDefect) for d in defects)


def test_content_defect_has_required_fields():
    """ContentDefect carries kind, slide_index, slot, message."""
    d = ContentDefect(kind="title-length", slide_index=3, slot="title",
                      message="example")
    assert d.kind == "title-length"
    assert d.slide_index == 3
    assert d.slot == "title"
    assert d.message == "example"


def test_format_defects_empty():
    """Empty defect list produces the clean message."""
    assert "clean" in format_defects({}).lower()


def test_format_defects_with_one_defect():
    """Formatted output mentions slide index, kind, and message."""
    d = ContentDefect(kind="title-length", slide_index=2, slot="title",
                      message="title too long: 22 words")
    out = format_defects({2: [d]})
    assert "slide 2" in out
    assert "title-length" in out
    assert "title too long: 22 words" in out


# ---------- title-length ----------

def test_title_length_under_limit_passes():
    """≤15 words → no defect."""
    ctx = {"title": "Q3 revenue dropped twelve percent due to enterprise churn"}
    assert validate_content(ctx, slide_index=1) == []


def test_title_length_at_limit_passes():
    """Exactly 15 words → no defect."""
    title = " ".join(f"word{i}" for i in range(15))
    assert validate_content({"title": title}, slide_index=1) == []


def test_title_length_over_word_limit_fails():
    """16 words → title-length defect."""
    title = " ".join(f"word{i}" for i in range(16))
    defects = validate_content({"title": title}, slide_index=1)
    assert len(defects) == 1
    assert defects[0].kind == "title-length"
    assert "16" in defects[0].message
    assert defects[0].slot == "title"


def test_title_length_too_many_lines_fails():
    """≥3 manual newlines in title → title-length defect."""
    title = "Line one\nline two\nline three"
    defects = validate_content({"title": title}, slide_index=1)
    assert len(defects) == 1
    assert defects[0].kind == "title-length"
    assert "lines" in defects[0].message


def test_title_length_two_lines_passes():
    """Exactly 2 lines is allowed."""
    title = "Line one\nline two"
    assert validate_content({"title": title}, slide_index=1) == []


def test_title_length_skipped_when_no_title():
    """ctx without 'title' key → no title-length defect."""
    assert validate_content({"body": "anything"}, slide_index=1) == []


def test_title_length_skipped_when_empty_title():
    """Empty title → no defect (let downstream handle empty rendering)."""
    assert validate_content({"title": ""}, slide_index=1) == []
    assert validate_content({"title": "   "}, slide_index=1) == []


def test_title_length_emits_both_defects_when_both_limits_breached():
    """A title that's both too long AND too many lines → 2 defects."""
    # 16 words spread across 3 lines.
    title = "\n".join([
        " ".join(f"w{i}" for i in range(6)),   # line 1: 6 words
        " ".join(f"w{i}" for i in range(6, 11)),  # line 2: 5 words
        " ".join(f"w{i}" for i in range(11, 16)),  # line 3: 5 words → total 16
    ])
    defects = validate_content({"title": title}, slide_index=1)
    assert len(defects) == 2
    kinds = {d.kind for d in defects}
    assert kinds == {"title-length"}
    messages = [d.message for d in defects]
    # one message mentions the 16-word breach, one mentions the 3-line breach
    assert any("16" in m and "words" in m for m in messages)
    assert any("3" in m and "lines" in m for m in messages)


# ---------- action-verb-leading ----------

def test_action_starts_with_imperative_passes():
    """Verb-led action items → no defect."""
    ctx = {"actions": ["Grow revenue 20%", "Minimize churn", "Launch pilot"]}
    assert validate_content(ctx, slide_index=1) == []


def test_action_starts_with_noun_fails():
    """Noun-led action item → action-verb-leading defect."""
    ctx = {"actions": ["Revenue growth strategy"]}
    defects = validate_content(ctx, slide_index=1)
    assert len(defects) == 1
    assert defects[0].kind == "action-verb-leading"
    assert defects[0].slot == "actions[0]"


def test_recommendations_slot_also_checked():
    """recommendations[] is treated like actions[]."""
    ctx = {"recommendations": ["Better customer experience"]}
    defects = validate_content(ctx, slide_index=1)
    assert len(defects) == 1
    assert defects[0].kind == "action-verb-leading"
    assert defects[0].slot == "recommendations[0]"


def test_mitigations_slot_also_checked():
    """mitigations[] is treated like actions[]."""
    ctx = {"mitigations": ["Risk assessment quarterly"]}
    defects = validate_content(ctx, slide_index=1)
    assert len(defects) == 1
    assert defects[0].slot == "mitigations[0]"


def test_each_bad_item_flagged_independently():
    """Multiple bad items → multiple defects with correct indices."""
    ctx = {"actions": ["Grow revenue",
                       "Customer outreach",
                       "Launch pilot",
                       "Product strategy"]}
    defects = validate_content(ctx, slide_index=1)
    kinds = [d.slot for d in defects]
    assert "actions[1]" in kinds
    assert "actions[3]" in kinds
    assert len(defects) == 2


def test_action_with_dict_uses_verb_field():
    """Action items as dicts use the 'verb' key (Phase-4 schema)."""
    ctx = {"actions": [{"verb": "Grow", "what": "revenue 20%"},
                       {"verb": "Strategy", "what": "review"}]}
    defects = validate_content(ctx, slide_index=1)
    assert len(defects) == 1
    assert defects[0].slot == "actions[1].verb"


def test_empty_actions_list_is_clean():
    """Empty list → no defects, no crash."""
    assert validate_content({"actions": []}, slide_index=1) == []


def test_extra_imperatives_env_var(monkeypatch):
    """FEINSCHLIFF_EXTRA_IMPERATIVES extends the whitelist."""
    monkeypatch.setenv("FEINSCHLIFF_EXTRA_IMPERATIVES", "Foo,Bar")
    ctx = {"actions": ["Foo the thing", "Bar the other thing"]}
    assert validate_content(ctx, slide_index=1) == []


def test_imperative_check_case_insensitive():
    """Lowercase / mixed-case verbs still match."""
    ctx = {"actions": ["grow revenue", "LAUNCH pilot"]}
    assert validate_content(ctx, slide_index=1) == []


def test_emit_defects_and_abort_message(capsys):
    """Helper prints formatted defects + abort line to stderr."""
    from feinschliff.content_validator import emit_defects_and_abort_message
    d = ContentDefect(kind="title-length", slide_index=2, slot="title",
                      message="title too long: 22 words")
    emit_defects_and_abort_message({2: [d]}, cli_name="deck build")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "title-length" in captured.err
    assert "slide 2" in captured.err
    assert "feinschliff deck build: aborting" in captured.err


# ---------- pyramid-arity ----------
#
# `_PYRAMID_ARITY_LAYOUTS` ships empty (no production layout has a clean
# 2-3 supporting-arguments slot — executive-summary.insights is 3-5 per
# schema, conflicting with the 2-3 Pyramid bound). The Phase 4
# `recommendation` layout is the intended consumer. To still cover the
# framework, these tests register a synthetic layout via monkeypatch.

import pytest
from feinschliff import content_validator as cv


@pytest.fixture
def pyramid_layout(monkeypatch):
    """Register a synthetic layout → `claims` slot in the routing table."""
    monkeypatch.setitem(cv._PYRAMID_ARITY_LAYOUTS, "test-pyramid", "claims")
    return "test-pyramid"


def test_pyramid_arity_at_lower_bound_passes(pyramid_layout):
    """2 claims → clean (Pyramid Principle minimum)."""
    ctx = {"claims": ["First claim", "Second claim"]}
    assert validate_content(ctx, slide_index=1, layout=pyramid_layout) == []


def test_pyramid_arity_at_upper_bound_passes(pyramid_layout):
    """3 claims → clean (Pyramid Principle maximum)."""
    ctx = {"claims": ["First", "Second", "Third"]}
    assert validate_content(ctx, slide_index=1, layout=pyramid_layout) == []


def test_pyramid_arity_one_argument_fails(pyramid_layout):
    """Single claim → pyramid-arity defect."""
    ctx = {"claims": ["Lone claim"]}
    defects = validate_content(ctx, slide_index=1, layout=pyramid_layout)
    assert len(defects) == 1
    assert defects[0].kind == "pyramid-arity"
    assert defects[0].slot == "claims"
    assert "1" in defects[0].message and ("2" in defects[0].message or "3" in defects[0].message)


def test_pyramid_arity_four_arguments_fails(pyramid_layout):
    """4 claims → pyramid-arity defect."""
    ctx = {"claims": ["a", "b", "c", "d"]}
    defects = validate_content(ctx, slide_index=1, layout=pyramid_layout)
    assert len(defects) == 1
    assert defects[0].kind == "pyramid-arity"
    assert "4" in defects[0].message


def test_pyramid_arity_skipped_when_no_arguments_slot(pyramid_layout):
    """ctx without the routed slot → no pyramid-arity defect."""
    assert validate_content({"title": "anything"}, slide_index=1, layout=pyramid_layout) == []


def test_pyramid_arity_empty_list_fails(pyramid_layout):
    """Empty claims list → defect (zero is below 2)."""
    defects = validate_content({"claims": []}, slide_index=1, layout=pyramid_layout)
    assert len(defects) == 1
    assert defects[0].kind == "pyramid-arity"


def test_pyramid_arity_skipped_on_non_pyramid_layout():
    """A layout NOT in the routing table → no pyramid-arity defect,
    even with 1 item in a coincidentally-named slot."""
    ctx = {"claims": ["Lone claim"], "arguments": ["Also lone"]}
    # No layout → off.
    assert validate_content(ctx, slide_index=1) == []
    # Wrong layout → off.
    assert validate_content(ctx, slide_index=1, layout="action-title") == []


def test_pyramid_arity_fires_on_real_recommendation_layout():
    """Now that Phase 4 activates pyramid-arity for the recommendation layout,
    a 4-item recommendations slot should trip without monkeypatching."""
    ctx = {
        "title": "Four recommendations",
        "recommendations": [
            {"verb_phrase": "Cut SaaS sprawl"},
            {"verb_phrase": "Re-onboard top accounts"},
            {"verb_phrase": "Sunset weak SKUs"},
            {"verb_phrase": "Hire Director CS"},
        ],
    }
    defects = validate_content(ctx, slide_index=1, layout="recommendation")
    arity_defects = [d for d in defects if d.kind == "pyramid-arity"]
    assert len(arity_defects) == 1
    assert arity_defects[0].slot == "recommendations"
    assert "4" in arity_defects[0].message  # mentions the count


def test_pyramid_arity_clean_on_3_recommendations():
    """3 recommendations is exactly the Pyramid Principle sweet spot."""
    ctx = {
        "recommendations": [{"verb_phrase": x} for x in ("Grow", "Cut", "Hire")],
    }
    defects = validate_content(ctx, slide_index=1, layout="recommendation")
    assert not any(d.kind == "pyramid-arity" for d in defects)


def test_chunking_clean_on_3_recommendations():
    """3 recommendations is also clean for chunking-3-to-9."""
    ctx = {
        "recommendations": [{"verb_phrase": x} for x in ("Grow", "Cut", "Hire")],
    }
    defects = validate_content(ctx, slide_index=1, layout="recommendation")
    assert not any(d.kind == "chunking-3-to-9" for d in defects)


# ---------- chunking-3-to-9 ----------
#
# `key-takeaways` is the canonical Phase 3 consumer; its list slot is
# named `cards`.

def test_chunking_at_lower_bound_passes():
    """3 cards on key-takeaways → clean."""
    ctx = {"cards": ["a", "b", "c"]}
    assert validate_content(ctx, slide_index=1, layout="key-takeaways") == []


def test_chunking_at_upper_bound_passes():
    """9 cards on key-takeaways → clean (chunking-3-to-9 max)."""
    ctx = {"cards": [f"card{i}" for i in range(9)]}
    assert validate_content(ctx, slide_index=1, layout="key-takeaways") == []


def test_chunking_two_items_fails():
    """2 cards on key-takeaways → chunking-3-to-9 defect."""
    ctx = {"cards": ["a", "b"]}
    defects = validate_content(ctx, slide_index=1, layout="key-takeaways")
    assert len(defects) == 1
    assert defects[0].kind == "chunking-3-to-9"
    assert defects[0].slot == "cards"
    assert "2" in defects[0].message


def test_chunking_ten_items_fails():
    """10 cards on key-takeaways → chunking-3-to-9 defect."""
    ctx = {"cards": [f"c{i}" for i in range(10)]}
    defects = validate_content(ctx, slide_index=1, layout="key-takeaways")
    assert len(defects) == 1
    assert defects[0].kind == "chunking-3-to-9"
    assert "10" in defects[0].message


def test_chunking_skipped_when_no_cards_slot():
    """ctx without `cards` on key-takeaways → no chunking-3-to-9 defect."""
    assert validate_content({"title": "x"}, slide_index=1, layout="key-takeaways") == []


def test_chunking_skipped_on_non_chunking_layout():
    """A layout NOT in the routing table → no chunking-3-to-9 defect,
    even with 2 items in a coincidentally-named slot."""
    ctx = {"cards": ["a", "b"], "items": ["a", "b"]}
    # No layout → off.
    assert validate_content(ctx, slide_index=1) == []
    # Wrong layout → off.
    assert validate_content(ctx, slide_index=1, layout="action-title") == []


def test_both_validators_fire_independently(pyramid_layout, monkeypatch):
    """A slide can have BOTH a pyramid-arity AND a chunking-3-to-9
    defect when both validators are routed to the same layout."""
    # Register the same synthetic layout for chunking too.
    monkeypatch.setitem(cv._CHUNKING_LAYOUTS, pyramid_layout, "bullets")
    ctx = {"claims": ["lone"], "bullets": ["a", "b"]}
    defects = validate_content(ctx, slide_index=1, layout=pyramid_layout)
    kinds = sorted(d.kind for d in defects)
    assert kinds == ["chunking-3-to-9", "pyramid-arity"]


# ---------- vague-so-what ----------

def test_so_what_clean_with_numeric_anchor():
    """A so_what with numeric anchor passes despite vague words."""
    ctx = {"so_what": "Improving revenue by leveraging cross-sell drove 12% growth"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "vague-so-what" for d in defects)


def test_so_what_clean_with_proper_noun():
    """A so_what with a specific named referent passes despite vagueness."""
    ctx = {"so_what": "Optimizing AcmeCorp deployment streamlined onboarding"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "vague-so-what" for d in defects)


def test_so_what_fires_on_pure_vagueness():
    """Two+ vague words with no concrete anchor fires the defect."""
    ctx = {"so_what": "Leveraging synergies to enable transformative innovation"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    vague = [d for d in defects if d.kind == "vague-so-what"]
    assert len(vague) == 1
    assert vague[0].slot == "so_what"


def test_so_what_clean_with_single_vague_word():
    """One vague word alone isn't enough signal — false-positive guard."""
    ctx = {"so_what": "Improving customer onboarding reduced first-week churn"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "vague-so-what" for d in defects)


def test_so_what_skipped_on_non_chart_layout():
    """Pure vagueness on a non-chart layout: no defect (lint doesn't apply)."""
    ctx = {"so_what": "Leveraging synergies to enable transformative innovation"}
    defects = validate_content(ctx, slide_index=1, layout="key-takeaways")
    assert not any(d.kind == "vague-so-what" for d in defects)


def test_so_what_missing_slot_is_clean():
    """ctx without so_what key: no defect."""
    defects = validate_content({"title": "Q3 chart"}, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "vague-so-what" for d in defects)


# ---------- title-length on action_title (Phase 1-6 deep-verify regression) ----------

def test_title_length_fires_on_action_title_slot():
    """Phase 1's title-length lint must also check `action_title` (the
    conventional Feinschliff title slot in most content layouts).
    
    Regression: pre-fix the lint only inspected ctx["title"], silently
    bypassing all action-title-using layouts (recommendation, exec-summary,
    bar-chart, etc.). Verified end-to-end in the Phase 1-6 deep-verify pass.
    """
    long_title = " ".join(f"w{i}" for i in range(20))  # 20 words → over the 15 limit
    defects = validate_content({"action_title": long_title}, slide_index=1)
    matching = [d for d in defects if d.kind == "title-length"]
    assert len(matching) == 1
    assert matching[0].slot == "action_title"
    assert "20" in matching[0].message


def test_title_length_fires_on_both_title_and_action_title():
    """If both `title` and `action_title` are over the limit, both fire
    with their respective slot names — useful when a layout uses both
    (e.g. a hero slide carrying its own title + the deck's action_title)."""
    long = " ".join(f"w{i}" for i in range(20))
    defects = validate_content(
        {"title": long, "action_title": long},
        slide_index=1,
    )
    slots = {d.slot for d in defects if d.kind == "title-length"}
    assert "title" in slots
    assert "action_title" in slots


# ---------- filler-word ----------

def test_filler_word_fires_on_two_fillers_in_so_what():
    """≥2 filler words in so_what → filler-word defect."""
    ctx = {"so_what": "Revenue very really grew because of better conversion"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    filler = [d for d in defects if d.kind == "filler-word"]
    assert len(filler) == 1
    assert filler[0].slot == "so_what"
    assert filler[0].slide_index == 1


def test_filler_word_single_filler_passes():
    """One filler word is noise — should not fire."""
    ctx = {"so_what": "Revenue really grew 12% due to enterprise renewals"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "filler-word" for d in defects)


def test_filler_word_fires_even_with_numeric_anchor():
    """Unlike vague-so-what, a numeric anchor does NOT clear filler-word.
    'Very extremely grew 12%' still has too many fillers."""
    ctx = {"so_what": "Churn very extremely dropped by 8% this quarter"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    filler = [d for d in defects if d.kind == "filler-word"]
    assert len(filler) == 1


def test_filler_word_skipped_on_non_chart_layout():
    """filler-word only applies to SO_WHAT_LAYOUTS — not key-takeaways etc."""
    ctx = {"so_what": "Revenue very really grew due to better conversion"}
    defects = validate_content(ctx, slide_index=1, layout="key-takeaways")
    assert not any(d.kind == "filler-word" for d in defects)


def test_filler_word_skipped_when_no_so_what_slot():
    """Missing so_what key → no filler-word defect."""
    defects = validate_content({"title": "Q3"}, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "filler-word" for d in defects)


def test_filler_word_empty_so_what_is_clean():
    """Empty so_what string → no filler-word defect."""
    ctx = {"so_what": ""}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "filler-word" for d in defects)


def test_filler_word_fires_on_all_so_what_layouts():
    """filler-word must fire on every layout in _SO_WHAT_LAYOUTS."""
    from feinschliff.content_validator import _SO_WHAT_LAYOUTS
    padded = "Revenue very really grew this quarter due to retention"
    for layout in _SO_WHAT_LAYOUTS:
        defects = validate_content({"so_what": padded}, slide_index=1, layout=layout)
        filler = [d for d in defects if d.kind == "filler-word"]
        assert len(filler) == 1, (
            f"Expected filler-word defect for layout={layout!r}, got {defects}"
        )


# ---------- vague-so-what with improved numeric detection ----------

def test_so_what_clean_with_percentage():
    """A so_what with a percentage anchor passes despite vague words."""
    ctx = {"so_what": "Improving leverage drove 12% growth in enterprise"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "vague-so-what" for d in defects)


def test_so_what_clean_with_currency():
    """A so_what with a currency anchor passes despite vague words."""
    ctx = {"so_what": "Optimizing synergies enabled $2M cost reduction"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "vague-so-what" for d in defects)


def test_so_what_clean_with_multiplier():
    """A so_what with a multiplier (3x) passes despite vague words."""
    ctx = {"so_what": "Streamlining innovation improved throughput 3x overall"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    assert not any(d.kind == "vague-so-what" for d in defects)


def test_so_what_extended_keywords_fire():
    """New keywords from the extended vague set trigger the defect."""
    ctx = {"so_what": "Unlocking holistic value across the ecosystem seamlessly"}
    defects = validate_content(ctx, slide_index=1, layout="bar-chart")
    vague = [d for d in defects if d.kind == "vague-so-what"]
    assert len(vague) == 1, f"Expected vague-so-what, got {defects}"
