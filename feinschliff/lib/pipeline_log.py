"""Append-only event/timing log for the deck pipeline.

Two writers append to the same `timing.jsonl` in the deck's working dir:

  1. The Python CLI (`feinschliff deck build`, `verify-aspect`, etc.) wraps
     each phase with :class:`TimedPhase` and emits a row with exact
     `perf_counter` elapsed-ms.
  2. The skill-orchestrator AI emits transition markers via
     ``feinschliff deck log-event <phase> {start|end} --dir <deck-dir>``.

Each line is one JSON object:

  {"t": "2026-05-15T15:32:18.456+00:00",
   "phase": "step:2-plan",
   "status": "end",
   "elapsed_ms": 191234,
   "slide": 7,             # optional, set by build instrumentation
   "agent": "narrative",   # optional, set by parallel-verify aspects
   "note": "..."}

`summarize()` returns per-phase aggregates and a wall-clock estimate that
accounts for parallel phases (start/end pairs that overlap are credited
to a single wall-clock window).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def log_event(
    deck_dir: str | Path,
    phase: str,
    status: str,
    *,
    elapsed_ms: int | None = None,
    **extra: Any,
) -> dict:
    """Append one event row to `<deck_dir>/timing.jsonl`. Always succeeds —
    the timing log is best-effort and never raises on write failure (the
    pipeline must not abort because logging is unavailable).
    """
    rec: dict[str, Any] = {"t": _now_iso(), "phase": phase, "status": status}
    if elapsed_ms is not None:
        rec["elapsed_ms"] = int(elapsed_ms)
    rec.update({k: v for k, v in extra.items() if v is not None})
    path = Path(deck_dir) / "timing.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
    except OSError:
        # Best-effort. The deck must not fail because the log is unwritable.
        pass
    return rec


class TimedPhase:
    """Context manager that emits `start` and `end` events for a phase, with
    perf-counter-accurate `elapsed_ms` on the end event.

    Usage::

        from lib.pipeline_log import TimedPhase
        with TimedPhase(deck_dir, "build:slide", slide=i, layout="kpi-grid"):
            compile_slide(...)
    """

    def __init__(self, deck_dir: str | Path, phase: str, **extra: Any) -> None:
        self.deck_dir = deck_dir
        self.phase = phase
        self.extra = extra
        self._t0: float | None = None

    def __enter__(self) -> TimedPhase:
        self._t0 = time.perf_counter()
        log_event(self.deck_dir, self.phase, "start", **self.extra)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        elapsed_ms = round((time.perf_counter() - (self._t0 or 0)) * 1000)
        status = "end" if exc_type is None else "fail"
        extra = dict(self.extra)
        if exc is not None:
            extra["error"] = str(exc)[:200]
        log_event(self.deck_dir, self.phase, status, elapsed_ms=elapsed_ms, **extra)
        return False  # never swallow exceptions


def read_events(deck_dir: str | Path) -> list[dict]:
    """Read all events from `<deck_dir>/timing.jsonl`. Empty list on missing
    file. Malformed lines are skipped silently — the log is append-only and
    a partial write at the end is the only realistic corruption mode."""
    path = Path(deck_dir) / "timing.jsonl"
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def summarize(events: list[dict]) -> dict:
    """Aggregate events into per-phase stats + wall-clock estimate.

    For each phase we collect all `elapsed_ms` values from `end` (and
    `fail`) events; counts, totals, min/max/avg are reported.

    Wall-clock is approximated by parsing the ISO timestamps on the first
    `start` and last terminal event; this is the actual elapsed window.
    """
    by_phase: dict[str, list[int]] = {}
    starts: list[str] = []
    ends: list[str] = []
    for e in events:
        st = e.get("status")
        ph = e.get("phase", "?")
        if st == "start":
            starts.append(e.get("t", ""))
        elif st in ("end", "fail") and "elapsed_ms" in e:
            by_phase.setdefault(ph, []).append(int(e["elapsed_ms"]))
            ends.append(e.get("t", ""))

    def _avg(xs: list[int]) -> int:
        return sum(xs) // len(xs) if xs else 0

    phases = {
        ph: {
            "count": len(xs),
            "total_ms": sum(xs),
            "avg_ms": _avg(xs),
            "min_ms": min(xs) if xs else 0,
            "max_ms": max(xs) if xs else 0,
        }
        for ph, xs in sorted(by_phase.items())
    }

    wall_ms = 0
    if starts and ends:
        try:
            t0 = datetime.fromisoformat(min(starts))
            t1 = datetime.fromisoformat(max(ends))
            wall_ms = int((t1 - t0).total_seconds() * 1000)
        except ValueError:
            wall_ms = 0

    # Sum of all phase totals — useful to estimate parallelism speedup
    # (wall_ms < cpu_ms means phases overlapped in real time).
    cpu_ms = sum(p["total_ms"] for p in phases.values())

    return {
        "wall_ms": wall_ms,
        "cpu_ms": cpu_ms,
        "speedup": (cpu_ms / wall_ms) if wall_ms > 0 else 1.0,
        "phases": phases,
        "event_count": len(events),
    }


def _fmt_duration(ms: int) -> str:
    """Render milliseconds as `M:SS.S` (or `S.Ss` for short ones)."""
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def render_text_report(events: list[dict], summary: dict) -> str:
    """Human-readable Gantt-ish summary suitable for `feinschliff deck timing`."""
    lines: list[str] = []
    wall = summary["wall_ms"]
    cpu = summary["cpu_ms"]
    speedup = summary["speedup"]
    lines.append("Pipeline timing report")
    lines.append("=" * 56)
    lines.append(f"Wall clock:        {_fmt_duration(wall):>10}")
    lines.append(f"Total CPU (Σ):     {_fmt_duration(cpu):>10}")
    lines.append(f"Parallelism:       {speedup:>10.2f}x  (1.0 = serial)")
    lines.append(f"Events:            {summary['event_count']:>10}")
    lines.append("")
    lines.append("Phases (count × avg → total, sorted by total descending):")
    by_total = sorted(
        summary["phases"].items(),
        key=lambda kv: kv[1]["total_ms"],
        reverse=True,
    )
    if not by_total:
        lines.append("  (no completed phases)")
    max_total = by_total[0][1]["total_ms"] if by_total else 1
    for ph, stats in by_total:
        bar_w = round(28 * stats["total_ms"] / max(max_total, 1))
        bar = "▓" * bar_w + "·" * (28 - bar_w)
        pct = (stats["total_ms"] / max(cpu, 1)) * 100
        lines.append(
            f"  {ph:<32s} {bar} "
            f"{stats['count']:>3d}× avg={_fmt_duration(stats['avg_ms']):>7s}  "
            f"Σ={_fmt_duration(stats['total_ms']):>7s} ({pct:4.1f}%)"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "TimedPhase",
    "log_event",
    "read_events",
    "render_text_report",
    "summarize",
]
