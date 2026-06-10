from __future__ import annotations

import json
from pathlib import Path

from feinschliff_builder.eval.grader import grade

BRAND_DIR = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"

_FIVE_FOUR = {
    "type": "excalidraw", "version": 2, "appState": {},
    "elements": (
        [{"id": f"r{i}", "type": "rectangle", "x": i * 100, "y": 0, "width": 80, "height": 60}
         for i in range(5)]
        + [{"id": f"a{i}", "type": "arrow", "x": 0, "y": 0, "width": 10, "height": 0,
            "points": [[0, 0], [10, 0]]} for i in range(4)]
    ),
}


def _suite(tmp_path: Path) -> Path:
    evals_dir = tmp_path / "skill" / "evals"
    evals_dir.mkdir(parents=True)
    suite = {
        "skill": "excalidraw",
        "version": 1,
        "tests": [
            {"name": "five-box-flow", "prompt": "p",
             "checks": ["rectangles==5", "arrows==4"]},
        ],
    }
    (evals_dir / "evals.json").write_text(json.dumps(suite))
    return evals_dir / "evals.json"


def test_grade_all_pass(tmp_path):
    evals_path = _suite(tmp_path)
    results = tmp_path / "results"
    results.mkdir()
    (results / "five-box-flow.excalidraw").write_text(json.dumps(_FIVE_FOUR))

    report = grade(evals_path, results, BRAND_DIR)
    assert report["skill"] == "excalidraw"
    assert report["passed"] == 2 and report["total"] == 2
    assert report["score"] == 1.0
    assert report["tests"][0]["exists"] is True


def test_grade_missing_artifact_fails_all(tmp_path):
    evals_path = _suite(tmp_path)
    results = tmp_path / "results"
    results.mkdir()  # no artifact written

    report = grade(evals_path, results, BRAND_DIR)
    assert report["passed"] == 0 and report["total"] == 2
    assert report["score"] == 0.0
    assert report["tests"][0]["exists"] is False


def test_cli_eval_exit_codes(tmp_path):
    from feinschliff_builder.cli import main as cli_main

    # Build a skill dir with evals.json + a matching results dir.
    evals_path = _suite(tmp_path)
    skill_dir = evals_path.parent.parent  # <tmp>/skill
    results = tmp_path / "results"
    results.mkdir()
    (results / "five-box-flow.excalidraw").write_text(json.dumps(_FIVE_FOUR))

    rc = cli_main.main(["eval", str(skill_dir), "--results-dir", str(results)])
    assert rc == 0
    assert (results / "grades.json").is_file()

    # Remove the artifact -> checks fail -> nonzero exit.
    (results / "five-box-flow.excalidraw").unlink()
    rc = cli_main.main(["eval", str(skill_dir), "--results-dir", str(results)])
    assert rc == 1


def test_cli_eval_missing_evals(tmp_path):
    from feinschliff_builder.cli import main as cli_main

    rc = cli_main.main(["eval", str(tmp_path), "--results-dir", str(tmp_path)])
    assert rc == 2
