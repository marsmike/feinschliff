"""feinschliff/tests/test_units_drift.py

Conversion constants must come from feinschmiede.geometry.units — a locally
re-defined 6350/12700/0.5 in a consumer module is exactly the budget/emitter
drift that shipped silent overflow (same pattern as gen_launchers --check).
"""
import re
from pathlib import Path

_PKG = Path(__file__).resolve().parent.parent / "feinschliff"

# module path -> regexes that must NOT match (locally-defined conversion constants)
_FORBIDDEN = {
    _PKG / "slot_budget.py": [r"=\s*6350(\.0)?\b", r"(?:_PX_TO_PT|px_to_pt)\s*[:=][^#\n]*?\b0\.5\b", r"/\s*12700(\.0)?\b"],
    # NOTE: the `fitted_pt * 2.0` autoshrink pattern is added in Task 5, where
    # its behavior fix + test live — keep this list constants-only for now.
    _PKG / "dsl" / "pptx_emit.py": [r"=\s*12_?192_?000\b", r"EMU_PER_PT\s*=\s*12700\b"],
    _PKG / "textfit.py": [r"_EMU_PER_PT\s*=\s*12700\b"],
}

_REQUIRED_IMPORT = re.compile(r"from feinschmiede\.geometry(\.units)? import|import feinschmiede\.geometry")


def test_no_local_conversion_constants():
    offenders = []
    for path, patterns in _FORBIDDEN.items():
        text = path.read_text(encoding="utf-8")
        for pat in patterns:
            for m in re.finditer(pat, text):
                line_no = text[: m.start()].count("\n") + 1
                offenders.append(f"{path.name}:{line_no}: {m.group(0)!r}")
    assert not offenders, (
        "locally-defined conversion constants (use feinschmiede.geometry.units):\n"
        + "\n".join(offenders)
    )


def test_consumers_import_units():
    for path in _FORBIDDEN:
        assert _REQUIRED_IMPORT.search(path.read_text(encoding="utf-8")), (
            f"{path.name} must import feinschmiede.geometry.units"
        )
