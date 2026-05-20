import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ship_runs_build_verify_quality_and_emits_consolidated_report(tmp_path):
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        "brand: feinschliff\n"
        f"out: {tmp_path / 'deck.pptx'}\n"
        "slides:\n"
        f"  - layout: {REPO_ROOT / 'layouts' / 'executive-summary.slide.dsl'}\n"
        f"    content_file: {REPO_ROOT / 'tests' / 'fixtures' / 'verify_quality' / 'executive-summary-content.yaml'}\n"
    )
    proc = subprocess.run(
        ["uv", "run", "feinschliff", "ship", str(plan), "-o", str(tmp_path / "deck.pptx")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report_path = tmp_path / "ship_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert report["verdict"] == "pass"
    assert set(report["gates"]) >= {"build", "verify", "verify-quality"}
    for gate in report["gates"].values():
        assert gate["status"] in {"pass", "skipped"}


def test_ship_fails_when_build_aborts(tmp_path):
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        "brand: feinschliff\n"
        f"out: {tmp_path / 'deck.pptx'}\n"
        "slides:\n"
        f"  - layout: {REPO_ROOT / 'layouts' / 'executive-summary.slide.dsl'}\n"
        f"    content_file: {tmp_path / 'does-not-exist.yaml'}\n"
    )
    proc = subprocess.run(
        ["uv", "run", "feinschliff", "ship", str(plan), "-o", str(tmp_path / "deck.pptx")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode != 0
    report_path = tmp_path / "ship_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        assert report["verdict"] == "fail"
        assert report["gates"]["build"]["status"] == "fail"
