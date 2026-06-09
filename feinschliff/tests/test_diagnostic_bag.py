"""Tests for lib.diagnostics.DiagnosticBag."""
from __future__ import annotations

import pytest

from feinschmiede.diagnostics import Defect, DefectKind, DiagnosticBag, Severity


def _error(msg: str = "an error") -> Defect:
    return Defect(kind=DefectKind.INTERNAL, severity=Severity.ERROR, message=msg)


def _warning(msg: str = "a warning") -> Defect:
    return Defect(kind=DefectKind.INTERNAL, severity=Severity.WARNING, message=msg)


def _info(msg: str = "info") -> Defect:
    return Defect(kind=DefectKind.INTERNAL, severity=Severity.INFO, message=msg)


# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------

def test_severity_is_str_enum():
    assert Severity.ERROR == "error"
    assert Severity.WARNING == "warning"
    assert Severity.INFO == "info"
    assert isinstance(Severity.ERROR, str)


# ---------------------------------------------------------------------------
# Defect
# ---------------------------------------------------------------------------

def test_defect_to_dict_minimal():
    d = Defect(
        kind=DefectKind.BRAND_TOKEN_MISSING,
        severity=Severity.ERROR,
        message="missing color.accent",
    )
    result = d.to_dict()
    assert result["kind"] == "brand-token-missing"
    assert result["severity"] == "error"
    assert result["message"] == "missing color.accent"
    assert "location" not in result
    assert "suggestion" not in result
    assert "extra" not in result


def test_defect_to_dict_with_optionals():
    d = Defect(
        kind=DefectKind.LAYOUT_OVERLAP,
        severity=Severity.WARNING,
        message="boxes overlap",
        location="slide 3",
        suggestion="Move box A right 20px",
        extra={"box_ids": ["a", "b"]},
    )
    result = d.to_dict()
    assert result["location"] == "slide 3"
    assert result["suggestion"] == "Move box A right 20px"
    assert result["extra"] == {"box_ids": ["a", "b"]}


def test_defect_is_frozen():
    d = _error()
    with pytest.raises(dataclasses.FrozenInstanceError if hasattr(dataclasses, 'FrozenInstanceError') else AttributeError):
        d.message = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DiagnosticBag — construction
# ---------------------------------------------------------------------------

def test_bag_starts_empty():
    bag = DiagnosticBag()
    assert len(bag) == 0
    assert not bag


def test_bag_add_increments_len():
    bag = DiagnosticBag()
    bag.add(_error())
    assert len(bag) == 1
    bag.add(_warning())
    assert len(bag) == 2


def test_bag_add_rejects_non_defect():
    bag = DiagnosticBag()
    with pytest.raises(TypeError):
        bag.add("not a defect")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# extend
# ---------------------------------------------------------------------------

def test_extend_from_bag():
    bag1 = DiagnosticBag()
    bag1.add(_error())
    bag2 = DiagnosticBag()
    bag2.add(_warning())
    bag1.extend(bag2)
    assert len(bag1) == 2


def test_extend_from_list():
    bag = DiagnosticBag()
    bag.extend([_error(), _warning()])
    assert len(bag) == 2


def test_extend_empty_is_noop():
    bag = DiagnosticBag()
    bag.add(_error())
    bag.extend([])
    assert len(bag) == 1


# ---------------------------------------------------------------------------
# by_severity
# ---------------------------------------------------------------------------

def test_by_severity_filters_correctly():
    bag = DiagnosticBag()
    bag.add(_error("e1"))
    bag.add(_warning("w1"))
    bag.add(_error("e2"))
    bag.add(_info("i1"))
    errors = bag.by_severity(Severity.ERROR)
    assert len(errors) == 2
    assert all(d.severity is Severity.ERROR for d in errors)


def test_by_severity_returns_empty_list_when_none():
    bag = DiagnosticBag()
    bag.add(_warning())
    assert bag.by_severity(Severity.ERROR) == []


def test_by_severity_preserves_order():
    bag = DiagnosticBag()
    bag.add(_error("first"))
    bag.add(_warning())
    bag.add(_error("second"))
    msgs = [d.message for d in bag.by_severity(Severity.ERROR)]
    assert msgs == ["first", "second"]


# ---------------------------------------------------------------------------
# has_errors / has_only_warnings
# ---------------------------------------------------------------------------

def test_has_errors_true_when_error_present():
    bag = DiagnosticBag()
    bag.add(_error())
    assert bag.has_errors()


def test_has_errors_false_when_only_warnings():
    bag = DiagnosticBag()
    bag.add(_warning())
    assert not bag.has_errors()


def test_has_errors_false_when_empty():
    assert not DiagnosticBag().has_errors()


def test_has_only_warnings_true():
    bag = DiagnosticBag()
    bag.add(_warning())
    assert bag.has_only_warnings()


def test_has_only_warnings_false_when_errors():
    bag = DiagnosticBag()
    bag.add(_error())
    bag.add(_warning())
    assert not bag.has_only_warnings()


def test_has_only_warnings_false_when_empty():
    assert not DiagnosticBag().has_only_warnings()


# ---------------------------------------------------------------------------
# to_list
# ---------------------------------------------------------------------------

def test_to_list_returns_list_of_dicts():
    bag = DiagnosticBag()
    bag.add(_error("oops"))
    result = bag.to_list()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["message"] == "oops"
    assert result[0]["severity"] == "error"


def test_to_list_empty_bag_returns_empty_list():
    assert DiagnosticBag().to_list() == []


def test_to_list_preserves_insertion_order():
    bag = DiagnosticBag()
    bag.add(_error("first"))
    bag.add(_warning("second"))
    bag.add(_info("third"))
    msgs = [d["message"] for d in bag.to_list()]
    assert msgs == ["first", "second", "third"]


# ---------------------------------------------------------------------------
# Iteration
# ---------------------------------------------------------------------------

def test_iter_yields_defects():
    bag = DiagnosticBag()
    d1, d2 = _error(), _warning()
    bag.add(d1)
    bag.add(d2)
    assert list(bag) == [d1, d2]


# ---------------------------------------------------------------------------
# Re-export from feinschliff.defects
# ---------------------------------------------------------------------------

def test_diagnostic_bag_importable_from_defects():
    from feinschliff.defects import DiagnosticBag as DBFromDefects
    assert DBFromDefects is DiagnosticBag


import dataclasses
