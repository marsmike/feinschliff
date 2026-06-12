#!/usr/bin/env python3
"""Batch visual verifier for a brand pack vs. its source slide deck.

Thin CLI wrapper. The scorer itself lives in
`feinschliff_builder.verify.visual_diff` (importable — the verify-loop
orchestrator calls it in-process); this script only parses arguments and
forwards. See that module's docstring for the metrics and artefacts.

Usage:
  python scripts/brand_visual_diff.py \
      --brand-pack brands/<brand> \
      --source-dir <source-png-dir> \
      --render-dir out/png \
      --output-dir out/verify

`verify-map.yaml` schema (in brand pack root):
  layouts:
    cover-dark: 1
    quote: 11
    …
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
from feinschliff_builder.verify.visual_diff import run_visual_diff


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--brand-pack", type=Path, required=True,
                   help="Brand pack root (contains verify-map.yaml + layouts/)")
    p.add_argument("--source-dir", type=Path, required=True,
                   help="Directory with slide-NN.png exports from the source deck")
    p.add_argument("--render-dir", type=Path, required=True,
                   help="Directory with <layout>.png renders of the brand pack")
    p.add_argument("--output-dir", type=Path, required=True,
                   help="Where to write overlay/mask images + report.json + score trace")
    p.add_argument("--only", nargs="*",
                   help="Restrict to a subset of layouts (by name). Keeps the "
                        "report and score-trace consistent when an orchestrator "
                        "is iterating on a subset of verify-map.yaml.")
    p.add_argument("--loupe", action="store_true",
                   help="Emit a per-layout loupe PDF (top-N connected-component "
                        "diff hotspots, each cropped + scaled). Use when the "
                        "redline shows residual mismatches that are too small "
                        "to diagnose at slide scale. Writes loupe-hotspots.pdf "
                        "in --output-dir.")
    p.add_argument("--loupe-top-n", type=int, default=4,
                   help="Hotspots per layout in the loupe view (default: 4).")
    p.add_argument("--loupe-min-area", type=int, default=500,
                   help="Minimum connected-component area (px) to count as a "
                        "hotspot. Filters out single-pixel AA noise. Default: 500.")
    args = p.parse_args()
    return run_visual_diff(
        args.brand_pack, args.source_dir, args.render_dir, args.output_dir,
        only=args.only, loupe=args.loupe, loupe_top_n=args.loupe_top_n,
        loupe_min_area=args.loupe_min_area,
    )


if __name__ == "__main__":
    raise SystemExit(main())
