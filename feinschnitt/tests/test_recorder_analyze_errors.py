"""Regression tests for recorder/analyze error paths: v2-cast rejection,
banner-abort exiting nonzero, and analyze's bounded poll loop + cleanup of
failed Gemini uploads. Companion to test_cli_errors.py."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt import analyze, cli, recorder  # noqa: E402

RECIPE = (
    Path(__file__).resolve().parents[1]
    / "skills" / "cli-recorder" / "recipes" / "claude-commands.recipe.toml"
)
RECORDER_HOME = Path(__file__).resolve().parents[1] / "skills" / "cli-recorder"


# ── recorder: cast versions + abort exit code ────────────────────────────────

def _write_cast(path: Path, version: int, events: list[list]) -> None:
    lines = [json.dumps({"version": version, "width": 80, "height": 24})]
    lines += [json.dumps(e) for e in events]
    path.write_text("\n".join(lines) + "\n")


def test_postprocess_rejects_v2_cast(tmp_path):
    src = tmp_path / "v2.cast"
    _write_cast(src, 2, [[0.5, "o", "hello"], [3.0, "o", "world"]])
    recipe = recorder.Recipe(title="t", command="bash")
    with pytest.raises(recorder.RecorderError, match=r"asciinema >= 3\.0"):
        recorder.postprocess_cast(src, tmp_path / "out.cast", recipe)
    assert not (tmp_path / "out.cast").exists()


def test_postprocess_compresses_v3_deltas(tmp_path):
    src = tmp_path / "v3.cast"
    _write_cast(src, 3, [[0.2, "o", "a"], [4.4, "o", "b"]])
    recipe = recorder.Recipe(title="t", command="bash")  # threshold 0.4, speedup 4
    saved, final = recorder.postprocess_cast(src, tmp_path / "out.cast", recipe)
    assert saved == pytest.approx(3.0)
    assert final == pytest.approx(1.6)


def test_record_banner_abort_exits_nonzero(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("FEINSCHNITT_RECORDER_HOME", str(RECORDER_HOME))
    monkeypatch.setattr(recorder, "spawn_session",
                        lambda recipe, session, cast_path: tmp_path / "wrapper.sh")
    monkeypatch.setattr(recorder, "wait_for_banner", lambda *a: False)
    monkeypatch.setattr(recorder, "session_exists", lambda s: False)
    monkeypatch.setattr(recorder, "kill_session", lambda s: None)
    rc = cli.main(["record", str(RECIPE), "--out-dir", str(tmp_path), "--no-render"])
    err = capsys.readouterr().err
    assert rc == 1
    assert err.startswith("Error:")
    assert "banner" in err
    assert "Traceback" not in err


# ── analyze: bounded poll + failed-upload cleanup ────────────────────────────

class _FakeState:
    def __init__(self, name):
        self.name = name


class _FakeFile:
    def __init__(self, state):
        self.name = "files/abc"
        self.uri = "https://fake/files/abc"
        self.state = _FakeState(state)


class _FakeGenai:
    def __init__(self, states):
        self._states = list(states)
        self.deleted = []

    def upload_file(self, path):
        return _FakeFile(self._states.pop(0))

    def get_file(self, name):
        return _FakeFile(self._states.pop(0) if self._states else "PROCESSING")

    def delete_file(self, name):
        self.deleted.append(name)


def test_analyze_poll_timeout_clean_error(monkeypatch):
    fake = _FakeGenai(["PROCESSING"])
    monkeypatch.setattr(analyze, "genai", fake)
    monkeypatch.setattr(analyze.time, "sleep", lambda s: None)
    with pytest.raises(analyze.AnalyzeError, match="timed out"):
        analyze.upload_and_wait("video.mp4", "gemini-2.0-flash", timeout_s=0.0)
    assert fake.deleted == ["files/abc"]


def test_analyze_failed_upload_cleanup(monkeypatch):
    fake = _FakeGenai(["PROCESSING", "FAILED"])
    monkeypatch.setattr(analyze, "genai", fake)
    monkeypatch.setattr(analyze.time, "sleep", lambda s: None)
    with pytest.raises(analyze.AnalyzeError, match="failed to process"):
        analyze.upload_and_wait("video.mp4", "gemini-2.0-flash", timeout_s=60.0)
    assert fake.deleted == ["files/abc"]


def test_analyze_provider_error_clean(monkeypatch):
    class _BoomModel:
        def __init__(self, *a, **k):
            pass

        def generate_content(self, *a, **k):
            raise RuntimeError("503 service unavailable")

    fake = _FakeGenai([])
    fake.GenerativeModel = _BoomModel
    monkeypatch.setattr(analyze, "genai", fake)
    with pytest.raises(analyze.AnalyzeError, match="Gemini API: 503"):
        analyze.analyze(object(), "gemini-2.0-flash")
