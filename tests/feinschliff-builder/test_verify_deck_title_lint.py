"""Tests for verify/deck/title_lint.py — deterministic title rules."""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _lint(title: str):
    """Convenience: lint a single title string."""
    from feinschliff.verify.deck.title_lint import lint_titles
    return lint_titles([title])


def _rules(title: str) -> set[str]:
    return {i.rule for i in _lint(title)}


# ---------------------------------------------------------------------------
# Rule: title-empty
# ---------------------------------------------------------------------------

def test_empty_title_fails():
    issues = _lint("")
    assert any(i.rule == "title-empty" and i.severity == "fail" for i in issues)


def test_whitespace_only_title_fails():
    issues = _lint("   ")
    assert any(i.rule == "title-empty" and i.severity == "fail" for i in issues)


def test_nonempty_title_no_empty_issue():
    issues = _lint("Revenue grew 18% in Q3")
    assert not any(i.rule == "title-empty" for i in issues)


# ---------------------------------------------------------------------------
# Rule: title-too-long
# ---------------------------------------------------------------------------

def test_long_title_fails_at_21_words():
    # 21 words exactly
    title = " ".join(["word"] * 21)
    issues = _lint(title)
    assert any(i.rule == "title-too-long" and i.severity == "fail" for i in issues)


def test_long_title_warns_at_16():
    # 16 words exactly
    title = " ".join(["word"] * 16)
    issues = _lint(title)
    assert any(i.rule == "title-too-long" and i.severity == "warn" for i in issues)


def test_long_title_warns_at_20():
    title = " ".join(["word"] * 20)
    issues = _lint(title)
    assert any(i.rule == "title-too-long" and i.severity == "warn" for i in issues)


def test_short_title_no_length_issue():
    issues = _lint("Revenue grew 18% in Q3")
    assert not any(i.rule == "title-too-long" for i in issues)


def test_exactly_15_words_no_length_issue():
    title = " ".join(["word"] * 15)
    issues = _lint(title)
    assert not any(i.rule == "title-too-long" for i in issues)


# ---------------------------------------------------------------------------
# Rule: title-no-verb
# ---------------------------------------------------------------------------

def test_no_verb_warns():
    # Pure topic label: no verb
    issues = _lint("Market Overview")
    assert any(i.rule == "title-no-verb" and i.severity == "warn" for i in issues)


def test_irregular_verb_passes():
    # "is" is an irregular verb
    issues = _lint("The market is shifting from on-prem to cloud")
    assert not any(i.rule == "title-no-verb" for i in issues)


def test_verb_suffix_s_passes():
    # "drives" has suffix -s on ≥4-char word
    issues = _lint("Cost drives our decisions")
    assert not any(i.rule == "title-no-verb" for i in issues)


def test_verb_suffix_ed_passes():
    issues = _lint("Revenue expanded in Q3")
    assert not any(i.rule == "title-no-verb" for i in issues)


def test_verb_suffix_ing_passes():
    issues = _lint("Team is building new products")
    assert not any(i.rule == "title-no-verb" for i in issues)


def test_acronym_not_treated_as_verb():
    # "AI" is uppercase — should be ignored; title still has no verb
    issues = _lint("AI Overview")
    assert any(i.rule == "title-no-verb" for i in issues)


def test_number_not_treated_as_verb():
    # Pure number tokens should not trigger verb match
    issues = _lint("Q3 2025 Results")
    # "Results" has suffix -s on 6-char word → verb found
    assert not any(i.rule == "title-no-verb" for i in issues)


# ---------------------------------------------------------------------------
# Rule: title-and-conjunction
# ---------------------------------------------------------------------------

def test_and_conjunction_warns():
    issues = _lint("Cost and Revenue trends for Q3")
    assert any(i.rule == "title-and-conjunction" and i.severity == "warn" for i in issues)


def test_and_conjunction_case_insensitive():
    issues = _lint("Cost AND Revenue")
    assert any(i.rule == "title-and-conjunction" for i in issues)


def test_no_and_no_conjunction_issue():
    issues = _lint("Revenue grew 18% in Q3")
    assert not any(i.rule == "title-and-conjunction" for i in issues)


def test_and_inside_word_not_flagged():
    # "bandwidth" contains "and" as substring but is not a standalone word
    issues = _lint("Expanding bandwidth saves costs")
    assert not any(i.rule == "title-and-conjunction" for i in issues)


# ---------------------------------------------------------------------------
# Multiple titles + clean pass
# ---------------------------------------------------------------------------

def test_clean_titles_pass():
    from feinschliff.verify.deck.title_lint import lint_titles

    titles = [
        "Revenue grew 18% in Q3",
        "Three forces drive this shift",
        "We must act now",
    ]
    issues = lint_titles(titles)
    assert issues == []


def test_slide_indices_are_1_based():
    from feinschliff.verify.deck.title_lint import lint_titles

    titles = ["Market Overview", ""]
    issues = lint_titles(titles)
    slides = {i.slide for i in issues}
    assert 1 in slides   # "Market Overview" → no-verb → slide 1
    assert 2 in slides   # empty → slide 2


def test_multiple_violations_on_same_slide():
    from feinschliff.verify.deck.title_lint import lint_titles

    # Long AND topic-label AND conjunction: 16 words, no verb, has "and"
    title = "Market Overview and Revenue Summary " + " ".join(["item"] * 12)
    issues = lint_titles([title])
    rules = {i.rule for i in issues}
    assert "title-too-long" in rules
    assert "title-no-verb" in rules
    assert "title-and-conjunction" in rules
