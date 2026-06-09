"""Clean-error contract for the feinschnitt CLI: rc==1, 'Error:' on stderr,
never a traceback. Mirrors feinbild/tests/test_cli_errors.py."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt import cli  # noqa: E402

RECIPE = (
    Path(__file__).resolve().parents[1]
    / "skills" / "cli-recorder" / "recipes" / "claude-commands.recipe.toml"
)
RECORDER_HOME = Path(__file__).resolve().parents[1] / "skills" / "cli-recorder"


def test_version(capsys):
    try:
        cli.main(["--version"])
    except SystemExit:
        pass
    assert "feinschnitt" in capsys.readouterr().out


def test_record_dry_run(capsys, monkeypatch):
    monkeypatch.setenv("FEINSCHNITT_RECORDER_HOME", str(RECORDER_HOME))
    rc = cli.main(["record", str(RECIPE), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[dry-run] would execute these steps" in out


def test_record_missing_recipe(capsys):
    rc = cli.main(["record", "/nope/missing.recipe.toml", "--dry-run"])
    err = capsys.readouterr().err
    assert rc == 1
    assert err.startswith("Error:")
    assert "Traceback" not in err


def test_analyze_missing_key(capsys, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    rc = cli.main(["analyze", "/nope/video.mp4"])
    err = capsys.readouterr().err
    assert rc == 1
    assert err.startswith("Error:")
    assert "GEMINI_API_KEY" in err
    assert "Traceback" not in err
