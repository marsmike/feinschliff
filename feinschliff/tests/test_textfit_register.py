"""Brand packs register proprietary-font width ratios via tokens `font-metrics`.

Keeps client font names out of the toolkit source: the table ships generic
entries only, and a pack that uses its own corporate face declares the
measured ratios in its (often local-only) tokens.json.
"""
from __future__ import annotations

from feinschliff.pipeline import _register_brand_font_metrics
from feinschliff.textfit import chars_per_line, register_font_metrics, supported_fonts


class _FakeTokens:
    def __init__(self, raw):
        self.raw = raw


def test_register_font_metrics_extends_table():
    register_font_metrics("Test Narrow Sans", normal=0.40, bold=0.44)
    assert "Test Narrow Sans" in supported_fonts()
    # narrower ratio → more chars per line than the 0.52 default
    assert chars_per_line("Test Narrow Sans", 18, False, 914400) > chars_per_line(
        "Unknown Font", 18, False, 914400
    )


def test_pipeline_registers_from_tokens_block():
    tokens = _FakeTokens(
        {"font-metrics": {
            "$description": "skipped",
            "Pack Corporate Face": {"normal": 0.47, "bold": 0.51},
            "broken": {"normal": "x"},
        }}
    )
    _register_brand_font_metrics(tokens)
    assert "Pack Corporate Face" in supported_fonts()
    assert "$description" not in supported_fonts()
    assert "broken" not in supported_fonts()


def test_no_block_is_a_noop():
    _register_brand_font_metrics(_FakeTokens({}))
    _register_brand_font_metrics(_FakeTokens({"font-metrics": "not-a-dict"}))
