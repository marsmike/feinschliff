"""Repo-discipline rule — encodes the CLAUDE.md examples-folder allowlist.

Under ``feinschliff/examples/``, only rendered artifacts and a small set of
markdown files are allowed; every other file is a forbidden intermediate that
belongs under ``feinschliff/.debug/``. v1 implements only this examples
allowlist (stale-suppression detection is deferred), named so scope stays
honest.
"""

from __future__ import annotations

from pathlib import Path

from feinblick.model import (
    Action,
    Category,
    Domain,
    Finding,
    Location,
    Severity,
)

#: Examples subtree the allowlist governs (repo-relative).
_EXAMPLES_DIR = "feinschliff/examples"

#: File extensions permitted anywhere under the examples subtree.
_ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".png"}

#: Exact basenames permitted anywhere under the examples subtree.
_ALLOWED_BASENAMES = {"README.md", "ATTRIBUTION.md"}


def check_repo_discipline(repo_root: Path) -> list[Finding]:
    """Flag forbidden intermediates under ``feinschliff/examples/``.

    Returns one ``REPO_DISCIPLINE`` error per file whose extension is not in
    the allowlist and whose basename is not exempt. No examples dir -> ``[]``.
    """
    repo_root = Path(repo_root)
    examples = repo_root / _EXAMPLES_DIR
    if not examples.is_dir():
        return []

    findings: list[Finding] = []
    for path in sorted(examples.rglob("*")):
        if not path.is_file():
            continue
        if path.name in _ALLOWED_BASENAMES:
            continue
        if path.suffix in _ALLOWED_EXTENSIONS:
            continue
        rel = path.relative_to(repo_root).as_posix()
        ext = path.suffix or path.name
        findings.append(
            Finding(
                domain=Domain.CODE,
                category=Category.REPO_DISCIPLINE,
                severity=Severity.ERROR,
                location=Location(path=rel),
                message=(
                    f"Forbidden file in {_EXAMPLES_DIR}/: '{rel}' "
                    "(only .pdf/.pptx/.png + README.md/ATTRIBUTION.md allowed)"
                ),
                source_engine="feinblick:rules",
                rule_id="FB-REPO-EX001",
                evidence=f"forbidden extension '{ext}'",
                actions=[
                    Action(
                        "Move intermediate to feinschliff/.debug/",
                        auto_fixable=False,
                    )
                ],
            )
        )
    return findings
