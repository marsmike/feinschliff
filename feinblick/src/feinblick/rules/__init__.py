"""Native-rules orchestration — the ``pooled findings -> verdict-ready`` stage.

:func:`run_rules` is the single entry the orchestrator calls after the engine
adapters have produced their findings. It:

1. runs the **native checks** that don't require an external engine, gated by
   the selected ``domains`` (``check_skills`` for ``"skills"``,
   ``check_repo_discipline`` for ``"code"``),
2. **dedupes** the engine + native findings (severity reconciled, sources
   merged) via :func:`feinblick.rules.normalize.dedupe`, and
3. **synthesizes a health score** over the deduped set via
   :func:`feinblick.rules.health.compute_health`.

Returns ``(merged_findings, health)``.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from feinblick.config import Config
from feinblick.model import Finding
from feinblick.rules.health import compute_health
from feinblick.rules.normalize import dedupe
from feinblick.rules.repo_discipline import check_repo_discipline
from feinblick.rules.skills import check_skills


def run_rules(
    findings: list[Finding],
    repo_root: Path,
    config: Config,
    domains: Collection[str],
    file_metrics: dict[str, float] | None = None,
) -> tuple[list[Finding], dict]:
    """Append native checks, dedupe, and compute health for ``findings``.

    ``domains`` selects which native checks run (``"skills"`` -> ``check_skills``,
    ``"code"`` -> ``check_repo_discipline``). ``file_metrics`` (repo-relative
    path -> avg cyclomatic complexity) feeds the health complexity term.
    """
    extra: list[Finding] = []
    if "skills" in domains:
        extra += check_skills(repo_root, config.skills.roots, config)
    if "code" in domains:
        extra += check_repo_discipline(repo_root)

    merged = dedupe(findings + extra)
    health = compute_health(merged, file_metrics)
    return merged, health


__all__ = ["run_rules"]
