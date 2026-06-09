"""End-to-end integration test over ``tests/fixture_repo``.

Drives the full :func:`feinblick.orchestrator.run_pipeline` (engines -> native
rules -> dedupe -> health -> gate -> verdict) and the SARIF reporter against a
tiny, self-contained "dirty repo" that ships planted issues:

* ``src/pkg/alpha.py`` — an unused ``import os`` and a never-called
  ``dead_alpha_function`` (what a real CytoScnPy run would flag),
* ``skills/bad/SKILL.md`` — oversized body + ``name`` != dir + weak description,
* ``skills/good/SKILL.md`` — a clean control that must yield zero findings,
* ``feinschliff/examples/x/brief.txt`` — a forbidden examples/ intermediate.

CI has no network, so the **external** code engines (CytoScnPy / Tach) are
stubbed: ``feinblick.adapters.ENGINES`` is monkeypatched to fake engines whose
``ensure_available`` returns ``(True, "")`` and whose ``parse`` yields canned
normalized findings (dead code + a boundary + a circular dependency). The skills
engine (agnix) is disabled in the fixture's ``feinblick.toml`` because it needs
Node, so the **native** rules (skill validation + repo discipline) run for real
against the fixture tree — the planted skill/discipline issues are detected
genuinely, matching how feinblick behaves on a no-Node machine.

The single test that actually shells ``uvx``/``npx`` is ``@pytest.mark.skip``-ed
(needs Node/network + the live engines, neither guaranteed in CI); an operator
runs it by temporarily dropping the skip.
"""

from __future__ import annotations

import json as _json
from pathlib import Path

import pytest

from feinblick.config import load_config
from feinblick.model import (
    Action,
    Category,
    Domain,
    Finding,
    Location,
    Severity,
)
from feinblick.orchestrator import run_pipeline
from feinblick.report import render
from feinblick.runner import RawOutput, Runner

FIXTURE_REPO = Path(__file__).parent / "fixture_repo"


class StubEngine:
    """A no-subprocess Engine: canned availability + canned parsed findings."""

    def __init__(self, name: str, findings: list[Finding]):
        self.name = name
        self._findings = findings

    def ensure_available(self, runner, targets, version):  # noqa: ARG002 - protocol shape
        return (True, "")

    def run(self, runner, targets, version):  # noqa: ARG002 - protocol shape
        return RawOutput("", "", 0)

    def parse(self, raw, targets):  # noqa: ARG002 - protocol shape
        return list(self._findings)


def _dead_code_finding() -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=Category.DEAD_CODE,
        severity=Severity.WARNING,
        location=Location(path="src/pkg/alpha.py", line=18, symbol="alpha.dead_alpha_function"),
        message="'alpha.dead_alpha_function' is defined but never used",
        source_engine="cytoscnpy",
        rule_id="CSP-U001",
        evidence="confidence=high",
        actions=[
            Action("Remove unused function", auto_fixable=True,
                   engine_fix_cmd="cytoscnpy src --make-whitelist"),
        ],
    )


def _unused_import_finding() -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=Category.DEAD_CODE,
        severity=Severity.INFO,
        location=Location(path="src/pkg/alpha.py", line=10, symbol="os"),
        message="'os' is imported but never used",
        source_engine="cytoscnpy",
        rule_id="CSP-U004",
        evidence="confidence=high",
        actions=[],
    )


def _boundary_finding() -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=Category.BOUNDARY,
        severity=Severity.ERROR,
        location=Location(path="src/pkg/alpha.py", line=10, symbol="os"),
        message="Module 'pkg' cannot depend on 'os' (uses 'os')",
        source_engine="tach",
        rule_id="TACH-UndeclaredDependency",
        evidence=None,
        actions=[],
    )


def _circular_finding() -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=Category.CIRCULAR_DEP,
        severity=Severity.ERROR,
        location=Location(path="src"),
        message="Circular dependency: pkg.alpha -> pkg.beta -> pkg.alpha",
        source_engine="tach",
        rule_id="TACH-CYCLE",
        evidence=None,
        actions=[],
    )


def _stub_engines(monkeypatch) -> None:
    """Replace the live ENGINES registry with no-network stubs."""
    # Only the code engines are stubbed. The fixture disables the skills engine
    # (agnix needs Node), so the native skill rules are the sole source of skill
    # findings — exactly the no-Node CI path.
    mapping = {
        "cytoscnpy": StubEngine("cytoscnpy", [_dead_code_finding(), _unused_import_finding()]),
        "tach": StubEngine("tach", [_boundary_finding(), _circular_finding()]),
    }
    import feinblick.adapters as adapters
    import feinblick.orchestrator as orch
    monkeypatch.setattr(adapters, "ENGINES", mapping)
    monkeypatch.setattr(orch, "ENGINES", mapping, raising=False)


