import json

from feinblick import baseline
from feinblick.model import Category, Domain, Finding, Location, Severity


def _finding(symbol: str, category: Category = Category.DEAD_CODE) -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=category,
        severity=Severity.WARNING,
        location=Location(path="lib/a.py", line=11, symbol=symbol),
        message=f"'{symbol}' is defined but never used",
        source_engine="cytoscnpy",
        rule_id="CSP-U001",
    )


def test_save_writes_sorted_unique_fingerprints(tmp_path):
    a = _finding("a.dead_fn")
    b = _finding("b.dead_fn")
    path = tmp_path / "nested" / "baseline.json"
    baseline.save(path, [a, b, a])  # duplicate a should collapse
    data = json.loads(path.read_text())
    fps = data["fingerprints"]
    assert fps == sorted(set(fps))  # sorted + unique
    assert set(fps) == {a.fingerprint, b.fingerprint}
    assert len(fps) == 2  # the duplicate a is collapsed


def test_save_load_roundtrip(tmp_path):
    a = _finding("a.dead_fn")
    b = _finding("b.dead_fn")
    path = tmp_path / "baseline.json"
    baseline.save(path, [a, b])
    loaded = baseline.load(path)
    assert isinstance(loaded, set)
    assert loaded == {a.fingerprint, b.fingerprint}


def test_load_missing_is_empty_set(tmp_path):
    loaded = baseline.load(tmp_path / "does-not-exist.json")
    assert loaded == set()
    assert isinstance(loaded, set)


def test_classify_splits_introduced_and_preexisting(tmp_path):
    a = _finding("a.dead_fn")
    b = _finding("b.dead_fn")
    c = _finding("c.dead_fn")
    accepted = {a.fingerprint, b.fingerprint}
    introduced, preexisting = baseline.classify([a, b, c], accepted)
    assert introduced == [c]  # only c is new
    assert preexisting == [a, b]


def test_classify_empty_baseline_makes_all_introduced():
    a = _finding("a.dead_fn")
    b = _finding("b.dead_fn")
    introduced, preexisting = baseline.classify([a, b], set())
    assert introduced == [a, b]
    assert preexisting == []
