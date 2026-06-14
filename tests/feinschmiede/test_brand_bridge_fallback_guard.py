"""brand_bridge.font_fallback_resolvable — shared font-fallback guard (F4)."""
import json
from pathlib import Path

import pytest

import feinschmiede.diagrams.brand_bridge as bb
from feinschmiede.text import measure


def _brand(tmp_path: Path, name: str = "testbrand") -> Path:
    brand = tmp_path / name
    brand.mkdir()
    (brand / "tokens.json").write_text(
        json.dumps({"color": {"ink": {"$value": "#000000"}}}),
        encoding="utf-8",
    )
    return brand


def _clear(monkeypatch=None):
    """Clear module-level warned set and measure caches."""
    bb._warned_font_fallback.clear()
    measure.clear_caches()


@pytest.fixture(autouse=True)
def _reset_state():
    """Ensure the warned set and measure caches are clean before each test."""
    _clear()
    yield
    _clear()


def test_none_face_returns_true_no_warn(tmp_path, capsys):
    brand = _brand(tmp_path)
    result = bb.font_fallback_resolvable(brand, None, detail="test")
    assert result is True
    assert capsys.readouterr().err == ""


def test_resolvable_face_returns_true(tmp_path):
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable")
    brand = _brand(tmp_path)
    result = bb.font_fallback_resolvable(brand, "DejaVu Sans", detail="test")
    assert result is True


def test_unresolvable_face_returns_false_and_warns(tmp_path, capsys, monkeypatch):
    """An unresolvable face returns False and emits a WARN."""
    monkeypatch.setenv("FEINSCHMIEDE_NO_REAL_METRICS", "1")
    measure.clear_caches()
    brand = _brand(tmp_path)
    result = bb.font_fallback_resolvable(brand, "NoSuchFace ZZZ", detail="fallback to generic.")
    assert result is False
    err = capsys.readouterr().err
    assert "diagram-font-fallback" in err
    assert "NoSuchFace ZZZ" in err
    assert "fallback to generic." in err


def test_unresolvable_face_warns_only_once(tmp_path, capsys, monkeypatch):
    """Second call for the same (brand, face) produces no additional warning."""
    monkeypatch.setenv("FEINSCHMIEDE_NO_REAL_METRICS", "1")
    measure.clear_caches()
    brand = _brand(tmp_path)
    bb.font_fallback_resolvable(brand, "NoSuchFace ZZZ", detail="first call")
    capsys.readouterr()  # discard first warning
    bb.font_fallback_resolvable(brand, "NoSuchFace ZZZ", detail="second call")
    err = capsys.readouterr().err
    assert err == ""
