"""0-100 repo-health synthesis from pooled findings (+ optional file metrics).

A single headline number for "how healthy is this surface right now". The v1
formula is deliberately simple, documented, and *tunable* — every weight is a
named module constant so calibration against real feinschliff modules (spec
§13.4) is a config tweak, not a rewrite.

Formula (start at 100, floor at 0, round to int)::

    score = 100
          - W_ERROR   * #errors
          - W_WARNING * #warnings
          - W_INFO    * #infos
          - W_COMPLEXITY * max(0, avg_cyclomatic - COMPLEXITY_THRESHOLD)

``avg_cyclomatic`` is the mean of ``file_metrics`` values (per-file average
cyclomatic complexity); the term only bites once the project average crosses
:data:`COMPLEXITY_THRESHOLD`.

``hotspots`` are the top-:data:`HOTSPOT_LIMIT` files ranked by finding count,
breaking ties by complexity (from ``file_metrics``), each ``{"path", "findings"}``.
"""

from __future__ import annotations

from collections import Counter

from feinblick.model import Finding, Severity

#: Per-finding score penalties (tunable; calibration follow-up in spec §13.4).
W_ERROR = 4.0
W_WARNING = 1.5
W_INFO = 0.25

#: Penalty per unit of average cyclomatic complexity above the threshold.
W_COMPLEXITY = 0.5
#: Average cyclomatic complexity below which no complexity penalty applies.
COMPLEXITY_THRESHOLD = 10.0

#: Maximum number of hotspot files reported.
HOTSPOT_LIMIT = 5


def compute_health(
    findings: list[Finding],
    file_metrics: dict[str, float] | None = None,
) -> dict:
    """Synthesize a 0-100 health score plus the top finding hotspots.

    ``file_metrics`` maps repo-relative path -> average cyclomatic complexity.
    Returns ``{"score": int, "hotspots": [{"path": str, "findings": int}, ...]}``.
    """
    score = 100.0
    score -= W_ERROR * _count(findings, Severity.ERROR)
    score -= W_WARNING * _count(findings, Severity.WARNING)
    score -= W_INFO * _count(findings, Severity.INFO)
    score -= _complexity_penalty(file_metrics)

    score = max(0.0, score)
    return {
        "score": round(score),
        "hotspots": _hotspots(findings, file_metrics or {}),
    }


def _count(findings: list[Finding], severity: Severity) -> int:
    return sum(1 for f in findings if f.severity == severity)


def _complexity_penalty(file_metrics: dict[str, float] | None) -> float:
    if not file_metrics:
        return 0.0
    values = list(file_metrics.values())
    avg = sum(values) / len(values)
    return W_COMPLEXITY * max(0.0, avg - COMPLEXITY_THRESHOLD)


def _hotspots(findings: list[Finding], file_metrics: dict[str, float]) -> list[dict]:
    counts: Counter[str] = Counter(f.location.path for f in findings)
    if not counts:
        return []
    ranked = sorted(
        counts.items(),
        key=lambda item: (item[1], file_metrics.get(item[0], 0.0), item[0]),
        reverse=True,
    )
    return [
        {"path": path, "findings": n}
        for path, n in ranked[:HOTSPOT_LIMIT]
    ]
