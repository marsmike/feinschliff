"""M4 audio-score tests — Task 1: SFX cue derivation + lint_score_config.

Task 2 tests (score.py) are appended below."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit import sfx as sfxmod  # noqa: E402
from feinschnitt.edit import score as scoremod  # noqa: E402
from feinschnitt.edit import EditError  # noqa: E402
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


# ===========================================================================
# Task 2: score.py tests
# ===========================================================================

# ---------------------------------------------------------------------------
# measure_lufs: monkeypatched _run
# ---------------------------------------------------------------------------

_LOUDNORM_STDERR = """\
[Parsed_loudnorm_0 @ 0x...] Input Integrated:    -23.4 LUFS
{
    "input_i" : "-23.4",
    "input_tp" : "-1.0",
    "input_lra" : "4.5",
    "input_thresh" : "-33.8",
    "output_i" : "-26.0",
    "output_tp" : "-3.0",
    "output_lra" : "3.0",
    "output_thresh" : "-36.6",
    "normalization_type" : "dynamic",
    "target_offset" : "-2.6"
}
"""


def test_measure_lufs_parses_json(monkeypatch, tmp_path):
    fake_audio = tmp_path / "track.wav"
    fake_audio.write_bytes(b"")

    def fake_run(cmd, **kw):
        cp = subprocess.CompletedProcess(cmd, 0, stdout="", stderr=_LOUDNORM_STDERR)
        return cp

    monkeypatch.setattr(scoremod, "_run", fake_run)
    result = scoremod.measure_lufs(fake_audio)
    assert result == pytest.approx(-23.4)


def test_measure_lufs_garbage_stderr_raises(monkeypatch, tmp_path):
    fake_audio = tmp_path / "track.wav"
    fake_audio.write_bytes(b"")

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="no json here")

    monkeypatch.setattr(scoremod, "_run", fake_run)
    with pytest.raises(EditError, match="loudness analysis failed"):
        scoremod.measure_lufs(fake_audio)


def test_measure_lufs_json_without_input_i_raises(monkeypatch, tmp_path):
    fake_audio = tmp_path / "track.wav"
    fake_audio.write_bytes(b"")
    bad_stderr = '{"output_i": "-26.0"}'  # no input_i

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr=bad_stderr)

    monkeypatch.setattr(scoremod, "_run", fake_run)
    with pytest.raises(EditError, match="loudness analysis failed"):
        scoremod.measure_lufs(fake_audio)


# ---------------------------------------------------------------------------
# find_climax
# ---------------------------------------------------------------------------

def test_find_climax_quote_pull_wins_over_later_takeover():
    beats = [
        _beat("stat_punch", 10.0),      # takeover at 10s
        _beat("quote_pull", 6.0),       # quote at 6s — wins
        _beat("quote_pull", 8.0),       # second quote — ignored (not earliest)
    ]
    assert scoremod.find_climax(beats) == pytest.approx(6.0)


def test_find_climax_earliest_quote_among_two():
    beats = [
        _beat("quote_pull", 12.0),
        _beat("quote_pull", 5.0),
    ]
    assert scoremod.find_climax(beats) == pytest.approx(5.0)


def test_find_climax_no_quote_returns_last_takeover():
    beats = [
        _beat("stat_punch", 3.0),
        _beat("static", 8.0),
        _beat("vertical_timeline", 5.0),
    ]
    assert scoremod.find_climax(beats) == pytest.approx(8.0)


def test_find_climax_overlays_only_returns_none():
    beats = [
        _beat("hook_title", 0.0),
        _beat("word_pop", 2.0),
        _beat("image_card", 4.0),
    ]
    assert scoremod.find_climax(beats) is None


def test_find_climax_bool_start_ignored():
    beats = [
        {"kind": "quote_pull", "start_sec": True, "end_sec": 3.0, "reason": "x"},
        _beat("stat_punch", 7.0),
    ]
    # quote_pull with bool start_sec is rejected; fallback to last takeover
    assert scoremod.find_climax(beats) == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# _swell_value sample points
# ---------------------------------------------------------------------------

def test_swell_value_standard_climax():
    climax = 20.0
    duration = 30.0
    s = scoremod.SWELL_PEAK
    # Before rise start (r0 = 14.0) — flat at 1.0
    assert scoremod._swell_value(10.0, climax, duration) == pytest.approx(1.0)
    # At rise start — 1.0
    assert scoremod._swell_value(14.0, climax, duration) == pytest.approx(1.0)
    # At climax — SWELL_PEAK
    assert scoremod._swell_value(20.0, climax, duration) == pytest.approx(s)
    # Hold (climax + 1) — still SWELL_PEAK
    assert scoremod._swell_value(21.0, climax, duration) == pytest.approx(s)
    # Hold end (climax + 2 = 22.0) — still SWELL_PEAK
    assert scoremod._swell_value(22.0, climax, duration) == pytest.approx(s)
    # Halfway through fall (climax + 2 + 1.5 = 23.5) → midway between s and 1.0
    assert scoremod._swell_value(23.5, climax, duration) == pytest.approx((s + 1.0) / 2, rel=1e-4)
    # After fall end (climax + 5 = 25.0) — back to 1.0
    assert scoremod._swell_value(25.0, climax, duration) == pytest.approx(1.0)
    # Well after fall
    assert scoremod._swell_value(29.0, climax, duration) == pytest.approx(1.0)


def test_swell_value_climax_near_start_r0_clamped():
    # climax = 2.0 → r0 = max(0, 2-6) = 0; rise starts from t=0
    climax = 2.0
    duration = 30.0
    s = scoremod.SWELL_PEAK
    assert scoremod._swell_value(0.0, climax, duration) == pytest.approx(1.0)
    assert scoremod._swell_value(2.0, climax, duration) == pytest.approx(s)
    assert scoremod._swell_value(4.0, climax, duration) == pytest.approx(s)  # hold until h1=4.0
    # f1 = min(30, 4+3) = 7.0 — at t=5.5 we are halfway through the fall
    half_fall = (s + 1.0) / 2  # midpoint of fall
    assert scoremod._swell_value(5.5, climax, duration) == pytest.approx(half_fall, rel=1e-4)
    # after fall end (t=7) → back to 1.0
    assert scoremod._swell_value(7.0, climax, duration) == pytest.approx(1.0)


def test_swell_value_climax_near_duration():
    # climax close to duration → hold and fall clamp
    climax = 29.0
    duration = 30.0
    s = scoremod.SWELL_PEAK
    # h1 = min(30, 31) = 30; f1 = min(30, 33) = 30 → fall has zero width
    assert scoremod._swell_value(29.5, climax, duration) == pytest.approx(s)
    assert scoremod._swell_value(30.0, climax, duration) == pytest.approx(s)


# ---------------------------------------------------------------------------
# swell_expr: structural checks
# ---------------------------------------------------------------------------

def test_swell_expr_starts_with_if_lt_t():
    expr = scoremod.swell_expr(20.0, 60.0)
    assert expr.startswith("if(lt(t,")


def test_swell_expr_parens_balanced():
    expr = scoremod.swell_expr(20.0, 60.0)
    assert expr.count("(") == expr.count(")")


def test_swell_expr_contains_climax_value():
    expr = scoremod.swell_expr(20.0, 60.0)
    # 20.0 formatted as "20" or "20.0" — just check the number is present
    assert "20" in expr


def test_swell_expr_contains_swell_peak():
    expr = scoremod.swell_expr(20.0, 60.0)
    assert str(scoremod.SWELL_PEAK) in expr or "1.6" in expr


# ---------------------------------------------------------------------------
# pick_track
# ---------------------------------------------------------------------------

def test_pick_track_named_config_found(monkeypatch, tmp_path):
    (tmp_path / "my-track.mp3").touch()
    monkeypatch.setenv(scoremod.MUSIC_DIR_ENV, str(tmp_path))
    path, warnings = scoremod.pick_track({"music": "my-track.mp3"})
    assert path is not None
    assert path.name == "my-track.mp3"
    assert warnings == []


def test_pick_track_named_config_missing_warns(monkeypatch, tmp_path):
    monkeypatch.setenv(scoremod.MUSIC_DIR_ENV, str(tmp_path))
    path, warnings = scoremod.pick_track({"music": "missing.mp3"})
    assert path is None
    assert len(warnings) == 1
    assert "missing.mp3" in warnings[0]


def test_pick_track_signature_default_alphabetically_first(monkeypatch, tmp_path):
    (tmp_path / "00-ambient.mp3").touch()
    (tmp_path / "01-extra.wav").touch()
    (tmp_path / "cover.jpg").touch()  # non-audio — must be skipped
    monkeypatch.setenv(scoremod.MUSIC_DIR_ENV, str(tmp_path))
    path, warnings = scoremod.pick_track(None)
    assert path is not None
    assert path.name == "00-ambient.mp3"
    assert warnings == []


def test_pick_track_non_audio_files_skipped(monkeypatch, tmp_path):
    (tmp_path / "readme.txt").touch()
    (tmp_path / "cover.jpg").touch()
    (tmp_path / "track.ogg").touch()
    monkeypatch.setenv(scoremod.MUSIC_DIR_ENV, str(tmp_path))
    path, warnings = scoremod.pick_track(None)
    assert path is not None
    assert path.name == "track.ogg"


def test_pick_track_empty_dir_warns(monkeypatch, tmp_path):
    monkeypatch.setenv(scoremod.MUSIC_DIR_ENV, str(tmp_path))
    path, warnings = scoremod.pick_track(None)
    assert path is None
    assert len(warnings) == 1
    assert "empty" in warnings[0]


def test_pick_track_missing_dir_warns(monkeypatch, tmp_path):
    missing = tmp_path / "nonexistent"
    monkeypatch.setenv(scoremod.MUSIC_DIR_ENV, str(missing))
    path, warnings = scoremod.pick_track(None)
    assert path is None
    assert len(warnings) == 1
    assert "not found" in warnings[0]


# ---------------------------------------------------------------------------
# build_filtergraph: exact string assertions
# ---------------------------------------------------------------------------

def test_build_filtergraph_bed_two_cues():
    fg = scoremod.build_filtergraph(
        bed=True,
        n_cues=2,
        bed_gain_db=-3.5,
        swell=None,
        cue_delays_ms=[0, 5000],
        duration=60.0,
    )
    # asplit voice/sc
    assert "[0:a]asplit=2[voice][sc];" in fg
    # bed gain applied with 2 decimal places
    assert "volume=-3.50dB" in fg
    # trim to duration
    assert "atrim=0:60" in fg
    # sidechain — must have [bedlvl][sc] before sidechaincompress
    assert "[bedlvl][sc]sidechaincompress=" in fg
    # SFX cues from input index 2 and 3
    assert "[2:a]volume=-18dB,adelay=0|0[fx0];" in fg
    assert "[3:a]volume=-18dB,adelay=5000|5000[fx1];" in fg
    # amix with voice+duck+2 cues = 4 inputs
    assert "amix=inputs=4" in fg
    assert "normalize=0" in fg
    assert "[mix]" in fg


def test_build_filtergraph_no_bed_one_cue():
    fg = scoremod.build_filtergraph(
        bed=False,
        n_cues=1,
        bed_gain_db=0.0,
        swell=None,
        cue_delays_ms=[2000],
        duration=30.0,
    )
    # No asplit
    assert "asplit" not in fg
    assert "sidechaincompress" not in fg
    # cue at input index 1
    assert "[1:a]volume=-18dB,adelay=2000|2000[fx0];" in fg
    # amix with voice + 1 cue = 2 inputs
    assert "[0:a][fx0]amix=inputs=2" in fg
    assert "normalize=0" in fg


def test_build_filtergraph_bed_zero_cues():
    fg = scoremod.build_filtergraph(
        bed=True,
        n_cues=0,
        bed_gain_db=-5.0,
        swell=None,
        cue_delays_ms=[],
        duration=45.0,
    )
    # amix inputs=2 (voice + duck)
    assert "amix=inputs=2" in fg
    assert "normalize=0" in fg
    # no fx labels
    assert "[fx0]" not in fg


def test_build_filtergraph_normalize_zero_always_present():
    for bed in (True, False):
        fg = scoremod.build_filtergraph(
            bed=bed, n_cues=0, bed_gain_db=0.0, swell=None,
            cue_delays_ms=[], duration=30.0,
        )
        assert "normalize=0" in fg


def test_build_filtergraph_sidechain_order():
    fg = scoremod.build_filtergraph(
        bed=True, n_cues=0, bed_gain_db=0.0, swell=None,
        cue_delays_ms=[], duration=30.0,
    )
    # [bedlvl] must appear BEFORE [sc] in the sidechain compress call
    pos_bedlvl = fg.index("[bedlvl]")
    pos_sc = fg.index("[sc]sidechaincompress")
    assert pos_bedlvl < pos_sc


def test_build_filtergraph_swell_included_when_provided():
    swell = "if(lt(t,14),1,1.6)"
    fg = scoremod.build_filtergraph(
        bed=True, n_cues=0, bed_gain_db=0.0,
        swell=swell, cue_delays_ms=[], duration=30.0,
    )
    assert swell in fg
    assert "volume=eval=frame" in fg


# ---------------------------------------------------------------------------
# score() decision path: no track + no cues → (False, warnings), _run not called
# ---------------------------------------------------------------------------

def test_score_skips_when_no_track_and_no_cues(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"")
    out = tmp_path / "out.mp4"

    # pick_track → (None, [warning])
    monkeypatch.setattr(scoremod, "pick_track", lambda config: (None, ["no track"]))
    # plan_cues → ([], [])
    import feinschnitt.edit.sfx as _sfx
    monkeypatch.setattr(_sfx, "plan_cues", lambda beats, captions: ([], []))

    # _run must NOT be called
    def _run_must_not_be_called(cmd, **kw):
        raise AssertionError("_run should not have been called")

    monkeypatch.setattr(scoremod, "_run", _run_must_not_be_called)

    scored, warnings = scoremod.score(
        video, out, beats=[], captions=[], config=None, duration=30.0
    )
    assert scored is False
    assert "no track" in warnings
