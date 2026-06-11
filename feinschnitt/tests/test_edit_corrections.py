"""Deterministic transcription corrections (brand words + phrases)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit.corrections import apply_corrections  # noqa: E402


def w(text, s, e):
    return {"w": text, "s": s, "e": e}


def test_brand_word_preserves_capitalization():
    words = [w("Cloud", 0.0, 0.4), w("cloud", 0.5, 0.9), w("code", 1.0, 1.3)]
    out = apply_corrections(words)
    assert [x["w"] for x in out] == ["Claude", "claude", "code"]
    assert out[0]["s"] == 0.0 and out[0]["e"] == 0.4  # timing untouched


def test_phrase_merge_keeps_span_timing():
    words = [w("the", 0.0, 0.2), w("fine", 0.3, 0.6), w("schnitt", 0.7, 1.1), w("tool", 1.2, 1.5)]
    out = apply_corrections(words)
    assert [x["w"] for x in out] == ["the", "feinschnitt", "tool"]
    merged = out[1]
    assert merged["s"] == 0.3 and merged["e"] == 1.1


def test_untouched_words_pass_through():
    words = [w("hello", 0.0, 0.3), w("world", 0.4, 0.8)]
    assert apply_corrections(words) == words


def test_punctuation_is_preserved_around_replacement():
    words = [w("Cloud,", 0.0, 0.4), w("fine", 0.5, 0.8), w("schnitt.", 0.9, 1.3)]
    out = apply_corrections(words)
    assert [x["w"] for x in out] == ["Claude,", "feinschnitt."]


def test_leading_whitespace_tokens_still_match():
    words = [w(" cloud", 0.0, 0.4)]
    assert apply_corrections(words)[0]["w"] == "claude"
