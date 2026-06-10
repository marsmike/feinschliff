"""`feinschliff-builder eval` — grade generated artifacts against a skill's evals.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from feinschliff_builder.eval.grader import grade

_EPILOG = """\
Grades already-generated diagram artifacts (it never calls an LLM). Artifacts
must be named <test-name>.<ext> (.excalidraw or .svg) — one per test in the
skill's evals/evals.json. Exit code: 0 all checks pass, 1 some fail, 2 bad
evals.json.

Examples:
  # Score a results dir against the excalidraw eval suite
  feinschliff-builder eval feinbild/skills/excalidraw \\
      --results-dir .autoloop/excalidraw/results

  # Machine-readable report to stdout
  feinschliff-builder eval feinbild/skills/svg --results-dir <dir> --json

This is the deterministic scorer behind the `autoloop` skill
(feinschliff-builder/skills/autoloop/).
"""


def register(parser: argparse.ArgumentParser) -> None:
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.epilog = _EPILOG
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
    try:
        report = grade(evals_path, args.results_dir, brand_dir)
    except (ValueError, KeyError) as exc:
        # Bad evals.json (unknown check name or unsupported skill) — surface a
        # clean message, never a traceback, since autoloop runs this unattended.
        print(f"eval: {evals_path}: {exc}", file=sys.stderr)
        return 2

    out = args.out or (args.results_dir / "grades.json")
    out.write_text(json.dumps(report, indent=2))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"eval {report['skill']}: {report['passed']}/{report['total']} checks "
            f"passed (score {report['score']:.3f}) -> {out}"
        )
    # Strict gate: any failed check exits non-zero. The autoloop reads the
    # numeric `score` from grades.json for trend/keep-revert decisions.
    return 0 if report["passed"] == report["total"] else 1
