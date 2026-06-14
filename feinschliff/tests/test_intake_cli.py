"""CLI smoke tests for `feinschliff deck intake-validate` / `intake-skeleton`."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "feinschliff.cli.main", "deck", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_intake_validate_clean():
    brief = {
        "schema_version": 1,
        "goal": "decision",
        "audience": "exec",
        "deck_type": "pitch",
    }
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
        yaml.safe_dump(brief, f)
        path = Path(f.name)
    try:
        result = _run("intake-validate", str(path))
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout
    finally:
        path.unlink(missing_ok=True)


def test_intake_validate_invalid_returns_1():
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
        yaml.safe_dump({"schema_version": 1, "goal": "bad"}, f)
        path = Path(f.name)
    try:
        result = _run("intake-validate", str(path))
        assert result.returncode == 1
        assert "goal" in result.stderr or "required" in result.stderr
    finally:
        path.unlink(missing_ok=True)


def test_intake_validate_missing_returns_2():
    result = _run("intake-validate", "/nonexistent/deck_brief.yaml")
    assert result.returncode == 2


def test_intake_skeleton_empty_yields_required_unset():
    result = _run("intake-skeleton")
    assert result.returncode == 0, result.stderr
    parsed = yaml.safe_load(result.stdout)
    assert parsed["schema_version"] == 1
    assert parsed["goal"] == "<<unset>>"
    assert parsed["audience"] == "<<unset>>"
    assert parsed["deck_type"] == "<<unset>>"


def test_intake_skeleton_with_brief_seeds_fields():
    result = _run("intake-skeleton", "--brief", "Series A pitch to acme investors")
    assert result.returncode == 0, result.stderr
    parsed = yaml.safe_load(result.stdout)
    assert parsed["deck_type"] == "pitch"
    assert parsed["goal"] == "buy-in"
