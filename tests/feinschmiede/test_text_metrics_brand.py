"""char_width_em_for — measured brand-face ratio refines the 0.62 heuristic."""
import pytest

from feinschmiede.diagrams.text_metrics import CHAR_WIDTH_EM, char_width_em_for
from feinschmiede.text import measure


def test_no_face_returns_constant():
    assert char_width_em_for(None) == CHAR_WIDTH_EM


def test_kill_switch_returns_constant(monkeypatch):
    monkeypatch.setenv("FEINSCHMIEDE_NO_REAL_METRICS", "1")
    measure.clear_caches()
    assert char_width_em_for("DejaVu Sans") == CHAR_WIDTH_EM
    measure.clear_caches()


def test_resolvable_face_refines():
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable")
    ratio = char_width_em_for("DejaVu Sans")
    assert 0.35 < ratio < 0.85   # sanity band for any real text face
