"""`feinschliff verify-diagram` — structural lint for a single diagram file.

Runs the deterministic checks in `lib/diagrams/structural_validator.py`
against an `.svg` or `.excalidraw` file and reports defects. Exits 0 if
no FATAL defects, 1 otherwise. WARN-level findings (e.g. arrow crossings)
print but don't fail.

Useful for ad-hoc authoring: render a diagram, then `feinschliff
verify-diagram out/diagram.excalidraw` before shipping it into a slide.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from feinschliff.defects import Severity, format_defect
from feinschliff_builder.diagrams.structural_validator import validate_diagram_file


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "path",
        type=Path,
        help="Path to an .svg or .excalidraw file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report instead of human format",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the 'clean' message when no defects are found",
    )
    parser.set_defaults(func=cmd_verify_diagram)


def cmd_verify_diagram(args) -> int:
    path: Path = args.path
    if not path.is_file():
        print(f"verify-diagram: file not found: {path}", file=sys.stderr)
        return 2
    if path.suffix.lower() not in (".svg", ".excalidraw"):
        print(
            f"verify-diagram: unsupported extension {path.suffix!r} "
            f"(expected .svg or .excalidraw)",
            file=sys.stderr,
        )
        return 2

    try:
        defects = validate_diagram_file(path)
    except Exception as exc:
        print(f"verify-diagram: {exc}", file=sys.stderr)
        return 2

    fatal = [d for d in defects if d.severity == Severity.FATAL]

    if args.json:
        payload = {
            "path": str(path),
            "defects": [d.to_dict() for d in defects],
            "fatal_count": len(fatal),
            "warn_count": sum(1 for d in defects if d.severity == Severity.WARN),
            "status": "fail" if fatal else "pass",
        }
        print(json.dumps(payload, indent=2))
    else:
        if defects:
            for d in defects:
                print(format_defect(d))
        elif not args.quiet:
            print(f"verify-diagram: {path.name} · clean (no structural defects)")

    return 1 if fatal else 0
