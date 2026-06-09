"""Tests for the orchestrator pipeline.

Drives :func:`feinblick.orchestrator.run_pipeline` with a *fake* engine
(monkeypatched into ``feinblick.adapters.ENGINES``) so nothing shells out to a
real ``uvx``/``npx`` or the network. Asserts pooling+dedupe, verdict math, and
unavailable-engine degradation.
"""

from __future__ import annotations

import pytest

from feinblick.config import load_config
from feinblick.model import Action, Category, Domain, Finding, Location, Severity
from feinblick.orchestrator import Result, run_pipeline
from feinblick.runner import RawOutput, Runner


class FakeEngine:
    """A stand-in Engine: canned availability + canned findings, no subprocess."""

    name = "fake"

    def __init__(self, findings, *, available=True, reason="", error=None):
        self._findings = findings
        self._available = available
        self._reason = reason
        self._error = error
        self.ran = False

    def ensure_available(self, runner, targets, version):
        return (self._available, self._reason)

    def run(self, runner, targets, version):
        self.ran = True
        return RawOutput("", "", 0)

    def parse(self, raw, targets):
        return list(self._findings)

    def is_error(self, raw):
        return self._error


def _finding(symbol="a.dead", severity=Severity.ERROR, engine="cytoscnpy",
             category=Category.DEAD_CODE, path="feinschliff/lib/a.py"):
    return Finding(
        domain=Domain.CODE, category=category, severity=severity,
        location=Location(path=path, line=11, symbol=symbol),
        message=f"'{symbol}' is dead", source_engine=engine,
        rule_id="CSP-U001", evidence=None,
        actions=[Action(description="Remove it", auto_fixable=True)],
    )


def _patch_engines(monkeypatch, mapping):
    import feinblick.adapters as adapters
    monkeypatch.setattr(adapters, "ENGINES", mapping)
    # orchestrator looks up ENGINES.get on the live module object
    import feinblick.orchestrator as orch
    monkeypatch.setattr(orch, "ENGINES", mapping, raising=False)


def _config(tmp_path, *, engines=("cytoscnpy",)):
    cfg = load_config(tmp_path)
    cfg.code.engines = list(engines)
    cfg.code.roots = ["lib"]
    (tmp_path / "lib").mkdir(exist_ok=True)  # root must exist or the domain is skipped
    cfg.skills.engines = []
    return cfg


def test_pools_and_dedupes_two_engines(tmp_path, monkeypatch):
    # Two engines report the SAME logical finding -> dedupe collapses to one.
    f = _finding(engine="cytoscnpy")
    g = _finding(engine="cytoscnpy")  # identical fingerprint
    _patch_engines(monkeypatch, {
        "cytoscnpy": FakeEngine([f]),
        "tach": FakeEngine([g]),
    })
    cfg = _config(tmp_path, engines=("cytoscnpy", "tach"))
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner)
    assert isinstance(res, Result)
    assert len(res.findings) == 1
    assert res.meta["engines"] == ["cytoscnpy", "tach"]
    assert res.meta["domains"] == ["code"]


def test_gate_none_is_informational_pass(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, {"cytoscnpy": FakeEngine([_finding()])})
    cfg = _config(tmp_path)
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, gate=None)
    assert res.verdict == "pass"
    assert len(res.findings) == 1


def test_introduced_error_fails(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, {"cytoscnpy": FakeEngine([_finding(severity=Severity.ERROR)])})
    cfg = _config(tmp_path)
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, gate="all")
    assert res.verdict == "fail"
    assert res.meta["introduced"] == 1


def test_tolerance_respected(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, {"cytoscnpy": FakeEngine([_finding(severity=Severity.ERROR)])})
    cfg = _config(tmp_path)
    cfg.gate.tolerance = 1  # one error tolerated -> not over budget
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, gate="all")
    assert res.verdict == "pass"


def test_warning_only_yields_warn(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, {"cytoscnpy": FakeEngine([_finding(severity=Severity.WARNING)])})
    cfg = _config(tmp_path)
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, gate="all")
    assert res.verdict == "warn"


def test_baseline_classifies_preexisting_out_of_introduced(tmp_path, monkeypatch):
    err = _finding(severity=Severity.ERROR)
    _patch_engines(monkeypatch, {"cytoscnpy": FakeEngine([err])})
    cfg = _config(tmp_path)
    # accept the error in the baseline -> classified as preexisting, not introduced
    from feinblick import baseline
    baseline.save(tmp_path / ".feinblick" / "baseline.json", [err])
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, gate="all")
    # gate=all gates on the full merged set, so the verdict still fails...
    assert res.verdict == "fail"
    # ...but the baseline-classified introduced set is empty (it's preexisting).
    assert res.introduced == []