def _run(monkeypatch, **kw):
    _stub_engines(monkeypatch)
    cfg = load_config(FIXTURE_REPO)
    runner = Runner(repo_root=FIXTURE_REPO, cache=False)
    return run_pipeline(
        FIXTURE_REPO, cfg, domains={"code", "skills"}, runner=runner, **kw
    )


def test_pipeline_finds_the_planted_issues(monkeypatch):
    res = _run(monkeypatch)
    cats = {f.category for f in res.findings}

    # Stubbed engine findings (code domain).
    assert Category.DEAD_CODE in cats
    assert Category.BOUNDARY in cats
    assert Category.CIRCULAR_DEP in cats

    # Native skill rules over skills/bad/SKILL.md.
    assert Category.PROGRESSIVE_DISCLOSURE in cats
    assert Category.DESCRIPTION in cats
    assert Category.FRONTMATTER in cats

    # Native repo-discipline rule over feinschliff/examples/x/brief.txt.
    assert Category.REPO_DISCIPLINE in cats


def test_bad_skill_findings_point_at_the_bad_skill(monkeypatch):
    res = _run(monkeypatch)
    skill_findings = [f for f in res.findings if f.domain == Domain.SKILL]
    # Every native skill finding here comes from skills/bad/SKILL.md — the good
    # control skill yields nothing.
    assert skill_findings
    assert all(f.location.path == "skills/bad/SKILL.md" for f in skill_findings)
    rule_ids = {f.rule_id for f in skill_findings}
    assert any(r.startswith("FB-SK-PD") for r in rule_ids)
    assert any(r.startswith("FB-SK-FM") for r in rule_ids)
    assert any(r.startswith("FB-SK-DESC") for r in rule_ids)


def test_repo_discipline_flags_brief_txt(monkeypatch):
    res = _run(monkeypatch)
    repo = [f for f in res.findings if f.category == Category.REPO_DISCIPLINE]
    assert len(repo) == 1
    assert repo[0].location.path == "feinschliff/examples/x/brief.txt"
    assert repo[0].rule_id == "FB-REPO-EX001"
    assert repo[0].severity == Severity.ERROR


def test_good_skill_is_clean(monkeypatch):
    res = _run(monkeypatch)
    assert not any(
        f.location.path == "skills/good/SKILL.md" for f in res.findings
    )


def test_gate_all_fails_on_introduced_errors(monkeypatch):
    # The fixture has fresh ERROR-severity findings (boundary + circular +
    # repo-discipline) and no baseline, so gating the full set must FAIL.
    res = _run(monkeypatch, gate="all")
    assert res.verdict == "fail"
    assert res.meta["introduced"] >= 1


def test_informational_run_passes(monkeypatch):
    # gate=None is informational: a verdict is produced and it never fails.
    res = _run(monkeypatch)
    assert res.verdict == "pass"
    assert isinstance(res.health, dict)
    assert 0 <= res.health["score"] <= 100


def test_sarif_report_parses_as_json(monkeypatch):
    res = _run(monkeypatch)
    sarif = render("sarif", res.findings, res.verdict, res.health, res.meta)
    doc = _json.loads(sarif)  # must be valid JSON
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "feinblick"
    # one result per finding, levels mapped through severity.sarif_level
    assert len(doc["runs"][0]["results"]) == len(res.findings)
    rule_ids = {r["ruleId"] for r in doc["runs"][0]["results"]}
    assert "FB-REPO-EX001" in rule_ids
    assert "CSP-U001" in rule_ids


def test_json_report_is_agent_consumable(monkeypatch):
    res = _run(monkeypatch)
    payload = _json.loads(render("json", res.findings, res.verdict, res.health, res.meta))
    assert payload["verdict"] in {"pass", "warn", "fail"}
    assert isinstance(payload["findings"], list)
    # the dead-code finding carries its auto-fix action through to the report
    dead = [f for f in payload["findings"] if f["category"] == "dead_code"]
    assert dead and any(f["actions"] for f in dead)


@pytest.mark.skip(reason="shells real uvx/npx engines — needs Node/network, not run in CI")
def test_live_engines_smoke():  # pragma: no cover - network/uvx only
    """Real ``uvx`` CytoScnPy/Tach run over the fixture (skipped by default).

    Left here so an operator can prove the live chain end-to-end by dropping the
    skip; CI has no guaranteed engines or network.
    """
    cfg = load_config(FIXTURE_REPO)
    runner = Runner(repo_root=FIXTURE_REPO, cache=False)
    res = run_pipeline(FIXTURE_REPO, cfg, domains={"code", "skills"}, runner=runner)
    assert res.verdict in {"pass", "warn", "fail"}
