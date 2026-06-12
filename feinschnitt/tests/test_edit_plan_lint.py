"""Plan loading + lint contracts."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit import EditError, plan as planmod  # noqa: E402
from feinschnitt.edit import lint as lintmod  # noqa: E402


def _write(tmp_path, payload):
    p = tmp_path / "edit_plan.json"
    p.write_text(json.dumps(payload))
    return p


def test_load_plan_ok(tmp_path):
    p = _write(tmp_path, {"video": "clip.mp4", "beats": [
        {"kind": "stat_punch", "start_sec": 1.6, "end_sec": 4.0,
         "value": "10×", "caption": "faster", "reason": "hero number"}]})
    loaded = planmod.load_plan(p)
    assert loaded["beats"][0]["kind"] == "stat_punch"


def test_load_plan_rejects_garbage(tmp_path):
    p = tmp_path / "edit_plan.json"
    p.write_text("not json")
    with pytest.raises(EditError):
        planmod.load_plan(p)


def test_load_plan_requires_beats_list(tmp_path):
    p = _write(tmp_path, {"video": "clip.mp4"})
    with pytest.raises(EditError):
        planmod.load_plan(p)


def test_load_plan_missing_file_is_clean_error(tmp_path):
    with pytest.raises(EditError):
        planmod.load_plan(tmp_path / "nope.json")


def _beat(**kw):
    base = {"kind": "stat_punch", "start_sec": 2.0, "end_sec": 5.0,
            "value": "10×", "caption": "faster", "reason": "hero number proof"}
    base.update(kw)
    return base


def test_lint_clean_plan_passes():
    beats = [
        {"kind": "hook_title", "start_sec": 0.0, "end_sec": 3.5,
         "title": "AI DID.", "kicker": "I DIDN'T EDIT THIS",
         "reason": "cold-open retention hook"},
        _beat(start_sec=5.0, end_sec=8.0),
    ]
    errors, warnings = lintmod.lint_beats(beats, duration=20.0)
    assert errors == []


def test_lint_missing_required_field_is_error():
    beats = [_beat()]
    del beats[0]["caption"]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("caption" in e for e in errors)


def test_lint_missing_reason_is_error():
    beats = [_beat()]
    del beats[0]["reason"]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("reason" in e for e in errors)


def test_lint_unknown_kind_is_error():
    errors, _ = lintmod.lint_beats([_beat(kind="dance_party")], duration=20.0)
    assert any("dance_party" in e for e in errors)


def test_lint_first_takeover_before_1_5s_is_error():
    errors, _ = lintmod.lint_beats([_beat(start_sec=0.8, end_sec=3.0)], duration=20.0)
    assert any("1.5" in e for e in errors)


def test_lint_hook_title_exempt_from_floor_but_low_vertical_text_is_error():
    beats = [{"kind": "word_pop", "start_sec": 2.0, "end_sec": 5.0,
              "vertical": 0.3, "reason": "emphasis line",
              "items": [{"text": "NOBODY", "appear_sec": 2.2}]}]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("vertical" in e for e in errors)


def test_lint_beat_past_video_end_is_error():
    errors, _ = lintmod.lint_beats([_beat(end_sec=25.0)], duration=20.0)
    assert any("duration" in e for e in errors)


def test_lint_density_and_missing_hook_are_warnings():
    beats = [_beat(start_sec=2.0 + i * 2.0, end_sec=3.5 + i * 2.0) for i in range(5)]
    errors, warnings = lintmod.lint_beats(beats, duration=30.0)
    assert errors == []
    assert any("density" in w for w in warnings)
    assert any("hook_title" in w for w in warnings)


def test_lint_string_timing_is_error_not_crash():
    errors, _ = lintmod.lint_beats([_beat(start_sec="2.0")], duration=20.0)
    assert any("start_sec" in e for e in errors)


def test_lint_bool_timing_is_error_not_crash():
    errors, _ = lintmod.lint_beats([_beat(start_sec=True)], duration=20.0)
    assert any("start_sec" in e for e in errors)


def test_lint_negative_start_is_error():
    beats = [{"kind": "hook_title", "start_sec": -2.0, "end_sec": 3.0,
              "title": "X", "reason": "hook for the cold open"}]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("start_sec" in e for e in errors)


def test_lint_null_reason_is_error():
    errors, _ = lintmod.lint_beats([_beat(reason=None)], duration=20.0)
    assert any("reason" in e for e in errors)


def test_lint_vertical_ceiling_is_error():
    beats = [{"kind": "word_pop", "start_sec": 2.0, "end_sec": 5.0, "vertical": 0.95,
              "reason": "emphasis", "items": [{"text": "X", "appear_sec": 2.2}]}]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("vertical" in e for e in errors)


def test_lint_appear_sec_outside_window_is_error():
    beats = [{"kind": "word_pop", "start_sec": 2.0, "end_sec": 5.0,
              "reason": "emphasis", "items": [{"text": "X", "appear_sec": 9.0}]}]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("appear_sec" in e for e in errors)


def test_lint_malformed_items_is_error_not_crash():
    beats = [{"kind": "word_pop", "start_sec": 2.0, "end_sec": 5.0,
              "reason": "emphasis", "items": [2.2]},
             {"kind": "word_pop", "start_sec": 6.0, "end_sec": 8.0,
              "reason": "emphasis", "items": "FAST"}]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("items[0]" in e for e in errors)
    assert any("must be a list" in e for e in errors)


# ---------------------------------------------------------------------------
# M2 new kinds — happy paths
# ---------------------------------------------------------------------------

def test_lint_quote_pull_ok():
    beat = {"kind": "quote_pull", "start_sec": 2.0, "end_sec": 8.0,
            "quote_text": "Done is better than perfect.", "reason": "credibility hook"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert errors == []


def test_lint_quote_pull_missing_quote_text():
    beat = {"kind": "quote_pull", "start_sec": 2.0, "end_sec": 8.0,
            "reason": "credibility hook"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("quote_text" in e for e in errors)


def test_lint_static_ok(tmp_path):
    img = tmp_path / "slide.png"
    img.write_bytes(b"fake")
    beat = {"kind": "static", "start_sec": 2.0, "end_sec": 6.0,
            "image_path": str(img), "reason": "product screenshot"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0, base_dir=tmp_path)
    assert errors == []


def test_lint_static_missing_image_path():
    beat = {"kind": "static", "start_sec": 2.0, "end_sec": 6.0,
            "reason": "product screenshot"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("image_path" in e for e in errors)


def test_lint_vertical_timeline_ok():
    beat = {"kind": "vertical_timeline", "start_sec": 2.0, "end_sec": 10.0,
            "steps": [{"heading": "Plan", "appear_sec": 3.0},
                      {"heading": "Build", "appear_sec": 6.0}],
            "reason": "roadmap walkthrough"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert errors == []


def test_lint_vertical_timeline_missing_steps():
    beat = {"kind": "vertical_timeline", "start_sec": 2.0, "end_sec": 10.0,
            "reason": "roadmap walkthrough"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("steps" in e for e in errors)


def test_lint_image_card_ok(tmp_path):
    img = tmp_path / "photo.jpg"
    img.write_bytes(b"fake")
    beat = {"kind": "image_card", "start_sec": 2.0, "end_sec": 6.0,
            "image_path": str(img), "reason": "social proof visual"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0, base_dir=tmp_path)
    assert errors == []


def test_lint_image_card_missing_image_path():
    beat = {"kind": "image_card", "start_sec": 2.0, "end_sec": 6.0,
            "reason": "social proof visual"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("image_path" in e for e in errors)


def test_lint_ratio_dots_ok():
    beat = {"kind": "ratio_dots", "start_sec": 2.0, "end_sec": 7.0,
            "total": 10, "marked": 7, "polarity": "positive",
            "mark_at": 3.5, "reason": "conversion rate proof"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert errors == []


def test_lint_ratio_dots_missing_fields():
    beat = {"kind": "ratio_dots", "start_sec": 2.0, "end_sec": 7.0,
            "reason": "conversion rate proof"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("total" in e for e in errors)


def test_lint_inline_chart_ok():
    beat = {"kind": "inline_chart", "start_sec": 2.0, "end_sec": 8.0,
            "title": "Monthly Growth", "data": [10, 25, 40],
            "reason": "growth trend proof"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert errors == []


def test_lint_inline_chart_missing_fields():
    beat = {"kind": "inline_chart", "start_sec": 2.0, "end_sec": 8.0,
            "reason": "growth trend proof"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("title" in e for e in errors)


# ---------------------------------------------------------------------------
# M2 per-kind validation — detailed error cases
# ---------------------------------------------------------------------------

def test_lint_vertical_timeline_steps_non_list_is_error():
    beat = {"kind": "vertical_timeline", "start_sec": 2.0, "end_sec": 10.0,
            "steps": "Plan → Build → Ship", "reason": "roadmap"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("must be a list" in e for e in errors)


def test_lint_vertical_timeline_appear_sec_outside_window_is_error():
    beat = {"kind": "vertical_timeline", "start_sec": 2.0, "end_sec": 10.0,
            "steps": [{"heading": "Plan", "appear_sec": 15.0}],
            "reason": "roadmap"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("appear_sec" in e and "outside the beat window" in e for e in errors)


def test_lint_ratio_dots_marked_exceeds_total_is_error():
    beat = {"kind": "ratio_dots", "start_sec": 2.0, "end_sec": 7.0,
            "total": 10, "marked": 12, "polarity": "positive",
            "mark_at": 3.5, "reason": "stat"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("marked" in e and "exceeds" in e and "total" in e for e in errors)


def test_lint_ratio_dots_bad_polarity_is_error():
    beat = {"kind": "ratio_dots", "start_sec": 2.0, "end_sec": 7.0,
            "total": 10, "marked": 7, "polarity": "neutral",
            "mark_at": 3.5, "reason": "stat"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("polarity" in e for e in errors)


def test_lint_ratio_dots_string_total_is_error_not_crash():
    beat = {"kind": "ratio_dots", "start_sec": 2.0, "end_sec": 7.0,
            "total": "12", "marked": 7, "polarity": "positive",
            "mark_at": 3.5, "reason": "stat"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("total" in e for e in errors)


def test_lint_inline_chart_one_point_data_is_error():
    beat = {"kind": "inline_chart", "start_sec": 2.0, "end_sec": 8.0,
            "title": "Growth", "data": [42], "reason": "trend"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert any("data" in e and "at least 2" in e for e in errors)


# ---------------------------------------------------------------------------
# image_path — file existence with/without base_dir
# ---------------------------------------------------------------------------

def test_lint_image_path_missing_file_with_base_dir_is_error(tmp_path):
    beat = {"kind": "static", "start_sec": 2.0, "end_sec": 6.0,
            "image_path": "nonexistent.png", "reason": "screenshot"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0, base_dir=tmp_path)
    assert any("image not found" in e for e in errors)


def test_lint_image_path_missing_file_without_base_dir_no_image_error():
    beat = {"kind": "static", "start_sec": 2.0, "end_sec": 6.0,
            "image_path": "nonexistent.png", "reason": "screenshot"}
    errors, _ = lintmod.lint_beats([beat], duration=20.0)
    assert not any("image not found" in e for e in errors)


# ---------------------------------------------------------------------------
# Reading-time warnings
# ---------------------------------------------------------------------------

def test_lint_reading_time_too_short_warns():
    # 60-char quote, 1.0s window → viewer can't finish
    quote = "A" * 60
    beat = {"kind": "quote_pull", "start_sec": 2.0, "end_sec": 3.0,
            "quote_text": quote, "reason": "social proof"}
    _, warnings = lintmod.lint_beats([beat], duration=20.0)
    assert any("can't finish reading" in w for w in warnings)


def test_lint_reading_time_too_long_warns():
    # Very short text, 20s window → text lingers
    beat = {"kind": "stat_punch", "start_sec": 2.0, "end_sec": 22.0,
            "value": "10×", "caption": "x", "reason": "hero stat"}
    _, warnings = lintmod.lint_beats([beat], duration=30.0)
    assert any("lingers" in w for w in warnings)


# ---------------------------------------------------------------------------
# Image breathing room (plan-level)
# ---------------------------------------------------------------------------

def test_lint_image_breath_back_to_back_warns(tmp_path):
    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    img1.write_bytes(b"x")
    img2.write_bytes(b"x")
    beats = [
        {"kind": "static", "start_sec": 2.0, "end_sec": 5.0,
         "image_path": str(img1), "reason": "screenshot one"},
        {"kind": "image_card", "start_sec": 5.4, "end_sec": 8.0,
         "image_path": str(img2), "reason": "screenshot two"},
    ]
    _, warnings = lintmod.lint_beats(beats, duration=20.0, base_dir=tmp_path)
    assert any("slideshow" in w for w in warnings)


def test_lint_image_breath_far_apart_no_warn(tmp_path):
    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    img1.write_bytes(b"x")
    img2.write_bytes(b"x")
    beats = [
        {"kind": "static", "start_sec": 2.0, "end_sec": 5.0,
         "image_path": str(img1), "reason": "screenshot one"},
        {"kind": "image_card", "start_sec": 7.0, "end_sec": 10.0,
         "image_path": str(img2), "reason": "screenshot two"},
    ]
    _, warnings = lintmod.lint_beats(beats, duration=20.0, base_dir=tmp_path)
    assert not any("slideshow" in w for w in warnings)


def test_lint_mark_at_outside_window_is_error():
    beats = [{"kind": "ratio_dots", "start_sec": 2.0, "end_sec": 5.0,
              "reason": "ratio", "total": 12, "marked": 9,
              "polarity": "negative", "mark_at": 9.0}]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("mark_at" in e for e in errors)


def test_lint_authored_low_vertical_on_new_overlay_is_error():
    beats = [{"kind": "image_card", "start_sec": 2.0, "end_sec": 5.0,
              "reason": "broll", "image_path": "x.png", "vertical": 0.2}]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("vertical" in e for e in errors)
