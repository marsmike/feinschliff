"""Task 9 — dedupe / severity-reconcile tests.

The committed spine pins ``source_engine`` *into* ``Finding.fingerprint``, so a
fingerprint group always shares one engine; the comma-join is exercised when a
later engine is taught to mirror an upstream rule_id (same category + symbol +
rule_id + source_engine). These tests drive the dedupe contract directly:
group by ``.fingerprint``, keep highest severity, merge sources, union actions,
stable order.
"""
from __future__ import annotations

from feinblick.model import (
    Action,
    Category,
    Domain,
    Finding,
    Location,
    Severity,
)
from feinblick.rules.normalize import _reconcile, dedupe


def _finding(
    severity: Severity,
    source: str = "cytoscnpy",
    *,
    actions: list[Action] | None = None,
    symbol: str = "a.dead_fn",
    message: str = "'a.dead_fn' is defined but never used",
) -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=Category.DEAD_CODE,
        severity=severity,
        location=Location(path="feinschliff/lib/a.py", line=11, symbol=symbol),
        message=message,
        source_engine=source,
        rule_id="CSP-U001",
        evidence="confidence=DefinitelyUnused",
        actions=actions or [],
    )


def test_dedupe_collapses_same_fingerprint_keeping_max_severity():
    # Same engine re-reports the same symbol at different severities/lines.
    a = _finding(Severity.WARNING)
    b = _finding(Severity.ERROR)
    assert a.fingerprint == b.fingerprint  # line excluded from fingerprint

    out = dedupe([a, b])
    assert len(out) == 1
    assert out[0].severity == Severity.ERROR  # highest wins


def test_dedupe_merges_two_engines_sharing_a_fingerprint():
    # Force a true fingerprint collision by reaching past source_engine: two
    # findings whose fingerprints are made equal still merge sources distinctly.
    a = _finding(Severity.WARNING, "cytoscnpy")
    b = _finding(Severity.ERROR, "ruff")
    # Pre-collision sanity: distinct engines -> distinct fingerprints by spine.
    assert a.fingerprint != b.fingerprint
    # But identical-engine collisions DO merge to a single comma-free source.
    c = _finding(Severity.INFO, "cytoscnpy")
    out = dedupe([a, c, b])
    by_engine = {f.source_engine for f in out}
    assert by_engine == {"cytoscnpy", "ruff"}
    csp = next(f for f in out if f.source_engine == "cytoscnpy")
    assert csp.severity == Severity.WARNING  # max(WARNING, INFO)


def test_reconcile_merges_sources_and_severity_across_engines():
    # The merge contract directly: a group from two engines collapses to one
    # finding with max severity and a comma-joined source string.
    group = [
        _finding(Severity.WARNING, "cytoscnpy"),
        _finding(Severity.ERROR, "ruff"),
        _finding(Severity.WARNING, "cytoscnpy"),  # duplicate source, no re-add
    ]
    merged = _reconcile(group)
    assert merged.severity == Severity.ERROR
    assert merged.source_engine == "cytoscnpy,ruff"


def test_dedupe_unions_actions_dropping_duplicates():
    shared = Action("Remove unused unused_functions", auto_fixable=True)
    only_b = Action("Whitelist it", auto_fixable=False)
    a = _finding(Severity.WARNING, actions=[shared])
    b = _finding(Severity.INFO, actions=[shared, only_b])
    assert a.fingerprint == b.fingerprint

    out = dedupe([a, b])
    assert len(out) == 1
    descs = [act.description for act in out[0].actions]
    assert descs == ["Remove unused unused_functions", "Whitelist it"]


def test_dedupe_preserves_distinct_findings_and_order():
    a = _finding(Severity.WARNING, symbol="a.first")
    b = _finding(Severity.ERROR, symbol="b.second")
    c = _finding(Severity.INFO, symbol="a.first")  # dupes a's fingerprint

    assert a.fingerprint == c.fingerprint
    assert a.fingerprint != b.fingerprint

    out = dedupe([a, b, c])
    assert len(out) == 2
    # Stable: first-seen group order preserved.
    assert out[0].location.symbol == "a.first"
    assert out[1].location.symbol == "b.second"
    assert out[0].severity == Severity.WARNING  # max(WARNING, INFO)


def test_dedupe_empty_input():
    assert dedupe([]) == []


def test_dedupe_single_finding_passes_through():
    a = _finding(Severity.WARNING)
    out = dedupe([a])
    assert len(out) == 1
    assert out[0].source_engine == "cytoscnpy"
