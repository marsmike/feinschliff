"""CLI smoke tests for `feinschliff deck commitment-validate`."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "feinschliff.cli.main", "deck", *args],
        capture_output=True,
        text=True,
    )


def _write(commitment: dict) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w")
    yaml.safe_dump(commitment, f)
    f.close()
    return Path(f.name)


def test_validate_clean():
    path = _write({
        "deck_type": "pitch",
        "thesis": "The market is shifting from on-prem to cloud.",
        "key_moves": [
            "Show the shift.",
            "Name the stakes.",
            "Position the promised land.",
            "Demo our features as the magic path.",
            "Prove with three customers.",
            "Ask for the next call.",
        ],
    })
    try:
        result = _run("commitment-validate", str(path))
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout
    finally:
        path.unlink(missing_ok=True)


def test_validate_missing_thesis_fails():
    path = _write({"deck_type": "pitch", "key_moves": ["a", "b"]})
    try:
        result = _run("commitment-validate", str(path))
        assert result.returncode == 1
    finally:
        path.unlink(missing_ok=True)


def test_validate_check_arc_alignment_pass():
    path = _write({
        "deck_type": "pitch",
        "thesis": "Cloud is the new normal.",
        "key_moves": [
            "Show the shift.",
            "Stakes: who pays.",
            "Promised land: cloud future.",
            "Obstacles in the path.",
            "Features as magic.",
            "Proof from customers.",
            "Ask for a pilot.",
        ],
    })
    try:
        result = _run("commitment-validate", "--check-arc", str(path))
        assert result.returncode == 0, result.stderr
    finally:
        path.unlink(missing_ok=True)


def test_validate_check_arc_missing_required_act():
    path = _write({
        "deck_type": "pitch",
        "thesis": "Cloud is the new normal.",
        "key_moves": ["Show the shift.", "Promised land of cloud."],
    })
    try:
        result = _run("commitment-validate", "--check-arc", str(path))
        assert result.returncode == 1
        assert "ask" in result.stderr or "stakes" in result.stderr
    finally:
        path.unlink(missing_ok=True)


def test_validate_missing_file_returns_2():
    result = _run("commitment-validate", "/nonexistent/commitment.yaml")
    assert result.returncode == 2
