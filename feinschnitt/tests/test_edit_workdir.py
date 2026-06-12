"""Workdir + stage-cache helpers for the edit pipeline."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
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
