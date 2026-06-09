"""Changed-code attribution — restrict findings to the code under review.

For the ``audit --gate introduced`` flow the gate only cares about findings
that touch *changed* code. :func:`changed_paths` asks git for the repo-relative
paths that differ from a reference (committed since the ref, plus staged and
unstaged working-tree edits); :func:`attribute` keeps the findings whose
:class:`~feinblick.model.Location` path is in that set. A pre-computed unified
diff can be fed instead via :func:`parse_diff_file`.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from feinblick.model import Finding

# Captures the repo-relative path from a unified-diff "+++ b/<path>" header,
# excluding the /dev/null target that marks a pure deletion.
_PLUS_HEADER = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def _git_name_only(repo_root: Path, args: list[str]) -> set[str]:
    """Run ``git diff --name-only <args>`` and return its non-empty lines."""
    proc = subprocess.run(
        ["git", "diff", "--name-only", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return set()
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def changed_paths(repo_root: Path, since_ref: str) -> set[str]:
    """Repo-relative paths changed since ``since_ref`` (committed + working tree).

    Unions three git views so nothing in flight is missed:
      * ``git diff --name-only <ref>...HEAD`` — committed since the merge-base,
      * ``git diff --name-only`` — unstaged working-tree edits,
      * ``git diff --name-only --cached`` — staged-but-uncommitted edits.
    """
    repo_root = Path(repo_root)
    paths: set[str] = set()
    paths |= _git_name_only(repo_root, [f"{since_ref}...HEAD"])
    paths |= _git_name_only(repo_root, [])
    paths |= _git_name_only(repo_root, ["--cached"])
    return paths


def attribute(findings: list[Finding], changed: set[str]) -> list[Finding]:
    """Keep findings whose ``location.path`` is in the ``changed`` set."""
    return [f for f in findings if f.location.path in changed]


def parse_diff_file(path: Path) -> set[str]:
    """Extract changed repo-relative paths from a unified diff at ``path``.

    Reads each ``+++ b/<path>`` header; ``+++ /dev/null`` (a deletion) is
    intentionally not matched, so deleted files do not appear.
    """
    text = Path(path).read_text()
    return set(_PLUS_HEADER.findall(text))
