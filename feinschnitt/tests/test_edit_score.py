"""M4 audio-score tests — Task 1: SFX cue derivation + lint_score_config.

Task 2 tests (score.py) will be appended here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit import sfx as sfxmod  # noqa: E402
from feinschnitt.edit.lint import lint_score_config  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _beat(kind, start, end=None):
    return {"kind": kind, "start_sec": start, "end_sec": end or start + 2.0,
            "reason": "test beat"}


def _chunk(s, e, accent_words=()):
    words = [{"w": "plain", "s": s, "e": s + 0.1}]
    for word in accent_words:
        words.append({"w": word, "accent": True, "s": s + 0.5, "e": s + 0.8})
    return {"s": s, "e": e, "words": words}


# ---------------------------------------------------------------------------
# derive_cues: hook whoosh
# ---------------------------------------------------------------------------

def test_hook_produces_whoosh_once():
    beats = [
        _beat("hook_title", 0.0),
        _beat("hook_title", 0.5),  # second hook_title — whoosh only fires on first
    ]
    cues = sfxmod.derive_cues(beats, [])
    whooshes = [c for c in cues if c["kind"] == "whoosh"]
    assert len(whooshes) == 1
    assert whooshes[0]["at"] == 0.0


def test_hook_with_invalid_start_ignored():
    beats = [
        {"kind": "hook_title", "start_sec": "bad", "end_sec": 2.0, "reason": "x"},
        _beat("hook_title", 1.0),
    ]
    cues = sfxmod.derive_cues(beats, [])
    whooshes = [c for c in cues if c["kind"] == "whoosh"]
    # "bad" is a string — skipped; the valid hook fires
    assert len(whooshes) == 1
    assert whooshes[0]["at"] == 1.0


# ---------------------------------------------------------------------------
# derive_cues: pop for takeovers, none for overlays
# ---------------------------------------------------------------------------

def test_pops_for_takeover_kinds():
    beats = [
        _beat("stat_punch", 2.0),
        _beat("quote_pull", 4.0),
        _beat("static", 6.0),
        _beat("vertical_timeline", 8.0),
    ]
    cues = sfxmod.derive_cues(beats, [])
    pops = [c for c in cues if c["kind"] == "pop"]
    assert len(pops) == 4
    assert [p["at"] for p in pops] == [2.0, 4.0, 6.0, 8.0]


def test_no_pop_for_overlay_kinds():
    beats = [
        _beat("hook_title", 0.0),   # overlay — no pop (does produce whoosh)
        _beat("word_pop", 1.0),     # overlay
        _beat("image_card", 2.0),   # overlay
        _beat("ratio_dots", 3.0),   # overlay
        _beat("inline_chart", 4.0), # overlay
    ]
    cues = sfxmod.derive_cues(beats, [])
    pops = [c for c in cues if c["kind"] == "pop"]
    assert pops == []


# ---------------------------------------------------------------------------
# derive_cues: emphasis strokes, last suppressed
# ---------------------------------------------------------------------------

def test_emphasis_strokes_last_suppressed():
    captions = [
        _chunk(1.0, 1.5, accent_words=["great"]),
        _chunk(2.0, 2.5, accent_words=["amazing"]),
        _chunk(3.0, 3.5, accent_words=["incredible"]),
    ]
    cues = sfxmod.derive_cues([], captions)
    strokes = [c for c in cues if c["kind"] == "stroke"]
    # 3 emphasis chunks → first 2 fire, last suppressed
    assert len(strokes) == 2
    assert strokes[0]["at"] == 1.0
    assert strokes[1]["at"] == 2.0


def test_single_emphasis_produces_zero_strokes():
    captions = [_chunk(1.0, 1.5, accent_words=["only"])]
    cues = sfxmod.derive_cues([], captions)
    strokes = [c for c in cues if c["kind"] == "stroke"]
    assert strokes == []


def test_no_strokes_for_non_accent_chunks():
    captions = [
        _chunk(1.0, 1.5),
        _chunk(2.0, 2.5),
    ]
    cues = sfxmod.derive_cues([], captions)
    strokes = [c for c in cues if c["kind"] == "stroke"]
    assert strokes == []


# ---------------------------------------------------------------------------
# derive_cues: empty inputs and sorting
# ---------------------------------------------------------------------------

def test_empty_beats_and_captions_returns_empty():
    assert sfxmod.derive_cues([], []) == []


def test_cues_sorted_by_time():
    beats = [_beat("stat_punch", 5.0), _beat("quote_pull", 2.0)]
    captions = [
        _chunk(1.0, 1.5, accent_words=["first"]),
        _chunk(3.0, 3.5, accent_words=["second"]),
        _chunk(7.0, 7.5, accent_words=["third"]),
    ]
    cues = sfxmod.derive_cues(beats, captions)
    times = [c["at"] for c in cues]
    assert times == sorted(times)


def test_bool_start_sec_skipped():
    # bool is a subclass of int — must be rejected for start_sec
    beats = [
        {"kind": "stat_punch", "start_sec": True, "end_sec": 2.0, "reason": "x"},
        {"kind": "quote_pull", "start_sec": False, "end_sec": 3.0, "reason": "x"},
        _beat("static", 4.0),
    ]
    cues = sfxmod.derive_cues(beats, [])
    pops = [c for c in cues if c["kind"] == "pop"]
    assert len(pops) == 1
    assert pops[0]["at"] == 4.0


# ---------------------------------------------------------------------------
# resolve_assets
# ---------------------------------------------------------------------------

def test_resolve_assets_stem_match(tmp_path):
    (tmp_path / "whoosh.wav").touch()
    (tmp_path / "pop.mp3").touch()
    assets = sfxmod.resolve_assets(tmp_path)
    assert "whoosh" in assets
    assert "pop" in assets
    assert assets["whoosh"].name == "whoosh.wav"


def test_resolve_assets_first_wins_on_duplicates(tmp_path):
    # sorted order: whoosh.mp3 < whoosh.wav alphabetically
    (tmp_path / "whoosh.mp3").touch()
    (tmp_path / "whoosh.wav").touch()
    assets = sfxmod.resolve_assets(tmp_path)
    assert assets["whoosh"].name == "whoosh.mp3"


def test_resolve_assets_non_matching_ignored(tmp_path):
    (tmp_path / "background.mp3").touch()
    (tmp_path / "intro.wav").touch()
    assets = sfxmod.resolve_assets(tmp_path)
    assert assets == {}


def test_resolve_assets_missing_dir_returns_empty():
    missing = Path("/nonexistent/sfx/dir/that/does/not/exist")
    assert sfxmod.resolve_assets(missing) == {}


# ---------------------------------------------------------------------------
# plan_cues: missing asset → warning + skipped
# ---------------------------------------------------------------------------

def test_plan_cues_missing_pop_warns_and_skips(tmp_path):
    # only whoosh.wav present — pop missing
    (tmp_path / "whoosh.wav").touch()
    beats = [_beat("hook_title", 0.0), _beat("stat_punch", 2.0)]
    resolved, warnings = sfxmod.plan_cues(beats, [], directory=tmp_path)
    pop_cues = [c for c in resolved if c["kind"] == "pop"]
    assert pop_cues == []
    assert len(warnings) == 1
    assert "pop" in warnings[0]
    assert str(tmp_path) in warnings[0]


def test_plan_cues_resolved_path_is_string(tmp_path):
    (tmp_path / "whoosh.wav").touch()
    beats = [_beat("hook_title", 0.0)]
    resolved, warnings = sfxmod.plan_cues(beats, [], directory=tmp_path)
    assert len(resolved) == 1
    assert isinstance(resolved[0]["path"], str)
    assert resolved[0]["path"].endswith("whoosh.wav")


def test_plan_cues_one_warning_per_missing_kind(tmp_path):
    # whoosh present; pop and stroke missing — exactly 2 warnings
    (tmp_path / "whoosh.wav").touch()
    beats = [_beat("stat_punch", 2.0), _beat("quote_pull", 4.0)]
    captions = [
        _chunk(1.0, 1.5, accent_words=["bold"]),
        _chunk(3.0, 3.5, accent_words=["bolder"]),
    ]
    resolved, warnings = sfxmod.plan_cues(beats, captions, directory=tmp_path)
    assert len(warnings) == 2
    assert any("pop" in w for w in warnings)
    assert any("stroke" in w for w in warnings)


def test_plan_cues_one_warning_per_missing_kind_both_missing(tmp_path):
    # empty dir — pop and stroke both missing, exactly 2 warnings
    beats = [_beat("stat_punch", 2.0), _beat("quote_pull", 4.0)]
    captions = [
        _chunk(1.0, 1.5, accent_words=["bold"]),
        _chunk(3.0, 3.5, accent_words=["bolder"]),
    ]
    resolved, warnings = sfxmod.plan_cues(beats, captions, directory=tmp_path)
    assert resolved == []
    assert len(warnings) == 2
    # warning format: "sfx: no 'pop.*' file in ..." — kind name is before '.*'
    kinds_warned = {w.split("'")[1].replace(".*", "") for w in warnings}
    assert kinds_warned == {"pop", "stroke"}


# ---------------------------------------------------------------------------
# sfx_dir() env override
# ---------------------------------------------------------------------------

def test_sfx_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(sfxmod.SFX_DIR_ENV, str(tmp_path))
    assert sfxmod.sfx_dir() == tmp_path


def test_sfx_dir_default_without_env(monkeypatch):
    monkeypatch.delenv(sfxmod.SFX_DIR_ENV, raising=False)
    result = sfxmod.sfx_dir()
    assert "feinschnitt" in str(result)
    assert result == sfxmod.DEFAULT_SFX_DIR


# ---------------------------------------------------------------------------
# lint_score_config
# ---------------------------------------------------------------------------

def test_lint_score_config_valid_empty_dict():
    assert lint_score_config({}) == []


def test_lint_score_config_bad_enabled():
    errs = lint_score_config({"enabled": "yes"})
    assert len(errs) == 1
    assert "enabled" in errs[0]


def test_lint_score_config_bad_music():
    errs = lint_score_config({"music": 42})
    assert len(errs) == 1
    assert "music" in errs[0]


def test_lint_score_config_unknown_key():
    errs = lint_score_config({"musik": "track.mp3"})
    assert len(errs) == 1
    assert "musik" in errs[0]
    assert "allowed" in errs[0]


def test_lint_score_config_not_a_dict():
    errs = lint_score_config("enabled")
    assert len(errs) == 1
    assert "dict" in errs[0]


def test_lint_score_config_valid_full():
    errs = lint_score_config({"enabled": True, "music": "00-ambient.mp3"})
    assert errs == []
