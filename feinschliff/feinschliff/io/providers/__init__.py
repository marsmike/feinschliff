"""Built-in image providers.

Importing this package triggers registration of every bundled provider
into :data:`lib.io.image_provider._REGISTRY`. Discovery only needs to
``from lib import providers`` (which it does) to surface every built-in
without scanning the bundled directory file-by-file.

Out-of-tree providers live under
``~/.claude/plugins/.../feinschliff_providers/`` and are loaded by
:func:`lib.io.image_provider.discover_providers` via the normal file-scan
mechanism.
"""
from __future__ import annotations

from feinschliff.io.providers import unsplash  # noqa: F401 — side-effect import

__all__ = ["unsplash"]
