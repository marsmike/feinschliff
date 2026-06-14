import sys
from pathlib import Path

# Plugin root (contains pyproject.toml, feinschliff/, brands/, layouts/, ...)
# Tests moved to tests/feinschliff/ — repo root is parents[2], plugin root one level in.
PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
# Preserve REPO_ROOT alias for test files that use it
REPO_ROOT = PLUGIN_ROOT

# Extra brands directory (feinschliff-extra plugin, co-installed alongside core)
_EXTRA_BRANDS = PLUGIN_ROOT.parent / "feinschliff-extra" / "brands"

sys.path.insert(0, str(PLUGIN_ROOT))
# Also add the test directory itself so cross-test imports (e.g. from
# test_emitter_restraint import ...) continue to work after the tests
# moved out of feinschliff/tests/ into the repo-root tests/feinschliff/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
