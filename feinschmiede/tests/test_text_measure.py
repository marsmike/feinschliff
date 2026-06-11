"""Real-font measurement: resolution via fontconfig, widths via optional PIL."""
import shutil

import pytest

from feinschmiede.text import measure

requires_fc = pytest.mark.skipif(shutil.which("fc-match") is None,
                                 reason="fontconfig not installed")


def _pil_available() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def test_unknown_family_returns_none():
    measure.clear_caches()
    assert measure.find_font_file("No Such Font Family XYZ") is None


@requires_fc
def test_known_family_resolves_when_installed():
    measure.clear_caches()
    p = measure.find_font_file("DejaVu Sans")
    if p is None:
        pytest.skip("DejaVu Sans not installed")
    assert p.is_file()


@requires_fc
def test_line_width_scales_linearly():
    measure.clear_caches()
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not installed")
    if not _pil_available():
        assert measure.line_width_pt("Hamburgefonstiv", "DejaVu Sans", 10) is None
        pytest.skip("PIL unavailable — None path verified")
    w10 = measure.line_width_pt("Hamburgefonstiv", "DejaVu Sans", 10)
    w20 = measure.line_width_pt("Hamburgefonstiv", "DejaVu Sans", 20)
    assert w10 and w20 and abs(w20 - 2 * w10) < 0.01


@requires_fc
def test_avg_char_width_ratio_plausible():
    measure.clear_caches()
    if measure.find_font_file("DejaVu Sans") is None or not _pil_available():
        pytest.skip("DejaVu Sans or PIL unavailable")
    r = measure.avg_char_width_ratio("DejaVu Sans")
    assert 0.3 < r < 0.8          # sane ratio for a text face
    rb = measure.avg_char_width_ratio("DejaVu Sans", bold=True)
    assert rb >= r                 # bold is never narrower


def test_env_kill_switch(monkeypatch):
    monkeypatch.setenv("FEINSCHMIEDE_NO_REAL_METRICS", "1")
    measure.clear_caches()
    assert measure.find_font_file("DejaVu Sans") is None
    monkeypatch.delenv("FEINSCHMIEDE_NO_REAL_METRICS")
    measure.clear_caches()
