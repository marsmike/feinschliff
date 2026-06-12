"""Transcribe stage: faster-whisper wrapper, corrections, stage cache."""
import json
import os
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit import EditError, transcribe, workdir  # noqa: E402


class _Word:
    def __init__(self, word, start, end):
        self.word, self.start, self.end = word, start, end


class _Seg:
    def __init__(self, words):
        self.words = words


class _Info:
    duration = 2.0


class _FakeModel:
    calls = 0

    def __init__(self, *a, **k):
        pass

    def transcribe(self, path, word_timestamps=True):
        _FakeModel.calls += 1
        return iter([_Seg([_Word(" cloud", 0.1, 0.5), _Word(" code", 0.6, 1.0)])]), _Info()


@pytest.fixture()
def fake_whisper(monkeypatch, tmp_path):
    mod = types.ModuleType("faster_whisper")
    mod.WhisperModel = _FakeModel
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    monkeypatch.setattr(workdir, "CACHE_ROOT", tmp_path / "cache")
    _FakeModel.calls = 0
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    return video


def test_transcribe_writes_corrected_words(fake_whisper):
    out = transcribe.run(fake_whisper)
    data = json.loads(out.read_text())
    assert data["duration"] == 2.0
    assert [w["w"] for w in data["words"]] == ["claude", "code"]


def test_transcribe_is_cached_on_source_mtime(fake_whisper):
    transcribe.run(fake_whisper)
    transcribe.run(fake_whisper)
    assert _FakeModel.calls == 1


def test_missing_video_is_clean_error(tmp_path, monkeypatch):
    monkeypatch.setattr(workdir, "CACHE_ROOT", tmp_path / "cache")
    with pytest.raises(EditError):
        transcribe.run(tmp_path / "nope.mp4")


def test_missing_dependency_is_clean_error(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)  # forces ImportError
    monkeypatch.setattr(workdir, "CACHE_ROOT", tmp_path / "cache")
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    with pytest.raises(EditError, match="feinschnitt\\[edit\\]"):
        transcribe.run(video)


def test_cache_invalidates_on_mtime_change(fake_whisper):
    transcribe.run(fake_whisper)
    os.utime(fake_whisper, (1, 1))
    transcribe.run(fake_whisper)
    assert _FakeModel.calls == 2