def test_baseline_unaccepted_is_introduced(tmp_path, monkeypatch):
    err = _finding(severity=Severity.ERROR)
    _patch_engines(monkeypatch, {"cytoscnpy": FakeEngine([err])})
    cfg = _config(tmp_path)
    # empty baseline -> the error is introduced
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, gate="all")
    assert res.verdict == "fail"
    assert len(res.introduced) == 1


def test_unavailable_engine_records_meta_and_continues(tmp_path, monkeypatch):
    good = FakeEngine([_finding()])
    bad = FakeEngine([], available=False, reason="npx not found")
    _patch_engines(monkeypatch, {"cytoscnpy": good, "agnix": bad})
    cfg = _config(tmp_path, engines=("cytoscnpy", "agnix"))
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner)
    assert res.meta["engines"] == ["cytoscnpy"]
    assert res.meta["unavailable"] == [{"engine": "agnix", "reason": "npx not found"}]
    assert len(res.findings) == 1  # partial result still produced


def test_strict_raises_on_unavailable(tmp_path, monkeypatch):
    bad = FakeEngine([], available=False, reason="npx not found")
    _patch_engines(monkeypatch, {"agnix": bad})
    cfg = _config(tmp_path, engines=("agnix",))
    runner = Runner(repo_root=tmp_path, cache=False)
    with pytest.raises(RuntimeError, match="npx not found"):
        run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, strict=True)


def test_unknown_engine_name_is_skipped(tmp_path, monkeypatch):
    _patch_engines(monkeypatch, {})  # registry empty -> ENGINES.get returns None
    cfg = _config(tmp_path, engines=("cytoscnpy",))
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner)
    assert res.findings == []
    assert res.meta["engines"] == []


def test_engine_runtime_error_recorded_not_counted_as_clean(tmp_path, monkeypatch):
    # An engine that errors at runtime (e.g. cytoscnpy exit 1 + empty stdout on a
    # missing path) must surface in meta["errors"], NOT masquerade as a clean run.
    bad = FakeEngine([_finding()], error="cytoscnpy exited 1 with no output")
    _patch_engines(monkeypatch, {"cytoscnpy": bad})
    cfg = _config(tmp_path)
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, gate="all")
    assert res.meta["errors"] == [
        {"engine": "cytoscnpy", "reason": "cytoscnpy exited 1 with no output"}
    ]
    assert res.meta["engines"] == []          # not counted as a successful run
    assert res.findings == []                 # its (untrusted) output is not parsed


def test_strict_raises_on_engine_error(tmp_path, monkeypatch):
    bad = FakeEngine([], error="cytoscnpy crashed")
    _patch_engines(monkeypatch, {"cytoscnpy": bad})
    cfg = _config(tmp_path)
    runner = Runner(repo_root=tmp_path, cache=False)
    with pytest.raises(RuntimeError, match="cytoscnpy crashed"):
        run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, strict=True)


def test_missing_root_recorded_and_domain_skipped(tmp_path, monkeypatch):
    eng = FakeEngine([_finding()])
    _patch_engines(monkeypatch, {"cytoscnpy": eng})
    cfg = _config(tmp_path)
    cfg.code.roots = ["does_not_exist"]       # never created -> missing
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner)
    assert res.meta["missing_roots"] == ["code:does_not_exist"]
    assert eng.ran is False                   # engine never invoked on a dead path
    assert res.meta["engines"] == [] and res.findings == []


def test_skills_domain_engine_runs_without_test_globs_attr(tmp_path, monkeypatch):
    # Regression: the orchestrator builds Targets(..., section.test_globs, ...)
    # for EVERY domain. SkillsCfg must expose test_globs or an available skills
    # engine (agnix) crashes with AttributeError the moment npx is present.
    agnix = FakeEngine([_finding(category=Category.FRONTMATTER, engine="agnix")])
    _patch_engines(monkeypatch, {"agnix": agnix})
    cfg = _config(tmp_path)
    cfg.skills.engines = ["agnix"]
    cfg.skills.roots = ["."]
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"skills"}, runner=runner)
    assert agnix.ran is True
    assert res.meta["engines"] == ["agnix"]


def test_introduced_gate_without_diff_or_ref_gates_nothing(tmp_path, monkeypatch):
    # gate=introduced but neither since_ref nor diff_file -> no attribution set
    # -> nothing is treated as a candidate -> pass even with an error present.
    _patch_engines(monkeypatch, {"cytoscnpy": FakeEngine([_finding(severity=Severity.ERROR)])})
    cfg = _config(tmp_path)
    runner = Runner(repo_root=tmp_path, cache=False)
    res = run_pipeline(tmp_path, cfg, domains={"code"}, runner=runner, gate="introduced")
    assert res.verdict == "pass"
    assert res.meta["introduced"] == 0
    # but the full (deduped) finding set is still reported
    assert len(res.findings) == 1
    # ...and a vacuous PASS is flagged so it isn't misread as "tree is clean"
    assert "gate_note" in res.meta and "does not reflect" in res.meta["gate_note"]
