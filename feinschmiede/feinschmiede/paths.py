"""Filesystem locations of resources bundled inside the engine package.

``compounds_dir()`` is the single source of truth for the std compounds
(``kpi-cell``, ``card``, …). Callers that pass ``std_dir=`` to a compound
loader must use it instead of re-deriving the path from their own
``__file__`` — package layouts differ, so per-caller guesses silently
point at nonexistent directories and the std compounds get skipped.
"""
from __future__ import annotations

from pathlib import Path


def compounds_dir() -> Path:
    """Return the std compounds/ directory shipped inside the engine."""
    return Path(__file__).resolve().parent / "compounds"
