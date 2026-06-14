"""Regression test: the built wheel ships every non-.py data file the package
loads at runtime.

The runtime-quality PR shipped JSON schemas + arc YAML files under
feinschliff/intake/, feinschliff/storyline/, feinschliff/storyline/arcs/, and
feinschliff/schemas/. Without `[tool.setuptools.package-data]` in pyproject.toml
the built wheel includes only the .py modules; any CLI subcommand that opens
these files at first use crashes with FileNotFoundError.

This test enumerates the data files in the source tree and asserts that the
package-data globs in pyproject.toml would include each one. The build itself
is exercised separately by the wheel-install CI job; this test prevents the
package-data list from drifting silently when new schemas / YAML fixtures land.
"""
from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "feinschliff"
PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

DATA_SUFFIXES = (".json", ".yaml", ".dsl")


def _all_data_files() -> list[str]:
    """Return paths relative to the package root for every data file."""
    result: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in DATA_SUFFIXES:
            continue
        if "__pycache__" in path.parts:
            continue
        result.append(str(path.relative_to(PACKAGE_ROOT)))
    return result


def _package_data_globs() -> list[str]:
    raw = tomllib.loads(PYPROJECT.read_text())
    table = raw.get("tool", {}).get("setuptools", {}).get("package-data", {})
    return list(table.get("feinschliff", []))


def test_pyproject_declares_package_data():
    globs = _package_data_globs()
    assert globs, (
        "pyproject.toml has no [tool.setuptools.package-data] feinschliff entry. "
        "Without it, the built wheel ships .py files only and schemas/YAML resources "
        "are missing → CLI subcommands crash at first use with FileNotFoundError."
    )


@pytest.mark.parametrize("rel_path", _all_data_files())
def test_every_data_file_is_covered_by_package_data_glob(rel_path: str):
    """Every JSON/YAML/DSL file under feinschliff/ must match at least one glob."""
    globs = _package_data_globs()
    matched = any(fnmatch.fnmatch(rel_path, g) for g in globs)
    assert matched, (
        f"{rel_path!r} is in the source tree but no glob in "
        f"[tool.setuptools.package-data] feinschliff matches it. Add a glob "
        f"covering its directory or the wheel will ship without it. "
        f"Current globs: {globs}"
    )
