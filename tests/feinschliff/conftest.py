import sys
from pathlib import Path

# Plugin root (contains pyproject.toml, feinschliff/, brands/, layouts/, ...)
PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
# Preserve REPO_ROOT alias for test files that use it
REPO_ROOT = PLUGIN_ROOT

# Extra brands directory (feinschliff-extra plugin, co-installed alongside core)
_EXTRA_BRANDS = PLUGIN_ROOT.parent / "feinschliff-extra" / "brands"

sys.path.insert(0, str(PLUGIN_ROOT))
# This tests directory itself, so sibling test modules can share helpers
# (e.g. `from test_emitter_restraint import _minimal_tokens`). The workspace
# root must NOT go on sys.path: the package directories (feinschmiede/, ...)
# would shadow the editable installs as namespace packages.
sys.path.append(str(Path(__file__).resolve().parent))
