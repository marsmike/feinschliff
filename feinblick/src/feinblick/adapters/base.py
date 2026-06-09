"""Engine adapter protocol + shared value types.

Each adapter shells out to a real engine (``cytoscnpy``/``tach``/``agnix``) via
the :class:`~feinblick.runner.Runner` and parses the engine's native output into
a list of :class:`~feinblick.model.Finding`. The :class:`Engine` protocol is the
contract the orchestrator drives; :class:`Targets` bundles the inputs an adapter
needs (repo root, scan roots, test globs, and the resolved config).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from feinblick.model import Finding
from feinblick.runner import RawOutput, Runner

__all__ = ["Engine", "Targets", "RawOutput", "Runner"]


@dataclass(frozen=True)
class Targets:
    repo_root: Path
    roots: list[str]  # code or skill roots, repo-relative
    test_globs: list[str]
    config: object  # feinblick.config.Config (typed as object to avoid an import cycle)


class Engine(Protocol):
    name: str

    def ensure_available(self, runner: Runner, version: str) -> tuple[bool, str]:
        """Probe runtime availability; return ``(ok, reason)``."""
        ...

    def run(self, runner: Runner, targets: Targets, version: str) -> RawOutput:
        """Invoke the engine and return its raw stdout/stderr/exit code."""
        ...

    def parse(self, raw: RawOutput, targets: Targets) -> list[Finding]:
        """Parse the engine's raw output into normalized findings."""
        ...
