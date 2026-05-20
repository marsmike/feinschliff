"""`feinschliff verify …` — pre-flight layout validator.

Runs `lib.layout_validator.validate_deck` over a `.pptx` file and prints a
human-readable report. Exits 0 if clean, 1 if any text-overlap or
out-of-bounds defects are found. Useful in CI: gate a deck before
shipping it out, without needing a PNG render + human eyeball.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

from pptx import Presentation

from lib.layout_validator import validate_deck, format_defects
from lib.verify.chrome import scan_pp_chrome, scan_chrome_drift


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "deck",
        type=Path,
        help="Path to a .pptx file to validate",
    )
    parser.add_argument(
        "--ignore-out-of-bounds",
        action="store_true",
        help="Don't fail on out-of-bounds shapes (e.g. intentional bleed)",
    )
    parser.add_argument(
        "--ignore-overlap",
        action="store_true",
        help="Don't fail on text-overlap (use when intentional design overlaps "
             "are the norm — strips the corresponding defects from the exit "
             "code, but still prints them)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print on defects; no 'clean' line when everything passes",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report instead of the human format",
    )
    parser.set_defaults(func=cmd_verify)


def cmd_verify(args) -> int:
    deck_path: Path = args.deck
    if not deck_path.is_file():
        print(f"verify: deck not found: {deck_path}", file=sys.stderr)
        return 2

    try:
        prs = Presentation(str(deck_path))
    except Exception as exc:
        print(f"verify: failed to open {deck_path}: {exc}", file=sys.stderr)
        return 2

    defects = validate_deck(prs)
    # Layer 1 deterministic chrome defects (drop-shadow / gradient-fill /
    # fat-outline) plus deck-level chrome-drift (logo/footer positions
    # across slides).
    for d in scan_pp_chrome(prs) + scan_chrome_drift(prs):
        defects.setdefault(d.slide_index, []).append(d)

    # Apply ignore filters (do this after collection so user still sees them).
    fail_kinds = {
        "text-overlap", "out-of-bounds",
        "drop-shadow", "gradient-fill", "fat-outline", "chrome-drift",
    }
    if args.ignore_overlap:
        fail_kinds.discard("text-overlap")
    if args.ignore_out_of_bounds:
        fail_kinds.discard("out-of-bounds")

    failing = {
        idx: [d for d in ds if d.kind in fail_kinds]
        for idx, ds in defects.items()
    }
    failing = {idx: ds for idx, ds in failing.items() if ds}

    if args.json:
        payload = {
            "deck":  str(deck_path),
            "slides": prs.slides.__len__(),
            "defects": {
                str(idx): [_defect_to_dict(d) for d in ds]
                for idx, ds in defects.items()
            },
            "failing_slides": sorted(failing.keys()),
            "status": "fail" if failing else "pass",
        }
        print(json.dumps(payload, indent=2))
    else:
        report = format_defects(defects)
        if defects:
            print(report)
        elif not args.quiet:
            print(report)

    return 1 if failing else 0


def _defect_to_dict(d) -> dict:
    if is_dataclass(d):
        return asdict(d)
    if hasattr(d, "__dict__"):
        return {k: v for k, v in d.__dict__.items() if not k.startswith("_")}
    return {"repr": repr(d)}
