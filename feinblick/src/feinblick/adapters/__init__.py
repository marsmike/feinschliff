"""Lazy adapter registry.

Each adapter module (``cytoscnpy``/``tach``/``agnix``) exposes a module-level
``ENGINE = <Engine>()``. We import them lazily so a not-yet-implemented adapter
simply doesn't register — no shared-file edits required as adapters land, and an
absent optional adapter degrades cleanly instead of breaking the import.
"""

import importlib

ENGINES = {}
for _name in ("cytoscnpy", "tach", "agnix"):
    try:
        _mod = importlib.import_module(f"feinblick.adapters.{_name}")
    except ImportError:
        continue
    _eng = getattr(_mod, "ENGINE", None)
    if _eng is not None:
        ENGINES[_name] = _eng
