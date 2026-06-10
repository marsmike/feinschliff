"""Clean-error contract for the feinklang CLI: rc==1, 'Error:' on stderr,
never a traceback. Mirrors feinschnitt/tests/test_cli_errors.py."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinklang import cli  # noqa: E402


def test_version(capsys):
    try:
        cli.main(["--version"])
    except SystemExit:
        pass
    assert "feinklang" in capsys.readouterr().out


def test_help_exits_cleanly(capsys):
    try:
        cli.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "tts" in out
    assert "voices" in out


def test_tts_subcommand_help(capsys):
    try:
        cli.main(["tts", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "--text" in out


def test_voices_subcommand_help(capsys):
    try:
        cli.main(["voices", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "--search" in out or "search" in out


def test_tts_missing_api_key(capsys, monkeypatch):
    """feinklang tts with no API key must exit 1 with a friendly Error: message.

    monkeypatch both the env var AND the load_home_env function so a developer's
    populated ~/.env cannot repopulate ELEVENLABS_API_KEY — keeps the path
    deterministic regardless of the local environment.
    """
    # Remove the key from the live environment (if present)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    # Prevent load_home_env() from re-loading it from ~/.env
    monkeypatch.setattr(cli, "load_home_env", lambda: None)

    try:
        rc = cli.main(["tts", "--text", "hello"])
    except SystemExit as exc:
        rc = exc.code

    err = capsys.readouterr().err
    assert rc == 1
    assert err.startswith("Error:")
    assert "ELEVENLABS_API_KEY" in err
    assert "Traceback" not in err
