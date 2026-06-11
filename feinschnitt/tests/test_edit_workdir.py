"""Workdir + stage-cache helpers for the edit pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit import workdir  # noqa: E402


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
