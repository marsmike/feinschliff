"""Clean-error contract for `feinschnitt edit`: rc==1, 'Error:' on stderr,
never a traceback."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "feinschnitt" / "src"))
from feinschnitt import cli  # noqa: E402


def test_edit_transcribe_missing_video(capsys):
    rc = cli.main(["edit", "transcribe", "/nope/clip.mp4"])
    err = capsys.readouterr().err
    assert rc == 1
    assert err.startswith("Error:")
    assert "Traceback" not in err


def test_edit_render_missing_plan(capsys, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    rc = cli.main(["edit", "render", str(video), str(tmp_path / "nope.json")])
    err = capsys.readouterr().err
    assert rc == 1
    assert err.startswith("Error:")
    assert "Traceback" not in err


def test_edit_render_rejects_bad_quality(capsys, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    plan = tmp_path / "edit_plan.json"
    plan.write_text('{"beats": []}')
    rc = cli.main(["edit", "render", str(video), str(plan), "--quality", "ultra"])
    err = capsys.readouterr().err
    assert rc == 1 and err.startswith("Error:")
