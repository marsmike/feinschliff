#!/usr/bin/env python3
"""Plateau detector — flag layouts whose `struct_diff_ratio` has stopped
moving across recent `brand_visual_diff` runs.

Reads `<output-dir>/score-trace.jsonl` (one JSONL row per verify run)
and reports the per-layout swing over the last N runs. Layouts whose
swing is below `--threshold` are flagged as plateaued — candidates for
redirection per `skills/compile/references/techniques/plateau-categories.md`.

Usage:
  python scripts/brand_plateau.py \
      --output-dir out/verify \
      --window 3 \
      --threshold 0.005
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _category(score: float) -> str:
    if score < 0.05:
        return "clean"
    if score < 0.15:
        return "fine-tuning"
    if score < 0.30:
        return "structural"
    return "rewrite"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", type=Path, required=True,
                   help="Same --output-dir passed to brand_visual_diff")
    p.add_argument("--window", type=int, default=3,
                   help="Number of recent runs to check for movement")
    p.add_argument("--threshold", type=float, default=0.005,
                   help="Min struct_diff_ratio swing (absolute) to count as movement")
    p.add_argument("--min-score", type=float, default=0.05,
                   help="Layouts cleaner than this aren't reported as plateaued")
    args = p.parse_args()

    trace = args.output_dir / "score-trace.jsonl"
    if not trace.is_file():
        print(f"no trace at {trace}")
        return 1
    # Tolerate a truncated/garbled tail line (e.g. a run killed mid-append)
    # instead of crashing the whole tool.
    runs = []
    for ln in trace.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            runs.append(json.loads(ln))
        except json.JSONDecodeError:
            print("warning: skipping malformed score-trace line", file=sys.stderr)
    if len(runs) < 2:
        print(f"need ≥2 runs in trace; have {len(runs)}")
        return 0

    # `--window 0` would make `runs[-0:]` == all history; clamp to ≥1.
    win = max(1, args.window)
    print(f"checking last {win} run(s) per layout for plateau "
          f"(swing < {args.threshold*100:.1f}% = plateau)")
    print(f"{'layout':<28}{'current':>9}{'swing':>9}  category")
    print("-" * 65)

    layouts = sorted(set().union(*(r.get("scores", {}).keys() for r in runs)))
    plateaued: list[tuple[str, float]] = []
    for layout in layouts:
        # The window is the last `win` runs that ACTUALLY MEASURED this layout,
        # not the last `win` global rows. With subset (--only) iteration a
        # layout may appear in only some recent rows; a row-based window would
        # (a) drop a genuinely plateaued layout (len<2) and (b) take a stale
        # value as `current`. Per-layout windowing fixes both.
        layout_rows = [r["scores"][layout] for r in runs
                       if layout in r.get("scores", {})]
        scores = layout_rows[-win:]
        if len(scores) < 2:
            continue
        swing = max(scores) - min(scores)
        current = scores[-1]
        is_plateau = swing < args.threshold
        marker = "PLATEAU" if is_plateau else ""
        print(f"{layout:<28}{current*100:>8.2f}%{swing*100:>8.2f}%  "
              f"{_category(current)} {marker}")
        if is_plateau and current > args.min_score:
            plateaued.append((layout, current))

    if plateaued:
        print(f"\n{len(plateaued)} layout(s) plateaued above {args.min_score*100:.0f}% — "
              f"see skills/compile/references/techniques/plateau-categories.md "
              f"for the redirection playbook")
        for layout, score in sorted(plateaued, key=lambda x: -x[1]):
            print(f"  {layout:<28}{score*100:>6.2f}%   ({_category(score)})")
    else:
        print("\nno plateaus detected — iteration is still moving the score")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
