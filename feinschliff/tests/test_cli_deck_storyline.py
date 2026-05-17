"""Integration test: feinschliff deck storyline emits out/storyline_report.md."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FEINSCHLIFF = REPO / "feinschliff"


def _write_plan(tmp_path: Path) -> Path:
    plan = {
        "slides": [
            {"layout_id": "title-orange", "slot_values": {"title": "Q3 in one slide"}},
            {"layout_id": "key-takeaways",
             "slot_values": {"title": "Three things to remember"}},
            {"layout_id": "end", "slot_values": {}},
        ],
    }
    p = tmp_path / "deck_plan.json"
    p.write_text(json.dumps(plan))
    return p


def test_storyline_writes_report_to_explicit_out(tmp_path: Path):
    plan = _write_plan(tmp_path)
    out = tmp_path / "storyline_report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "cli", "deck", "storyline",
            str(plan),
            "-o", str(out),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr
    body = out.read_text()
    assert "Verdict: pending" in body
    assert "Slides: 2" in body  # 2 non-empty titles
    assert "1. Q3 in one slide" in body
    assert "2. Three things to remember" in body
    assert "3. _(no title)_" in body


def test_storyline_brief_summary_flag(tmp_path: Path):
    plan = _write_plan(tmp_path)
    out = tmp_path / "storyline_report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "cli", "deck", "storyline",
            str(plan),
            "-o", str(out),
            "--brief-summary", "Q3 update — 2-pager for the exec team.",
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr
    body = out.read_text()
    assert "Q3 update" in body
    assert body.index("Q3 update") < body.index("1. Q3 in one slide")


def test_storyline_missing_plan(tmp_path: Path):
    out = tmp_path / "storyline_report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "cli", "deck", "storyline",
            str(tmp_path / "nope.json"),
            "-o", str(out),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode != 0
    assert "not found" in (result.stderr + result.stdout).lower()
