"""Workdir + stage-cache helpers for the edit pipeline."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "feinschnitt" / "src"))
from feinschnitt.edit import workdir  # noqa: E402
from feinschnitt.edit import render as rendermod  # noqa: E402
from feinschnitt.edit import EditError  # noqa: E402


def test_workdir_is_deterministic_and_unique(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "CACHE_ROOT", tmp_path / "cache")
    a = tmp_path / "clip-a.mp4"
    b = tmp_path / "clip-a (copy).mp4"
    a.touch()
    b.touch()
    wd1 = workdir.workdir_for(a)
    wd2 = workdir.workdir_for(a)
    wd3 = workdir.workdir_for(b)
    assert wd1 == wd2 and wd1.is_dir()
    assert wd1 != wd3
    assert wd1.name.startswith("clip-a-")


def test_stage_key_changes_with_inputs():
    k1 = workdir.stage_key("a", 1)
    k2 = workdir.stage_key("a", 2)
    assert k1 != k2 and len(k1) == 40


def test_stage_fresh_roundtrip(tmp_path):
    marker = tmp_path / ".stage"
    key = workdir.stage_key("x")
    assert not workdir.stage_is_fresh(marker, key)
    workdir.mark_stage_done(marker, key)
    assert workdir.stage_is_fresh(marker, key)
    assert not workdir.stage_is_fresh(marker, workdir.stage_key("y"))


def test_engine_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("FEINSCHNITT_EDIT_ENGINE", str(tmp_path))
    assert rendermod.engine_dir() == tmp_path


def test_engine_dir_default_is_repo_edit_engine(monkeypatch):
    monkeypatch.delenv("FEINSCHNITT_EDIT_ENGINE", raising=False)
    assert rendermod.engine_dir().name == "edit-engine"


def test_render_fingerprint_changes_with_props(tmp_path, monkeypatch):
    monkeypatch.setenv("FEINSCHNITT_EDIT_ENGINE", str(tmp_path))
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.tsx").write_text("x")
    fp1 = rendermod.render_fingerprint(b'{"a":1}', "preview", 123)
    fp2 = rendermod.render_fingerprint(b'{"a":2}', "preview", 123)
    fp3 = rendermod.render_fingerprint(b'{"a":1}', "final", 123)
    assert len({fp1, fp2, fp3}) == 3


def test_stage_source_links_into_public(tmp_path):
    engine = tmp_path / "engine"
    engine.mkdir()
    src = tmp_path / "v.mp4"
    src.write_bytes(b"x")
    name = rendermod._stage_source(src, engine, "abc-preview.mp4")
    assert name == "abc-preview.mp4"
    assert (engine / "public" / name).read_bytes() == b"x"
    src2 = tmp_path / "v2.mp4"
    src2.write_bytes(b"y")
    rendermod._stage_source(src2, engine, "abc-preview.mp4")
    assert (engine / "public" / name).read_bytes() == b"y"


def test_ffprobe_meta_no_video_stream_is_clean_error(monkeypatch):
    class _R:
        stdout = json.dumps({"streams": [{"codec_type": "audio"}],
                             "format": {"duration": "5.0"}})

    monkeypatch.setattr(rendermod, "_run", lambda cmd, **kw: _R())
    with pytest.raises(EditError):
        rendermod.ffprobe_meta(Path("/x.m4a"))


def test_ffprobe_meta_reports_audio_presence(monkeypatch):
    class _R:
        stdout = json.dumps({"streams": [
            {"codec_type": "video", "width": 720, "height": 1280},
            {"codec_type": "audio"}],
            "format": {"duration": "5.0"}})

    monkeypatch.setattr(rendermod, "_run", lambda cmd, **kw: _R())
    meta = rendermod.ffprobe_meta(Path("/x.mp4"))
    assert meta == {"duration": 5.0, "width": 720, "height": 1280,
                    "has_audio": True}


def _engine(tmp_path):
    engine = tmp_path / "engine"
    engine.mkdir()
    return engine


def test_stage_assets_rewrites_copy_not_input(tmp_path):
    engine = _engine(tmp_path)
    (tmp_path / "shot.png").write_bytes(b"img")
    beats = [{"kind": "static", "image_path": "shot.png"},
             {"kind": "stat_punch", "value": "1", "caption": "c"}]
    staged, stats = rendermod._stage_assets(beats, tmp_path, engine, "vid")
    assert staged[0]["image_path"] == "vid-asset-0.png"
    assert beats[0]["image_path"] == "shot.png"  # input untouched (D2)
    assert staged[1] == beats[1]
    assert (engine / "public" / "vid-asset-0.png").read_bytes() == b"img"
    assert len(stats) == 1 and stats[0][0].endswith("shot.png")


def test_stage_assets_absolute_path_and_missing(tmp_path):
    engine = _engine(tmp_path)
    img = tmp_path / "abs.jpg"
    img.write_bytes(b"j")
    beats = [{"kind": "image_card", "image_path": str(img)}]
    staged, _ = rendermod._stage_assets(beats, tmp_path / "elsewhere", engine, "v")
    assert staged[0]["image_path"] == "v-asset-0.jpg"
    with pytest.raises(EditError):
        rendermod._stage_assets(
            [{"kind": "static", "image_path": "nope.png"}], tmp_path, engine, "v")


def test_fingerprint_changes_with_asset_mtime(tmp_path, monkeypatch):
    monkeypatch.setenv("FEINSCHNITT_EDIT_ENGINE", str(tmp_path))
    (tmp_path / "src").mkdir()
    fp1 = rendermod.render_fingerprint(b"{}", "preview", 1,
                                       asset_stats=[("/a.png", 100)])
    fp2 = rendermod.render_fingerprint(b"{}", "preview", 1,
                                       asset_stats=[("/a.png", 200)])
    fp3 = rendermod.render_fingerprint(b"{}", "preview", 1)
    assert len({fp1, fp2, fp3}) == 3
