"""Score already-generated diagram artifacts against an evals.json suite.

The grader is pure and deterministic: it maps each test to its artifact
(``<results_dir>/<test-name>.<ext>``), runs the test's checks, and returns a
report dict with a pooled ``score`` = passed / total. Generation (running the
skill on each prompt) happens in the agent layer, NOT here.
"""

from __future__ import annotations

import json
from pathlib import Path

from feinschliff_builder.eval.checks import CheckContext, run_check

# evals.json "skill" -> generated artifact extension.
_EXT = {"excalidraw": ".excalidraw", "svg": ".svg", "slide-dsl": ".slide.dsl"}


def grade(evals_path: Path, results_dir: Path, brand_dir: Path) -> dict:
    suite = json.loads(evals_path.read_text())
    skill = suite["skill"]
    ext = _EXT[skill]
    ctx = CheckContext(brand_dir=brand_dir)

    tests_out: list[dict] = []
    passed = total = 0
    for test in suite.get("tests", []):
        artifact = results_dir / f"{test['name']}{ext}"
        exists = artifact.is_file()
        checks_out: list[dict] = []
        for chk in test.get("checks", []):
            ok = exists and _safe_check(chk, artifact, ctx)
            checks_out.append({"check": chk, "pass": ok})
            total += 1
            passed += 1 if ok else 0
        tests_out.append({
            "name": test["name"],
            "artifact": str(artifact),
            "exists": exists,
            "checks": checks_out,
            "passed": sum(1 for c in checks_out if c["pass"]),
            "total": len(checks_out),
        })

    return {
        "skill": skill,
        "score": (passed / total) if total else 0.0,
        "passed": passed,
        "total": total,
        "tests": tests_out,
    }


def _safe_check(name: str, artifact: Path, ctx: CheckContext) -> bool:
    # Unknown check names are an authoring error — let the ValueError surface so
    # the CLI boundary can report it cleanly. A malformed artifact, by contrast,
    # must fail the check rather than crash the grade.
    try:
        return run_check(name, artifact, ctx)
    except ValueError:
        raise
    except Exception:
        return False
