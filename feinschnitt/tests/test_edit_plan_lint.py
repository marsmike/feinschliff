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


def test_lint_malformed_items_is_error_not_crash():
    beats = [{"kind": "word_pop", "start_sec": 2.0, "end_sec": 5.0,
              "reason": "emphasis", "items": [2.2]},
             {"kind": "word_pop", "start_sec": 6.0, "end_sec": 8.0,
              "reason": "emphasis", "items": "FAST"}]
    errors, _ = lintmod.lint_beats(beats, duration=20.0)
    assert any("items[0]" in e for e in errors)
    assert any("must be a list" in e for e in errors)
