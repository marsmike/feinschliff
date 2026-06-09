from feinblick.model import (
    Action,
    Category,
    Domain,
    Finding,
    Location,
    Severity,
    fingerprint,
)


def _finding(**kw):
    base = dict(
        domain=Domain.CODE, category=Category.DEAD_CODE, severity=Severity.WARNING,
        location=Location(path="feinschliff/lib/a.py", line=11, symbol="a.dead_fn"),
        message="'a.dead_fn' is defined but never used", evidence=None,
        actions=[], source_engine="cytoscnpy", rule_id="CSP-U001",
    )
    base.update(kw)
    return Finding(**base)


def test_fingerprint_is_stable_across_line_moves():
    a = _finding(location=Location(path="lib/a.py", line=11, symbol="a.dead_fn"))
    b = _finding(location=Location(path="lib/a.py", line=999, symbol="a.dead_fn"))
    assert fingerprint(a) == fingerprint(b)          # line number excluded


def test_fingerprint_differs_on_symbol_or_category():
    a = _finding(location=Location(path="lib/a.py", line=11, symbol="a.dead_fn"))
    b = _finding(location=Location(path="lib/a.py", line=11, symbol="a.other_fn"))
    assert fingerprint(a) != fingerprint(b)
    c = _finding(category=Category.DUPLICATION)
    assert fingerprint(a) != fingerprint(c)


def test_fingerprint_digests_numbers_out_of_evidence():
    a = _finding(evidence="McCabe=6")
    b = _finding(evidence="McCabe=9")
    assert fingerprint(a) == fingerprint(b)          # numeric noise normalized


def test_to_dict_roundtrips_and_includes_actions():
    f = _finding(actions=[Action(description="Remove dead function", auto_fixable=True,
                                 engine_fix_cmd="cytoscnpy --make-whitelist")])
    d = f.to_dict()
    assert d["category"] == "dead_code" and d["severity"] == "warning"
    assert d["domain"] == "code" and d["fingerprint"] == fingerprint(f)
    assert d["actions"][0] == {"description": "Remove dead function", "auto_fixable": True,
                               "engine_fix_cmd": "cytoscnpy --make-whitelist"}
    assert d["location"] == {
        "path": "feinschliff/lib/a.py", "line": 11, "col": None, "symbol": "a.dead_fn",
    }


def test_severity_from_engine_normalizes_casing():
    assert Severity.from_engine("CRITICAL") == Severity.ERROR
    assert Severity.from_engine("HIGH") == Severity.ERROR
    assert Severity.from_engine("Critical") == Severity.ERROR
    assert Severity.from_engine("error") == Severity.ERROR
    assert Severity.from_engine("Error") == Severity.ERROR
    assert Severity.from_engine("MEDIUM") == Severity.WARNING
    assert Severity.from_engine("WARNING") == Severity.WARNING
    assert Severity.from_engine("warning") == Severity.WARNING
    assert Severity.from_engine("Warning") == Severity.WARNING
    assert Severity.from_engine("LOW") == Severity.INFO
    assert Severity.from_engine("INFO") == Severity.INFO
    assert Severity.from_engine("info") == Severity.INFO
    assert Severity.from_engine("note") == Severity.INFO
    assert Severity.from_engine("totally-unknown") == Severity.WARNING
