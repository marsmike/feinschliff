"""Task 9 — 0-100 health synthesis tests."""
from __future__ import annotations

from feinblick.model import (
    Category,
    Domain,
    Finding,
    Location,
    Severity,
)
from feinblick.rules import health
from feinblick.rules.health import compute_health


def _finding(severity: Severity, path: str, symbol: str) -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=Category.DEAD_CODE,
        severity=severity,
        location=Location(path=path, line=1, symbol=symbol),
        message="m",
        source_engine="cytoscnpy",
        rule_id="CSP-U001",
    )


def test_all_clean_is_100():
    out = compute_health([])
    assert out["score"] == 100
    assert out["hotspots"] == []


def test_named_weight_constants_exist():
    assert health.W_ERROR == 4.0
    assert health.W_WARNING == 1.5
    assert health.W_INFO == 0.25


def test_errors_drop_below_100_with_expected_weights():
    findings = [
        _finding(Severity.ERROR, "a.py", "e1"),
        _finding(Severity.WARNING, "a.py", "w1"),
        _finding(Severity.INFO, "b.py", "i1"),
    ]
    out = compute_health(findings)
    # 100 - 4.0 - 1.5 - 0.25 = 94.25 -> round -> 94
    assert out["score"] == 94
    assert isinstance(out["score"], int)


def test_score_floors_at_zero():
    findings = [_finding(Severity.ERROR, "a.py", f"e{i}") for i in range(50)]
    out = compute_health(findings)
    assert out["score"] == 0


def test_hotspots_top5_by_finding_count():
    findings = []
    # 6 files, descending finding counts 6..1
    for n, fname in enumerate(["f6", "f5", "f4", "f3", "f2", "f1"]):
        for k in range(6 - n):
            findings.append(_finding(Severity.INFO, f"{fname}.py", f"{fname}_{k}"))
    out = compute_health(findings)
    spots = out["hotspots"]
    assert len(spots) == 5  # top-5 only
    paths = [s["path"] for s in spots]
    assert paths == ["f6.py", "f5.py", "f4.py", "f3.py", "f2.py"]
    assert spots[0] == {"path": "f6.py", "findings": 6}
    assert all("findings" in s and "path" in s for s in spots)


def test_complexity_term_lowers_score():
    findings = [_finding(Severity.WARNING, "a.py", "w1")]
    base = compute_health(findings)
    # high average cyclomatic complexity over the threshold => extra penalty
    with_complex = compute_health(
        findings, file_metrics={"a.py": 40.0, "b.py": 35.0}
    )
    assert with_complex["score"] < base["score"]


def test_complexity_below_threshold_no_penalty():
    findings = [_finding(Severity.WARNING, "a.py", "w1")]
    base = compute_health(findings)
    low = compute_health(findings, file_metrics={"a.py": 2.0, "b.py": 3.0})
    assert low["score"] == base["score"]


def test_hotspots_break_ties_by_complexity():
    findings = [
        _finding(Severity.INFO, "a.py", "a1"),
        _finding(Severity.INFO, "b.py", "b1"),
    ]
    out = compute_health(findings, file_metrics={"a.py": 5.0, "b.py": 30.0})
    paths = [s["path"] for s in out["hotspots"]]
    # equal finding count (1 each) -> higher complexity ranks first
    assert paths == ["b.py", "a.py"]
