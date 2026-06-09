"""Task 11 — reporter contract tests.

Every reporter exposes ``render(findings, verdict, health, meta) -> str``.
``report/__init__.py`` exposes ``REPORTERS`` and a ``render(fmt, ...)`` dispatcher.
"""
from __future__ import annotations

import datetime
import json as _json

import pytest

from feinblick import report
from feinblick.model import (
    Action,
    Category,
    Domain,
    Finding,
    Location,
    Severity,
)


def _findings() -> list[Finding]:
    return [
        Finding(
            domain=Domain.CODE,
            category=Category.DEAD_CODE,
            severity=Severity.WARNING,
            location=Location(path="feinschliff/lib/a.py", line=11, symbol="a.dead_fn"),
            message="'a.dead_fn' is defined but never used",
            source_engine="cytoscnpy",
            rule_id="CSP-U001",
            evidence="confidence=DefinitelyUnused",
            actions=[
                Action(
                    description="Remove unused unused_functions",
                    auto_fixable=True,
                    engine_fix_cmd="cytoscnpy <roots> --make-whitelist",
                )
            ],
        ),
        Finding(
            domain=Domain.CODE,
            category=Category.CIRCULAR_DEP,
            severity=Severity.ERROR,
            location=Location(path="feinschliff/lib", line=None, symbol="mod_a"),
            message="Circular dependency: mod_a -> mod_b -> mod_a",
            source_engine="tach",
            rule_id="TACH-CYCLE",
            evidence=None,
            actions=[],
        ),
        Finding(
            domain=Domain.SKILL,
            category=Category.PROGRESSIVE_DISCLOSURE,
            severity=Severity.INFO,
            location=Location(path="feinbild/skills/svg/SKILL.md", line=1, symbol=None),
            message="SKILL.md body exceeds the progressive-disclosure budget",
            source_engine="feinblick:rules",
            rule_id="FB-SK-PD001",
            evidence="640 lines > 500",
            actions=[Action(description="Split into a reference doc", auto_fixable=False)],
        ),
    ]


def _health() -> dict:
    return {"score": 73, "hotspots": [{"path": "feinschliff/lib/a.py", "count": 2}]}


def _meta() -> dict:
    return {"engines": ["cytoscnpy", "tach"], "unavailable": ["agnix"], "introduced": 1}


# --- registry / dispatcher -------------------------------------------------


def test_reporters_registry_keys():
    assert set(report.REPORTERS) == {"terminal", "json", "sarif", "markdown"}
    for fn in report.REPORTERS.values():
        assert callable(fn)


def test_render_dispatch_matches_registry():
    findings, verdict, health, meta = _findings(), "fail", _health(), _meta()
    for fmt, fn in report.REPORTERS.items():
        assert report.render(fmt, findings, verdict, health, meta) == fn(
            findings, verdict, health, meta
        )


def test_render_unknown_format_raises():
    with pytest.raises(ValueError):
        report.render("xml", _findings(), "pass", _health(), _meta())


# --- json ------------------------------------------------------------------


def test_json_roundtrips_with_actions():
    findings = _findings()
    out = report.render("json", findings, "fail", _health(), _meta())
    data = _json.loads(out)
    assert data["verdict"] == "fail"
    assert data["health"]["score"] == 73
    assert data["meta"]["introduced"] == 1
    assert len(data["findings"]) == 3
    assert data["findings"] == [f.to_dict() for f in findings]
    first = data["findings"][0]
    assert first["actions"][0]["auto_fixable"] is True
    assert first["actions"][0]["engine_fix_cmd"] == "cytoscnpy <roots> --make-whitelist"


# --- sarif -----------------------------------------------------------------


def test_sarif_parses_and_maps_levels():
    findings = _findings()
    out = report.render("sarif", findings, "fail", _health(), _meta())
    doc = _json.loads(out)
    assert doc["version"] == "2.1.0"
    assert "$schema" in doc
    driver = doc["runs"][0]["tool"]["driver"]
    assert driver["name"] == "feinblick"

    rule_ids = [r["id"] for r in driver["rules"]]
    assert rule_ids == sorted(set(rule_ids))  # unique
    assert set(rule_ids) == {"CSP-U001", "TACH-CYCLE", "FB-SK-PD001"}

    results = doc["runs"][0]["results"]
    assert len(results) == 3
    by_rule = {r["ruleId"]: r for r in results}
    # info -> note
    assert by_rule["FB-SK-PD001"]["level"] == "note"
    assert by_rule["CSP-U001"]["level"] == "warning"
    assert by_rule["TACH-CYCLE"]["level"] == "error"

    dead = by_rule["CSP-U001"]
    phys = dead["locations"][0]["physicalLocation"]
    assert phys["artifactLocation"]["uri"] == "feinschliff/lib/a.py"
    assert phys["region"]["startLine"] == 11
    assert dead["message"]["text"] == "'a.dead_fn' is defined but never used"

    # no line -> no region
    cyc = by_rule["TACH-CYCLE"]
    assert "region" not in cyc["locations"][0]["physicalLocation"]


# --- terminal --------------------------------------------------------------


def test_terminal_ends_with_verdict_token():
    out = report.render("terminal", _findings(), "fail", _health(), _meta())
    assert out.rstrip().splitlines()[-1].find("FAIL") != -1
    # severities present as group labels
    assert "ERROR" in out and "WARNING" in out and "INFO" in out


def test_terminal_warn_and_pass_tokens():
    warn = report.render("terminal", _findings(), "warn", _health(), _meta())
    assert "WARN" in warn.rstrip().splitlines()[-1]
    clean = report.render("terminal", [], "pass", {"score": 100, "hotspots": []}, {})
    assert "PASS" in clean.rstrip().splitlines()[-1]


# --- markdown --------------------------------------------------------------


def test_markdown_has_score_and_category_heading():
    out = report.render("markdown", _findings(), "fail", _health(), _meta())
    assert out.lstrip().startswith("# ")
    assert str(datetime.date.today().year) in out
    assert "73" in out  # health score
    # one category heading per present category (title-ish form)
    assert "Dead Code" in out or "dead_code" in out
    assert "Circular Dep" in out or "circular_dep" in out
    # verdict line
    assert "FAIL" in out or "fail" in out
