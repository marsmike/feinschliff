"""Regression: validate_svg_structure must run on stdlib alone (no lxml).

The validator used to `from lxml import etree` inside its parse try/except,
so in the standalone plugin venv (where nothing declares lxml) every SVG
verify came back ERROR "svg parse failed: No module named 'lxml'".
"""

import sys

from feinschmiede.diagnostics import DefectKind
from feinschmiede.diagrams.structural_validator import validate_svg_structure

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100" '
    'width="200" height="100">'
    '<rect x="10" y="10" width="80" height="40" fill="#1a73e8"/>'
    '<text x="20" y="80" fill="#202124">brand label</text>'
    "</svg>"
)


def test_valid_svg_has_no_invalid_file_defect():
    defects = validate_svg_structure(_SVG)
    assert not any(d.kind == DefectKind.DIAGRAM_INVALID_FILE for d in defects)
    assert defects == []


def test_validator_runs_without_lxml(monkeypatch):
    # None in sys.modules makes any `import lxml` raise ImportError, so this
    # passes only if the validator no longer touches lxml at all.
    monkeypatch.setitem(sys.modules, "lxml", None)
    monkeypatch.setitem(sys.modules, "lxml.etree", None)
    off_canvas = _SVG.replace('x="10"', 'x="500"')
    defects = validate_svg_structure(off_canvas)
    assert not any(d.kind == DefectKind.DIAGRAM_INVALID_FILE for d in defects)
    assert any(d.kind == DefectKind.DIAGRAM_OVERFLOW for d in defects)
