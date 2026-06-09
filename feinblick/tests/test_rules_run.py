"""Task 9 — run_rules() orchestration tests."""
from __future__ import annotations

from feinblick.config import load_config
from feinblick.model import (
    Category,
    Domain,
    Finding,
    Location,
    Severity,
)
from feinblick.rules import run_rules


def _engine_finding(symbol: str = "a.dead_fn") -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=Category.DEAD_CODE,
        severity=Severity.WARNING,
        location=Location(path="feinschliff/lib/a.py", line=11, symbol=symbol),
        message="m",
        source_engine="cytoscnpy",
        rule_id="CSP-U001",
    )


def _bad_skill(tmp_path):
    d = tmp_path / "skills" / "something"
    d.mkdir(parents=True)
    # name does not match dir, weak description -> frontmatter + description findings
    (d / "SKILL.md").write_text(
        "---\nname: Bad_Name\ndescription: short\n---\n# x\nbody\n"
    )


def _examples_violation(tmp_path):
    p = tmp_path / "feinschliff" / "examples" / "a" / "brief.txt"
    p.parent.mkdir(parents=True)
    p.write_text("inputs")


def test_run_rules_returns_findings_and_health(tmp_path):
    cfg = load_config(tmp_path)
    cfg.skills.roots = ["skills"]
    findings, health = run_rules([_engine_finding()], tmp_path, cfg, domains=set())
    assert isinstance(findings, list)
    assert isinstance(health, dict)
    assert "score" in health and "hotspots" in health
    # no domains selected -> only the passed-in engine finding survives
    assert len(findings) == 1


def test_run_rules_skills_domain_picks_up_bad_skill(tmp_path):
    _bad_skill(tmp_path)
    cfg = load_config(tmp_path)
    cfg.skills.roots = ["skills"]
    findings, _ = run_rules([], tmp_path, cfg, domains={"skills"})
    assert any(f.domain == Domain.SKILL for f in findings)
    assert any(f.category == Category.FRONTMATTER for f in findings)


def test_run_rules_code_domain_picks_up_examples_violation(tmp_path):
    _examples_violation(tmp_path)
    cfg = load_config(tmp_path)
    findings, _ = run_rules([], tmp_path, cfg, domains={"code"})
    assert any(f.category == Category.REPO_DISCIPLINE for f in findings)


def test_run_rules_dedupes_engine_plus_native(tmp_path):
    # An engine finding that has the identical fingerprint of nothing native,
    # but assert dedupe is applied: feed two identical engine findings.
    a = _engine_finding()
    b = _engine_finding()
    assert a.fingerprint == b.fingerprint
    findings, _ = run_rules([a, b], tmp_path, load_config(tmp_path), domains=set())
    assert len(findings) == 1


def test_run_rules_skills_only_does_not_run_repo_discipline(tmp_path):
    _examples_violation(tmp_path)
    cfg = load_config(tmp_path)
    cfg.skills.roots = ["skills"]
    findings, _ = run_rules([], tmp_path, cfg, domains={"skills"})
    assert not any(f.category == Category.REPO_DISCIPLINE for f in findings)


def test_run_rules_health_reflects_findings(tmp_path):
    cfg = load_config(tmp_path)
    cfg.skills.roots = ["skills"]
    _, health = run_rules(
        [_engine_finding()], tmp_path, cfg, domains=set()
    )
    assert health["score"] < 100
