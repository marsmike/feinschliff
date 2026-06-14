"""End-to-end smoke test for the deck pipeline tooling.

Gated by the RUN_E2E_DECK_TEST environment variable and the ``orchestration``
pytest mark so CI does not run it on every PR.  No network calls are made:
ghost-deck uses ``--offline`` and all other operations are purely local.

    RUN_E2E_DECK_TEST=1 pytest -m orchestration -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.orchestration


@pytest.mark.skipif(
    not os.environ.get("RUN_E2E_DECK_TEST"),
    reason="Set RUN_E2E_DECK_TEST=1 to run; takes ~5 min and uses no network but is slow",
)
def test_deck_pipeline_artifacts(tmp_path: Path) -> None:
    """Verify the pipeline tooling produces the expected per-step artifacts.

    This is NOT a Claude-skill smoke run; it exercises the Python CLI layer
    directly and is the strongest unit-level proxy for the orchestration
    contract.  Catches the class of regressions where the underlying tooling
    stops producing the expected files even though the skill prose is intact.
    """
    # ------------------------------------------------------------------
    # 1. Write deck_brief.yaml using the public intake API
    # ------------------------------------------------------------------
    from feinschliff.intake import empty_brief, save_brief, validate_brief

    brief = empty_brief()
    # Fill all required fields so validate_brief passes
    brief.update(
        {
            "goal": "decision",
            "audience": "exec",
            "audience_prior": "some",
            "deck_type": "pitch",
            "visual_style": "mixed",
            "length_hint": "short",
            "tone": "confident-direct",
        }
    )
    errors = validate_brief(brief)
    assert not errors, f"Test setup: invalid brief: {errors}"

    brief_path = tmp_path / "deck_brief.yaml"
    save_brief(brief, brief_path)
    assert brief_path.exists(), "deck_brief.yaml was not written"

    # ------------------------------------------------------------------
    # 2. Write commitment.yaml using the public storyline API
    # ------------------------------------------------------------------
    from feinschliff.storyline.commitment import save_commitment

    commitment = {
        "deck_type": "pitch",
        "thesis": "Cloud is the default, not the exception.",
        "key_moves": [
            "Show the market shift.",
            "Name the stakes of staying on-prem.",
            "Paint the promised land.",
            "Demonstrate our features as the magic path.",
            "Proof from three customer case studies.",
            "Ask for the next meeting.",
        ],
    }
    commitment_path = tmp_path / "commitment.yaml"
    save_commitment(commitment, commitment_path)
    assert commitment_path.exists(), "commitment.yaml was not written"

    # ------------------------------------------------------------------
    # 3. Validate commitment with --check-arc (deck commitment-validate)
    # ------------------------------------------------------------------
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli.main",
            "deck", "commitment-validate", "--check-arc",
            str(commitment_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"commitment-validate --check-arc failed:\n{result.stderr}"
    )

    # ------------------------------------------------------------------
    # 4. Write a minimal content_plan.json (3 slides)
    # ------------------------------------------------------------------
    content_plan = {
        "slides": [
            {"title": "The market is shifting to cloud now."},
            {"title": "On-prem inertia costs more than migration."},
            {"title": "Our platform closes the gap in 90 days."},
        ]
    }
    plan_path = tmp_path / "content_plan.json"
    plan_path.write_text(json.dumps(content_plan), encoding="utf-8")
    assert plan_path.exists(), "content_plan.json was not written"

    # ------------------------------------------------------------------
    # 5. Run ghost-deck (offline — no LLM call)
    # ------------------------------------------------------------------
    ghost_report = tmp_path / "out" / "ghost_deck_report.md"
    ghost_report.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli.main",
            "deck", "ghost-deck",
            str(plan_path),
            "-o", str(ghost_report),
            "--offline",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode in (0, 1), (
        f"ghost-deck returned unexpected exit code {result.returncode}:\n{result.stderr}"
    )
    assert ghost_report.exists(), (
        f"ghost_deck_report.md was not created at {ghost_report}"
    )
    report_text = ghost_report.read_text(encoding="utf-8")
    assert "pass" in report_text or "warn" in report_text or "fail" in report_text, (
        "ghost_deck_report.md does not contain a verdict line"
    )

    # ------------------------------------------------------------------
    # 6. Run title-lint (zero LLM)
    # ------------------------------------------------------------------
    title_report = tmp_path / "out" / "title_lint_report.md"

    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli.main",
            "deck", "title-lint",
            str(plan_path),
            "-o", str(title_report),
        ],
        capture_output=True,
        text=True,
    )
    # title-lint returns 0 (clean) or 1 (issues found) — both are valid runs
    assert result.returncode in (0, 1), (
        f"title-lint returned unexpected exit code {result.returncode}:\n{result.stderr}"
    )
    assert title_report.exists(), (
        f"title_lint_report.md was not created at {title_report}"
    )

    # ------------------------------------------------------------------
    # 7. Summary: assert all produced artifacts exist
    # ------------------------------------------------------------------
    expected_artifacts = {
        "deck_brief.yaml": brief_path,
        "commitment.yaml": commitment_path,
        "content_plan.json": plan_path,
        "ghost_deck_report.md": ghost_report,
        "title_lint_report.md": title_report,
    }
    missing = [name for name, path in expected_artifacts.items() if not path.exists()]
    assert not missing, (
        f"Pipeline tooling failed to produce these artifacts: {missing}"
    )
