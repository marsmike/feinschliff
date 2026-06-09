"""Engine imports standalone (no feinschliff) and the public surface resolves."""

import importlib


def test_engine_imports_without_feinschliff():
    for mod in [
        "feinschmiede",
        "feinschmiede.diagrams.svg_expand",
        "feinschmiede.diagrams.excalidraw_expand",
        "feinschmiede.diagrams.render",
        "feinschmiede.diagrams.brand_bridge",
        "feinschmiede.brand_discovery",
        "feinschmiede.dsl.ast",
        "feinschmiede.dsl.tokens",
    ]:
        importlib.import_module(mod)


def test_no_feinschliff_import_in_engine_source():
    # Only IMPORT statements are forbidden — the engine legitimately keeps
    # `feinschliff` string literals (default brand name, the Excalidraw
    # `"source": "feinschliff"` field, the FEINSCHLIFF_BRAND* env vars).
    import pathlib
    import re

    pat = re.compile(r"^\s*(from|import)\s+feinschliff\b", re.MULTILINE)
    root = pathlib.Path(__file__).resolve().parents[1] / "feinschmiede"
    offenders = [
        str(p.relative_to(root))
        for p in root.rglob("*.py")
        if pat.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"engine imports feinschliff: {offenders}"
