"""CLI integration tests for `feinschliff deck title-lint`."""
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
# subprocess-based CLI tests
# ---------------------------------------------------------------------------

def test_cli_clean_titles_exits_0(tmp_path: Path):
    plan = _write_plan(tmp_path, [
        "Revenue grew 18% in Q3",
        "Three forces drive this shift",
        "We must act now",
    ])
    out = tmp_path / "report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "title-lint",
            str(plan),
            "-o", str(out),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    assert "0 issue" in out.read_text() or "_No issues._" in out.read_text()


def test_cli_dirty_titles_exits_1(tmp_path: Path):
    plan = _write_plan(tmp_path, ["Market Overview"])  # no verb
    out = tmp_path / "report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "title-lint",
            str(plan),
            "-o", str(out),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 1, result.stderr
    assert out.exists()


def test_cli_flat_titles_exits_0(tmp_path: Path):
    titles_file = _write_flat_titles(tmp_path, [
        "Revenue grew 18% in Q3",
        "Three forces drive this shift",
    ])
    out = tmp_path / "report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "title-lint",
            str(titles_file),
            "-o", str(out),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr


def test_cli_missing_plan_exits_2(tmp_path: Path):
    out = tmp_path / "report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "title-lint",
            str(tmp_path / "no_such_plan.yaml"),
            "-o", str(out),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 2, result.stderr


def test_cli_json_flag_emits_array(tmp_path: Path):
    import json as _json

    plan = _write_plan(tmp_path, ["Market Overview"])  # will trigger title-no-verb
    out = tmp_path / "report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "title-lint",
            str(plan),
            "-o", str(out),
            "--json",
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    # exit code 1 because there are issues
    assert result.returncode == 1, result.stderr
    # stdout should be a JSON array
    data = _json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "rule" in data[0]


# ---------------------------------------------------------------------------
# Unit-level cmd_title_lint tests (monkeypatch)
# ---------------------------------------------------------------------------

def test_cmd_title_lint_clean_exits_0(tmp_path: Path, monkeypatch):
    import argparse
    import feinschliff.cli.deck as deck_cli

    plan = _write_plan(tmp_path, ["Revenue grew 18% in Q3"])
    out = tmp_path / "report.md"

    monkeypatch.setattr(deck_cli, "lint_titles", lambda titles: [])

    args = argparse.Namespace(
        plan=str(plan),
        output=str(out),
        emit_json=False,
    )
    exit_code = deck_cli.cmd_title_lint(args)
    assert exit_code == 0


def test_cmd_title_lint_issues_exits_1(tmp_path: Path, monkeypatch):
    import argparse
    import feinschliff.cli.deck as deck_cli
    from feinschliff_builder.verify.deck.title_lint import TitleLintIssue

    plan = _write_plan(tmp_path, ["Market Overview"])
    out = tmp_path / "report.md"

    fake_issues = [
        TitleLintIssue(slide=1, rule="title-no-verb", severity="warn", message="No verb found.")
    ]
    monkeypatch.setattr(deck_cli, "lint_titles", lambda titles: fake_issues)

    args = argparse.Namespace(
        plan=str(plan),
        output=str(out),
        emit_json=False,
    )
    exit_code = deck_cli.cmd_title_lint(args)
    assert exit_code == 1
    assert out.exists()
    body = out.read_text()
    assert "title-no-verb" in body
