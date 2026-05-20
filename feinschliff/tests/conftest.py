import sys
from pathlib import Path

# Plugin root (contains pyproject.toml, feinschliff/, brands/, layouts/, ...)
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
# Preserve REPO_ROOT alias for test files that use it
REPO_ROOT = PLUGIN_ROOT

# Extra brands directory (feinschliff-extra plugin, co-installed alongside core)
_EXTRA_BRANDS = PLUGIN_ROOT.parent / "feinschliff-extra" / "brands"

sys.path.insert(0, str(PLUGIN_ROOT))
