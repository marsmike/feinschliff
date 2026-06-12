from pathlib import Path

# Builder plugin root (contains pyproject.toml, feinschliff_builder/, scripts/, ...)
BUILDER_ROOT = Path(__file__).resolve().parents[2] / "feinschliff-builder"
# Core plugin root (sibling directory)
CORE_ROOT = BUILDER_ROOT.parent / "feinschliff"
# Extra brands directory (feinschliff-extra plugin, co-installed alongside)
EXTRA_BRANDS = BUILDER_ROOT.parent / "feinschliff-extra" / "brands"
