"""`feinschliff-builder eval` — grade generated artifacts against a skill's evals.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from feinschliff_builder.eval.grader import grade


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "skill_dir", type=Path,
        help="Path to a skill dir containing evals/evals.json",
    )
    parser.add_argument(
        "--results-dir", type=Path, required=True,
        help="Directory of generated artifacts named <test-name>.<ext>",
    )
    parser.add_argument(
        "--brand", type=Path, default=None,
        help="Brand pack dir (default: bundled feinschliff brand)",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Where to write grades.json (default: <results-dir>/grades.json)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Also print the grades JSON to stdout",
    )
    parser.set_defaults(func=cmd_eval)


def _default_brand_dir() -> Path:
    # cli/eval.py -> cli -> feinschliff_builder -> feinschliff-builder -> repo root
    return Path(__file__).resolve().parents[3] / "feinschliff" / "brands" / "feinschliff"


def cmd_eval(args) -> int:
    evals_path = args.skill_dir / "evals" / "evals.json"
    if not evals_path.is_file():
        print(f"eval: no evals.json at {evals_path}", file=sys.stderr)
        return 2

    brand_dir = args.brand or _default_brand_dir()
    report = grade(evals_path, args.results_dir, brand_dir)

    out = args.out or (args.results_dir / "grades.json")
    out.write_text(json.dumps(report, indent=2))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"eval {report['skill']}: {report['passed']}/{report['total']} checks "
            f"passed (score {report['score']:.3f}) -> {out}"
        )
    return 0 if report["passed"] == report["total"] else 1
