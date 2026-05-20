import sys
from pathlib import Path

# Builder plugin root (contains pyproject.toml, feinschliff_builder/, tests/, ...)
BUILDER_ROOT = Path(__file__).resolve().parents[1]
# Core plugin root (sibling directory)
CORE_ROOT = BUILDER_ROOT.parent / "feinschliff"
# Extra brands directory (feinschliff-extra plugin, co-installed alongside)
EXTRA_BRANDS = BUILDER_ROOT.parent / "feinschliff-extra" / "brands"

# Make sure both plugins are importable
sys.path.insert(0, str(BUILDER_ROOT))
sys.path.insert(0, str(CORE_ROOT))
