"""Fixture module with a deliberately dead function and an unused import.

Used only by the feinblick integration test as a tiny "dirty repo". The unused
import and the never-called helper below are the KNOWN issues a real CytoScnPy
run would flag; the integration test asserts the *normalized* findings via a
stubbed engine, but the source is real so a network smoke run finds them too.
"""

import os  # noqa: F401  (deliberately unused — a known dead import)


def used_function(value: int) -> int:
    """Reachable from the package __init__ — not dead."""
    return value * 2


def dead_alpha_function() -> str:
    """Never referenced anywhere in the fixture — known dead code."""
    return "nobody calls me"
