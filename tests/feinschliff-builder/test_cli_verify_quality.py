import json
import subprocess
from pathlib import Path

import pytest

_BUILDER_ROOT = Path(__file__).resolve().parents[2] / "feinschliff-builder"
REPO_ROOT = _BUILDER_ROOT.parent / "feinschliff"
# The committed sample deck + content live with the core feinschliff tests.
_CORE_FIXTURES = Path(__file__).resolve().parents[1] / "feinschliff" / "fixtures"
SAMPLE_DECK = _CORE_FIXTURES / "verify_quality" / "clean-deck.pptx"


@pytest.fixture(autouse=True)
def _ensure_fixture(tmp_path):
    if not SAMPLE_DECK.exists():
        SAMPLE_DECK.parent.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([
            "uv", "run", "feinschliff", "build",
            str(REPO_ROOT / "layouts" / "executive-summary.slide.dsl"),
            "--brand", "feinschliff",
            "--content", str(_CORE_FIXTURES / "verify_quality" / "executive-summary-content.yaml"),
            "-o", str(SAMPLE_DECK),
        ], cwd=REPO_ROOT)


def test_verify_quality_offline_emits_skipped_verdict(tmp_path):
    out = tmp_path / "report.json"
    proc = subprocess.run(
        ["uv", "run", "feinschliff-builder", "verify-quality",
         str(SAMPLE_DECK), "--offline", "--json", "--out", str(out)],
        cwd=_BUILDER_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text())
    assert report["verdict"] in {"pass", "skipped-llm"}
    assert "squint" in report["rubric"]
    assert report["rubric"]["squint"]["status"] in {"pass", "skipped"}
    assert "thumbnails" in report["artifacts"]


def test_verify_quality_selective_rubric(tmp_path):
    out = tmp_path / "report.json"
    proc = subprocess.run(
        ["uv", "run", "feinschliff-builder", "verify-quality",
         str(SAMPLE_DECK), "--rubric", "title-body", "--offline",
         "--json", "--out", str(out)],
        cwd=_BUILDER_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text())
    assert set(report["rubric"]) == {"title-body"}


def test_verify_quality_emits_markdown_report_by_default(tmp_path):
    out = tmp_path / "verify_report.md"
    proc = subprocess.run(
        ["uv", "run", "feinschliff-builder", "verify-quality",
         str(SAMPLE_DECK), "--offline", "--out", str(out)],
        cwd=_BUILDER_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    body = out.read_text()
    assert "# Quality Verify Report" in body
    assert "## Squint test" in body
    assert "## Title-body coherence" in body
