"""Unit tests for lib/dsl/polish — pure text-normalization functions."""
from __future__ import annotations

from lib.dsl.polish import normalize_text


def test_smart_double_quotes_en():
    assert normalize_text('He said "hi" to me.', locale="en") == \
        'He said “hi” to me.'


def test_smart_double_quotes_de():
    assert normalize_text('Er sagte "hallo" zu mir.', locale="de") == \
        'Er sagte „hallo“ zu mir.'


def test_em_dash_double_hyphen():
    assert normalize_text("foo--bar", locale="en") == "foo—bar"


def test_true_minus_in_percentage():
    assert normalize_text("-1.2%", locale="en") == "−1.2%"


def test_true_minus_only_for_numeric_context():
    # Hyphen inside a word stays a hyphen.
    assert normalize_text("data-driven", locale="en") == "data-driven"


def test_ellipsis_normalization():
    assert normalize_text("wait...", locale="en") == "wait…"


def test_double_space_collapse():
    assert normalize_text("a  b   c", locale="en") == "a b c"


def test_empty_string_passes_through():
    assert normalize_text("", locale="en") == ""


def test_unknown_locale_falls_back_to_en():
    assert normalize_text('say "hi"', locale="xx") == 'say “hi”'


def test_idempotent():
    # Re-applying normalization yields the same result.
    src = 'He said "x--y" -1% wait...'
    once = normalize_text(src, locale="en")
    twice = normalize_text(once, locale="en")
    assert once == twice
