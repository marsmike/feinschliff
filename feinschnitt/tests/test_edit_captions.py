"""Caption generation: chunking, suppression, emphasis."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit import captions as capmod  # noqa: E402
from feinschnitt.edit import lint as lintmod  # noqa: E402


def w(text, s, e):
    return {"w": text, "s": s, "e": e}


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def test_chunks_break_on_max_words_and_punctuation():
    words = [w("one", 0.0, 0.2), w("two", 0.3, 0.5), w("three", 0.6, 0.8),
             w("four.", 0.9, 1.1), w("five", 1.3, 1.5)]
    chunks = capmod.chunk_words(words, max_words=3)
    # first 3 words hit max_words limit; "four." ends sentence; "five" alone
    assert [len(c["words"]) for c in chunks] == [3, 1, 1]


def test_chunks_break_on_gap():
    # gap of 0.6s between word 2 and word 3 triggers a break
    words = [w("hello", 0.0, 0.3), w("world", 0.4, 0.7), w("bye", 1.3, 1.6)]
    chunks = capmod.chunk_words(words, max_words=5)
    assert len(chunks) == 2
    assert chunks[0]["words"][0]["w"] == "hello"
    assert chunks[1]["words"][0]["w"] == "bye"


def test_chunk_tail_capped_by_next_chunk_start():
    # chunk 1 ends at 1.0 → tail would be 1.4, but next chunk starts at 1.2
    words = [w("alpha", 0.0, 1.0), w("beta", 1.2, 1.8)]
    chunks = capmod.chunk_words(words, max_words=1)
    # first chunk's e must be capped at 1.2 (next chunk start), not 1.4
    assert chunks[0]["e"] == 1.2


def test_chunk_tail_not_capped_for_last_chunk():
    words = [w("solo", 2.0, 2.5)]
    chunks = capmod.chunk_words(words, max_words=3)
    assert len(chunks) == 1
    assert abs(chunks[0]["e"] - (2.5 + capmod.CHUNK_TAIL)) < 0.001


# ---------------------------------------------------------------------------
# Suppression: suppressing kinds
# ---------------------------------------------------------------------------

def test_suppression_drops_chunk_inside_stat_punch():
    chunks = [{"s": 5.0, "e": 6.0, "words": [
        {"w": "amazing", "s": 5.0, "e": 5.5, "accent": False}]}]
    beats = [{"kind": "stat_punch", "start_sec": 4.5, "end_sec": 7.0,
              "value": "10x", "caption": "faster", "reason": "hero"}]
    result = capmod.suppress(chunks, beats)
    assert result == []


def test_suppression_keeps_chunk_inside_image_card_no_shared_words():
    # image_card is friendly — chunk survives if no semantic echo
    chunks = [{"s": 5.0, "e": 6.0, "words": [
        {"w": "hello", "s": 5.0, "e": 5.5, "accent": False}]}]
    beats = [{"kind": "image_card", "start_sec": 4.5, "end_sec": 7.0,
              "image_path": "pic.jpg", "caption": "product", "reason": "show"}]
    result = capmod.suppress(chunks, beats)
    assert len(result) == 1


def test_suppression_drops_chunk_inside_image_card_shared_meaningful_word():
    # chunk word "product" matches image_card caption "product" → dropped
    chunks = [{"s": 5.0, "e": 6.0, "words": [
        {"w": "product", "s": 5.0, "e": 5.5, "accent": False}]}]
    beats = [{"kind": "image_card", "start_sec": 4.5, "end_sec": 7.0,
              "image_path": "pic.jpg", "caption": "product", "reason": "show"}]
    result = capmod.suppress(chunks, beats)
    assert result == []


# ---------------------------------------------------------------------------
# Suppression: echo pad
# ---------------------------------------------------------------------------

def test_suppression_drops_chunk_in_echo_pad_sharing_meaningful_word():
    # chunk is 0.5s before the beat (within ±0.8s pad) and shares "bottleneck"
    chunks = [{"s": 9.5, "e": 10.2, "words": [
        {"w": "bottleneck", "s": 9.5, "e": 10.0, "accent": False}]}]
    beats = [{"kind": "quote_pull", "start_sec": 10.3, "end_sec": 14.0,
              "quote_text": "the bottleneck is trust", "reason": "thesis"}]
    result = capmod.suppress(chunks, beats)
    assert result == []


def test_suppression_keeps_chunk_in_echo_pad_sharing_only_stopwords():
    # "the" is a stopword — does not count as meaningful overlap
    chunks = [{"s": 9.5, "e": 10.2, "words": [
        {"w": "the", "s": 9.5, "e": 10.0, "accent": False}]}]
    beats = [{"kind": "quote_pull", "start_sec": 10.3, "end_sec": 14.0,
              "quote_text": "the bottleneck is trust", "reason": "thesis"}]
    result = capmod.suppress(chunks, beats)
    assert len(result) == 1


def test_suppression_umlaut_echo_drops_chunk():
    # chunk has "schön" (spoken), beat has "schoen" (typed) — _norm folds both
    chunks = [{"s": 5.0, "e": 5.8, "words": [
        {"w": "schön", "s": 5.0, "e": 5.5, "accent": False}]}]
    beats = [{"kind": "image_card", "start_sec": 4.5, "end_sec": 7.0,
              "image_path": "x.jpg", "caption": "schoen design", "reason": "r"}]
    result = capmod.suppress(chunks, beats)
    assert result == []


def test_suppression_skips_beat_with_invalid_timing():
    # start_sec is a string — beat must be skipped, chunk must survive
    chunks = [{"s": 5.0, "e": 6.0, "words": [
        {"w": "hello", "s": 5.0, "e": 5.5, "accent": False}]}]
    beats = [{"kind": "stat_punch", "start_sec": "x", "end_sec": 8.0,
              "value": "5x", "caption": "speed", "reason": "metric"}]
    result = capmod.suppress(chunks, beats)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Emphasis
# ---------------------------------------------------------------------------

def test_emphasis_marks_exact_word_run():
    chunks = [{"s": 0.0, "e": 1.5, "words": [
        {"w": "the", "s": 0.0, "e": 0.3, "accent": False},
        {"w": "bottleneck", "s": 0.4, "e": 0.9, "accent": False},
        {"w": "here", "s": 1.0, "e": 1.4, "accent": False},
    ]}]
    result_chunks, unmatched = capmod.apply_emphasis(chunks, ["bottleneck"])
    assert result_chunks[0]["words"][1]["accent"] is True
    assert result_chunks[0]["words"][0]["accent"] is False
    assert result_chunks[0]["words"][2]["accent"] is False
    assert unmatched == []


def test_emphasis_unmatched_phrase_returned_as_warning():
    chunks = [{"s": 0.0, "e": 1.0, "words": [
        {"w": "hello", "s": 0.0, "e": 0.5, "accent": False}]}]
    _, unmatched = capmod.apply_emphasis(chunks, ["bottleneck"])
    assert unmatched == ["bottleneck"]


def test_emphasis_multi_word_phrase():
    chunks = [{"s": 0.0, "e": 2.0, "words": [
        {"w": "fix", "s": 0.0, "e": 0.3, "accent": False},
        {"w": "the", "s": 0.4, "e": 0.6, "accent": False},
        {"w": "bottleneck", "s": 0.7, "e": 1.2, "accent": False},
        {"w": "now", "s": 1.3, "e": 1.8, "accent": False},
    ]}]
    result_chunks, unmatched = capmod.apply_emphasis(chunks, ["fix the bottleneck"])
    assert result_chunks[0]["words"][0]["accent"] is True
    assert result_chunks[0]["words"][1]["accent"] is True
    assert result_chunks[0]["words"][2]["accent"] is True
    assert result_chunks[0]["words"][3]["accent"] is False
    assert unmatched == []


# ---------------------------------------------------------------------------
# build_captions top-level
# ---------------------------------------------------------------------------

def test_build_captions_enabled_false_returns_empty():
    words = [w("hello", 0.0, 0.4), w("world", 0.5, 0.9)]
    chunks, warnings = capmod.build_captions(words, [], {"enabled": False}, 1080, 1920)
    assert chunks == []
    assert warnings == []


def test_build_captions_landscape_uses_5_word_chunks():
    # landscape: width > height → MAX_WORDS_LANDSCAPE = 5
    words = [w(f"w{i}", i * 0.2, i * 0.2 + 0.15) for i in range(6)]
    chunks, _ = capmod.build_captions(words, [], None, 1920, 1080)
    # 6 words at 5-word max → first chunk 5, second chunk 1
    assert chunks[0]["words"][0]["w"] == "w0"
    assert len(chunks[0]["words"]) == 5
    assert len(chunks[1]["words"]) == 1


# ---------------------------------------------------------------------------
# Kind coverage invariant
# ---------------------------------------------------------------------------

def test_classification_covers_all_kinds():
    assert (capmod.CAPTION_SUPPRESSING_KINDS | capmod.CAPTION_FRIENDLY_KINDS
            == lintmod.KNOWN_KINDS)


# ---------------------------------------------------------------------------
# Lint captions config
# ---------------------------------------------------------------------------

def test_lint_captions_config_bad_enabled_type():
    errors = lintmod.lint_captions_config({"enabled": "yes"})
    assert any("enabled" in e for e in errors)


def test_lint_captions_config_bad_emphasis_type():
    errors = lintmod.lint_captions_config({"emphasis": "bottleneck"})
    assert any("emphasis" in e for e in errors)


def test_lint_captions_config_valid_returns_empty():
    errors = lintmod.lint_captions_config(
        {"enabled": True, "emphasis": ["bottleneck", "trust"]}
    )
    assert errors == []


def test_lint_captions_config_not_a_dict():
    errors = lintmod.lint_captions_config("bad")
    assert any("dict" in e or "object" in e for e in errors)


def test_lint_captions_config_emphasis_not_list_of_strings():
    errors = lintmod.lint_captions_config({"emphasis": [1, 2, 3]})
    assert any("emphasis" in e for e in errors)
