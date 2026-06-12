"""brand_bridge.resolve_fonts — brand typography for the diagram pipeline."""
import json
from pathlib import Path

from feinschmiede.diagrams.brand_bridge import resolve_fonts

_TOKENS = {
    "color": {"ink": {"$value": "#000000"}},
    "font-family": {
        "display": {"$value": ["Spectral", "Georgia", "serif"]},
        "body": {"$value": ["Noto Sans", "Helvetica Neue", "Arial", "sans-serif"]},
        "mono": {"$value": ["Noto Sans Mono", "ui-monospace", "Menlo", "monospace"]},
    },
}


def _brand(tmp_path: Path, tokens: dict) -> Path:
    brand = tmp_path / "brandx"
    brand.mkdir()
    (brand / "tokens.json").write_text(json.dumps(tokens), encoding="utf-8")
    return brand


def test_resolve_fonts_reads_body_and_mono(tmp_path):
    fonts = resolve_fonts(_brand(tmp_path, _TOKENS))
    assert fonts.body[0] == "Noto Sans"
    assert fonts.mono[0] == "Noto Sans Mono"


def test_svg_stacks_quote_multiword_and_end_generic(tmp_path):
    fonts = resolve_fonts(_brand(tmp_path, _TOKENS))
    assert fonts.svg_body == "'Noto Sans', 'Helvetica Neue', Arial, sans-serif"
    assert fonts.svg_mono == "'Noto Sans Mono', Menlo, monospace"


def test_primary_faces_skip_generics(tmp_path):
    fonts = resolve_fonts(_brand(tmp_path, _TOKENS))
    assert fonts.primary_body == "Noto Sans"
    assert fonts.primary_mono == "Noto Sans Mono"


def test_body_falls_back_to_display(tmp_path):
    tokens = {"color": {"ink": {"$value": "#000"}},
              "font-family": {"display": {"$value": ["Spectral", "serif"]}}}
    fonts = resolve_fonts(_brand(tmp_path, tokens))
    assert fonts.body[0] == "Spectral"
    assert fonts.svg_mono == "monospace"
    assert fonts.primary_mono is None


def test_missing_font_family_yields_generic_only(tmp_path):
    fonts = resolve_fonts(_brand(tmp_path, {"color": {"ink": {"$value": "#000"}}}))
    assert fonts.svg_body == "sans-serif"
    assert fonts.svg_mono == "monospace"
    assert fonts.primary_body is None


def test_plain_list_values_supported(tmp_path):
    tokens = {"font-family": {"body": ["Open Sans", "sans-serif"]}}
    fonts = resolve_fonts(_brand(tmp_path, tokens))
    assert fonts.body[0] == "Open Sans"


def test_missing_tokens_json_degrades(tmp_path):
    brand = tmp_path / "nobrand"
    brand.mkdir()
    fonts = resolve_fonts(brand)
    assert fonts.svg_body == "sans-serif"


def test_repo_brand_resolves():
    brand = Path(__file__).resolve().parent.parent.parent / "feinschliff" / "brands" / "feinschliff"
    if not (brand / "tokens.json").exists():
        import pytest
        pytest.skip("repo brand not present")
    assert resolve_fonts(brand).body[0] == "Noto Sans"
