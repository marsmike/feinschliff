"""Theme resolution, zoom heuristic, props assembly."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit import EditError  # noqa: E402
from feinschnitt.edit import props as propsmod  # noqa: E402
from feinschnitt.edit import theme as thememod  # noqa: E402
from feinschnitt.edit import zoom as zoommod  # noqa: E402


def test_default_theme_without_brand():
    t = thememod.resolve_theme(None)
    assert set(t) >= {"bg", "text", "muted", "accent", "fontTitle", "fontBody"}


def test_theme_from_brand_tokens(tmp_path):
    (tmp_path / "tokens.json").write_text(json.dumps({
        "color": {
            "black": {"$value": "#0B1A33"},
            "paper": {"$value": "#F5F1E8"},
            "silver": {"$value": "#A9BCD6"},
            "accent": {"$value": "#C9A24A"},
        },
        "font-family": {"display": {"$value": ["Archivo", "Helvetica", "sans-serif"]}},
    }))
    t = thememod.resolve_theme(tmp_path)
    assert t["bg"] == "#0B1A33" and t["accent"] == "#C9A24A"
    assert t["fontTitle"] == "Archivo, Helvetica, sans-serif"


def test_zoom_plan_spacing_and_number_boost():
    words = []
    t = 0.0
    for k in range(40):
        text = "$400M." if k == 20 else ("word." if k % 8 == 7 else "word")
        words.append({"w": text, "s": round(t, 2), "e": round(t + 0.3, 2)})
        t += 0.5
    plan = zoommod.build_zoom_plan(words)
    assert plan, "expected at least one zoom window"
    for a, b in zip(plan, plan[1:]):
        assert b["start_sec"] - a["start_sec"] >= zoommod.MIN_SPACING - 0.01
    assert any(z["scale"] >= 1.08 for z in plan)  # the $400M sentence


def test_props_assembly(tmp_path):
    aligned = {"beats": [{"kind": "stat_punch", "start_sec": 2.0, "end_sec": 5.0,
                          "value": "10×", "caption": "faster", "reason": "r"}]}
    meta = {"duration": 20.0, "width": 1080, "height": 1920}
    out = propsmod.build_props(
        source_path="/abs/clip.mp4", aligned_plan=aligned, zoom_plan=[],
        theme=thememod.resolve_theme(None), meta=meta, fps=30)
    assert out["durationSec"] == 20.0 and out["fps"] == 30
    assert out["beats"][0]["kind"] == "stat_punch"
    assert out["theme"]["accent"]


def test_theme_dark_pack_text_not_bg(tmp_path):
    (tmp_path / "tokens.json").write_text(json.dumps({
        "color": {
            "black": {"$value": "#2E3440"},
            "paper": {"$value": "#2E3440"},
            "off-white": {"$value": "#ECEFF4"},
            "off-white-2": {"$value": "#D8DEE9"},
            "accent": {"$value": "#88C0D0"},
        }}))
    t = thememod.resolve_theme(tmp_path)
    assert t["text"] == "#ECEFF4"
    assert t["text"] != t["bg"]


def test_theme_missing_tokens_with_explicit_brand_is_error(tmp_path):
    with pytest.raises(EditError):
        thememod.resolve_theme(tmp_path / "no-such-brand")


def test_theme_corrupt_tokens_is_clean_error(tmp_path):
    (tmp_path / "tokens.json").write_text("not json")
    with pytest.raises(EditError):
        thememod.resolve_theme(tmp_path)


def test_props_injects_vertical_defaults():
    aligned = {"beats": [
        {"kind": "word_pop", "start_sec": 2.0, "end_sec": 5.0, "reason": "r",
         "items": [{"text": "X", "appear_sec": 2.2}]},
        {"kind": "hook_title", "start_sec": 0.0, "end_sec": 3.0, "title": "T",
         "reason": "r", "vertical": 0.8},
    ]}
    meta = {"duration": 20.0, "width": 1080, "height": 1920}
    out = propsmod.build_props("clip.mp4", aligned, [], thememod.resolve_theme(None),
                               meta)
    assert out["beats"][0]["vertical"] == 0.72   # injected default
    assert out["beats"][1]["vertical"] == 0.8    # authored value untouched
    assert "vertical" not in aligned["beats"][0]  # input not mutated
