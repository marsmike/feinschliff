"""Speech-anchor alignment: snap-to-words, extend-never-shorten, gap closing."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "feinschnitt" / "src"))
from feinschnitt.edit import EditError  # noqa: E402
from feinschnitt.edit import align  # noqa: E402
from feinschnitt.edit import verify as verifymod  # noqa: E402

WORDS = [
    {"w": "they", "s": 5.0, "e": 5.2}, {"w": "used", "s": 5.3, "e": 5.5},
    {"w": "ChatGPT,", "s": 5.6, "e": 6.1}, {"w": "Claude", "s": 6.3, "e": 6.7},
    {"w": "and", "s": 6.8, "e": 6.9}, {"w": "Grok", "s": 7.0, "e": 7.4},
    {"w": "to", "s": 8.0, "e": 8.1}, {"w": "build", "s": 8.2, "e": 8.5},
]


def test_anchor_snaps_start_and_extends_end():
    beat = {"kind": "stat_punch", "start_sec": 1.0, "end_sec": 2.0,
            "speech_anchor": "they used chatgpt"}
    out = align.align_beats([beat], WORDS)[0]
    assert abs(out["start_sec"] - (5.0 - align.LEAD)) < 0.01
    assert abs(out["end_sec"] - (6.1 + align.TAIL)) < 0.01


def test_authored_end_is_never_shortened():
    beat = {"kind": "stat_punch", "start_sec": 1.0, "end_sec": 9.5,
            "speech_anchor": "they used chatgpt"}
    out = align.align_beats([beat], WORDS)[0]
    assert out["end_sec"] == 9.5


def test_fuzzy_anchor_tolerates_one_mishearing():
    beat = {"kind": "stat_punch", "start_sec": 0.0, "end_sec": 1.0,
            "speech_anchor": "they used chatbot claude"}  # 3 of 4 tokens match
    out = align.align_beats([beat], WORDS)[0]
    assert abs(out["start_sec"] - (5.0 - align.LEAD)) < 0.01


def test_unmatched_anchor_is_flagged_not_fatal():
    beat = {"kind": "stat_punch", "start_sec": 1.0, "end_sec": 2.0,
            "speech_anchor": "completely different sentence entirely"}
    out = align.align_beats([beat], WORDS)[0]
    assert out["start_sec"] == 1.0 and out["_align"] == "anchor-not-found"


def test_non_sequence_kind_capped_at_max_beat():
    beat = {"kind": "stat_punch", "start_sec": 1.0, "end_sec": 2.0,
            "speech_anchor": "they used chatgpt claude and grok to build"}
    out = align.align_beats([beat], WORDS)[0]
    assert out["end_sec"] <= out["start_sec"] + align.MAX_BEAT + 0.01


def test_close_gaps_bridges_small_gaps_only():
    beats = [
        {"kind": "stat_punch", "start_sec": 1.0, "end_sec": 4.0},
        {"kind": "stat_punch", "start_sec": 4.3, "end_sec": 6.0},   # 0.3s gap → bridge
        {"kind": "stat_punch", "start_sec": 7.5, "end_sec": 9.0},   # 1.5s gap → keep
    ]
    out = align.close_gaps(beats)
    assert out[0]["end_sec"] == 4.3
    assert out[1]["end_sec"] == 6.0


def test_refrain_prefers_occurrence_near_authored_start():
    refrain = []
    for base in (2.0, 60.0):
        refrain += [
            {"w": "ship", "s": base, "e": base + 0.2},
            {"w": "it", "s": base + 0.3, "e": base + 0.4},
            {"w": "weekly", "s": base + 0.5, "e": base + 0.9},
        ]
    beat = {"kind": "stat_punch", "start_sec": 59.5, "end_sec": 61.0,
            "speech_anchor": "ship it weekly"}
    out = align.align_beats([beat], refrain)[0]
    assert abs(out["start_sec"] - (60.0 - align.LEAD)) < 0.01


def test_umlaut_anchor_matches_transliteration():
    words = [{"w": "schön", "s": 1.0, "e": 1.4}, {"w": "gebaut", "s": 1.5, "e": 1.9}]
    beat = {"kind": "stat_punch", "start_sec": 0.0, "end_sec": 1.0,
            "speech_anchor": "schoen gebaut"}
    out = align.align_beats([beat], words)[0]
    assert out["_align"] == "ok"


def test_extension_clamped_to_video_duration():
    words = [{"w": "final", "s": 9.0, "e": 9.4}, {"w": "words", "s": 9.5, "e": 9.9}]
    beat = {"kind": "stat_punch", "start_sec": 8.5, "end_sec": 9.9,
            "speech_anchor": "final words"}
    out = align.align_beats([beat], words, duration=10.0)[0]
    assert out["end_sec"] == 10.0


def test_run_roundtrip_and_derived_file(tmp_path):
    import json as _json
    words_path = tmp_path / "words.json"
    words_path.write_text(_json.dumps({"duration": 12.0, "words": [
        {"w": "hello", "s": 1.0, "e": 1.3}]}))
    plan = {"video": "x.mp4", "beats": [
        {"kind": "stat_punch", "start_sec": 0.5, "end_sec": 2.0,
         "speech_anchor": "hello", "value": "1", "caption": "c", "reason": "r"}]}
    out_path = tmp_path / "edit_plan.aligned.json"
    aligned = align.run(plan, words_path, out_path)
    assert out_path.exists()
    assert plan["beats"][0]["start_sec"] == 0.5  # authored plan untouched
    assert aligned["beats"][0]["_align"] == "ok"


def test_run_clean_error_on_malformed_words(tmp_path):
    bad = tmp_path / "words.json"
    bad.write_text("{}")
    with pytest.raises(EditError):
        align.run({"beats": []}, bad, tmp_path / "out.json")


def test_verify_duration_mismatch_fails():
    problems = verifymod.check_durations(source_dur=20.0, output_dur=18.0)
    assert problems
    assert "duration" in problems[0]


def test_verify_duration_within_tolerance_passes():
    assert verifymod.check_durations(20.0, 20.1) == []


def test_vertical_timeline_extension_not_capped():
    # Craft words that span > MAX_BEAT so a non-sequence kind would be capped.
    long_words = [
        {"w": "they", "s": 1.0, "e": 1.2},
        {"w": "used", "s": 1.5, "e": 1.7},
        {"w": "chatgpt", "s": 2.0, "e": 2.4},
        {"w": "claude", "s": 4.0, "e": 4.5},
        {"w": "and", "s": 5.5, "e": 5.7},
        {"w": "grok", "s": 6.5, "e": 6.9},
        {"w": "to", "s": 7.5, "e": 7.6},
        {"w": "build", "s": 8.0, "e": 8.5},
    ]
    beat = {"kind": "vertical_timeline", "start_sec": 1.0, "end_sec": 2.0,
            "speech_anchor": "they used chatgpt claude and grok to build"}
    out = align.align_beats([beat], long_words)[0]
    assert out["end_sec"] > out["start_sec"] + align.MAX_BEAT


# ---------------------------------------------------------------------------
# M2 Task 2 — quote_pull typewriter timing
# ---------------------------------------------------------------------------

QUOTE_WORDS = [
    {"w": "the", "s": 10.0, "e": 10.2}, {"w": "plan", "s": 10.3, "e": 10.6},
    {"w": "was", "s": 10.7, "e": 10.9}, {"w": "never", "s": 11.0, "e": 11.4},
    {"w": "the", "s": 11.5, "e": 11.6}, {"w": "bottleneck", "s": 11.7, "e": 12.4},
]


def test_quote_cps_derived_from_anchor_span():
    quote = "The plan was never the bottleneck."
    beat = {"kind": "quote_pull", "start_sec": 9.0, "end_sec": 11.0,
            "speech_anchor": "the plan was never the bottleneck",
            "quote_text": quote}
    out = align.align_beats([beat], QUOTE_WORDS)[0]
    expected_cps = len(quote) / (12.4 - 10.0)
    assert abs(out["chars_per_second"] - round(expected_cps, 2)) < 0.05


LONG_QUOTE_WORDS = [
    {"w": "the", "s": 10.0, "e": 10.2}, {"w": "plan", "s": 10.4, "e": 10.8},
    {"w": "was", "s": 11.0, "e": 11.3}, {"w": "never", "s": 11.6, "e": 12.1},
    {"w": "the", "s": 12.4, "e": 12.6}, {"w": "bottleneck", "s": 12.9, "e": 13.8},
]


def test_quote_dwell_extends_past_max_beat():
    quote = "The plan was never the bottleneck. The setup was."
    beat = {"kind": "quote_pull", "start_sec": 9.0, "end_sec": 10.0,
            "speech_anchor": "the plan was never the bottleneck",
            "quote_text": quote}
    out = align.align_beats([beat], LONG_QUOTE_WORDS)[0]
    typing_finish = (out["start_sec"] + align.QUOTE_GLYPH_LEAD
                     + len(quote) / out["chars_per_second"])
    assert out["end_sec"] >= typing_finish + align.QUOTE_DWELL_MIN - 0.01
    assert out["end_sec"] > out["start_sec"] + align.MAX_BEAT


def test_quote_without_anchor_uses_fallback_cps():
    beat = {"kind": "quote_pull", "start_sec": 1.0, "end_sec": 2.0,
            "quote_text": "Short quote."}
    out = align.align_beats([beat], QUOTE_WORDS)[0]
    assert out["chars_per_second"] == align.QUOTE_CPS_FALLBACK


def test_quote_dwell_clamped_to_duration():
    quote = "A quote near the very end of the video that wants more dwell."
    beat = {"kind": "quote_pull", "start_sec": 9.0, "end_sec": 10.0,
            "speech_anchor": "the plan was never the bottleneck",
            "quote_text": quote}
    out = align.align_beats([beat], QUOTE_WORDS, duration=12.0)[0]
    assert out["end_sec"] == 12.0


def test_quote_authored_long_end_never_shortened():
    beat = {"kind": "quote_pull", "start_sec": 9.0, "end_sec": 30.0,
            "quote_text": "Tiny."}
    out = align.align_beats([beat], QUOTE_WORDS)[0]
    assert out["end_sec"] == 30.0


def test_non_quote_kinds_unaffected_by_quote_logic():
    beat = {"kind": "stat_punch", "start_sec": 1.0, "end_sec": 2.0,
            "value": "10x", "caption": "c"}
    out = align.align_beats([beat], QUOTE_WORDS)[0]
    assert "chars_per_second" not in out


def test_quote_extension_never_shortens_anchor_extended_end():
    # Slow delivery + tiny quote: the quote-side end (13.2) lands BEFORE the
    # anchor-extended end (14.8). The floor must keep 14.8 — a regression that
    # floors on the authored end (10.0) would shrink it to 13.2.
    slow_words = [
        {"w": "trust", "s": 10.0, "e": 11.0}, {"w": "the", "s": 11.8, "e": 12.2},
        {"w": "process", "s": 13.0, "e": 14.0},
    ]
    beat = {"kind": "quote_pull", "start_sec": 9.5, "end_sec": 10.0,
            "speech_anchor": "trust the process", "quote_text": "Trust."}
    out = align.align_beats([beat], slow_words)[0]
    assert abs(out["end_sec"] - 14.8) < 0.01
