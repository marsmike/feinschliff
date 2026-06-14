"""CLI integration tests for `feinschliff deck ghost-deck`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[2]
FEINSCHLIFF = REPO / "feinschliff"


def _write_plan(tmp_path: Path, titles: list[str]) -> Path:
    slides = [{"layout": "layouts/title-body.slide.dsl", "content": {"title": t}} for t in titles]
    p = tmp_path / "plan.yaml"
    p.write_text(yaml.dump({"slides": slides}))
    return p


def _write_flat_titles(tmp_path: Path, titles: list[str]) -> Path:
    p = tmp_path / "titles.yaml"
    p.write_text(yaml.dump(titles))
    return p


# ---------------------------------------------------------------------------
# Offline mode tests
# ---------------------------------------------------------------------------

def test_cli_offline_exits_0(tmp_path: Path):
    """Offline ghost-deck on a plan.yaml exits 0 (pass)."""
    plan = _write_plan(tmp_path, ["Hook", "Body", "Ask"])
    out = tmp_path / "ghost_deck_report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "ghost-deck",
            str(plan),
            "-o", str(out),
            "--offline",
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    body = out.read_text()
    assert "pass" in body


def test_cli_offline_flat_titles_exits_0(tmp_path: Path):
    """Offline ghost-deck on a flat YAML list exits 0."""
    titles_file = _write_flat_titles(tmp_path, ["Hook", "Body", "Ask"])
    out = tmp_path / "report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "ghost-deck",
            str(titles_file),
            "-o", str(out),
            "--offline",
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()


def test_cli_missing_plan_exits_2(tmp_path: Path):
    out = tmp_path / "report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "ghost-deck",
            str(tmp_path / "no_such_plan.yaml"),
            "-o", str(out),
            "--offline",
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 2, result.stderr


def test_cli_fail_verdict_exits_1(tmp_path: Path, monkeypatch):
    """When judge_ghost_deck returns verdict=fail, CLI exits 1."""
    import argparse
    import feinschliff.cli.deck as deck_cli
    from feinschliff.verify.deck.ghost_deck import GhostDeckResult

    plan = _write_plan(tmp_path, ["Hook", "Body"])
    out = tmp_path / "report.md"

    def fake_judge(*a, **kw):
        return GhostDeckResult(
            verdict="fail",
            issues=[{"slide": 1, "issue": "topic label", "suggested": "add a verb"}],
            titles=["Hook", "Body"],
        )

    monkeypatch.setattr(deck_cli, "judge_ghost_deck", fake_judge)

    args = argparse.Namespace(
        plan=str(plan),
        output=str(out),
        offline=True,
        model="claude-haiku-4-5-20251001",
    )
    exit_code = deck_cli.cmd_ghost_deck(args)
    assert exit_code == 1


def test_cli_warn_verdict_exits_0(tmp_path: Path, monkeypatch):
    """When judge_ghost_deck returns verdict=warn, CLI exits 0."""
    import argparse
    import feinschliff.cli.deck as deck_cli
    from feinschliff.verify.deck.ghost_deck import GhostDeckResult

    plan = _write_plan(tmp_path, ["Hook", "Body"])
    out = tmp_path / "report.md"

    def fake_judge(*a, **kw):
        return GhostDeckResult(
            verdict="warn",
            issues=[{"slide": 2, "issue": "minor gap", "suggested": "bridge"}],
            titles=["Hook", "Body"],
        )

    monkeypatch.setattr(deck_cli, "judge_ghost_deck", fake_judge)

    args = argparse.Namespace(
        plan=str(plan),
        output=str(out),
        offline=True,
        model="claude-haiku-4-5-20251001",
    )
    exit_code = deck_cli.cmd_ghost_deck(args)
    assert exit_code == 0
