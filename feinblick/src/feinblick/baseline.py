"""The gate's memory — accepted-finding baselines by stable fingerprint.

A baseline is a JSON file recording the ``fingerprint`` of every finding the
operator has accepted (``{"fingerprints": [sorted unique]}``). The audit gate
loads it and :func:`classify` splits a fresh finding set into *introduced*
(new, not in the baseline) vs *preexisting* (already accepted) by fingerprint
membership — so the gate fails only on regressions, never on pre-existing debt.
"""

from __future__ import annotations

import json
from pathlib import Path

from feinblick.model import Finding


def save(path: Path, findings: list[Finding]) -> None:
    """Write the sorted, de-duplicated fingerprints of ``findings`` to ``path``.

    Parent directories are created as needed.
    """
    path = Path(path)
    fingerprints = sorted({f.fingerprint for f in findings})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fingerprints": fingerprints}, indent=2) + "\n")


def load(path: Path) -> set[str]:
    """Return the set of accepted fingerprints in ``path`` (empty if missing)."""
    path = Path(path)
    if not path.is_file():
        return set()
    data = json.loads(path.read_text())
    return set(data.get("fingerprints", []))


def classify(
    findings: list[Finding], accepted: set[str]
) -> tuple[list[Finding], list[Finding]]:
    """Split ``findings`` into ``(introduced, preexisting)`` by fingerprint.

    A finding is *preexisting* when its fingerprint is in ``accepted``; every
    other finding is *introduced*. Order within each bucket is preserved.
    """
    introduced: list[Finding] = []
    preexisting: list[Finding] = []
    for f in findings:
        if f.fingerprint in accepted:
            preexisting.append(f)
        else:
            introduced.append(f)
    return introduced, preexisting
