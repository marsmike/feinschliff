"""`feinschnitt edit` subcommand wiring (no logic — dispatch only)."""
from __future__ import annotations

import json
from pathlib import Path

from feinschnitt.edit import EditError
from feinschnitt.edit import align as alignmod
from feinschnitt.edit import plan as planmod
from feinschnitt.edit import render as rendermod
from feinschnitt.edit import transcribe as transcribemod
from feinschnitt.edit import verify as verifymod
from feinschnitt.edit.lint import lint_beats
from feinschnitt.edit.workdir import workdir_for

__all__ = ["add_parser"]


def _cmd_workdir(args) -> int:
    print(workdir_for(args.video))
    return 0


def _cmd_transcribe(args) -> int:
    if not args.video.exists():
        raise EditError(f"video not found: {args.video}")
    out = transcribemod.run(args.video, model_size=args.model)
    print(out)
    return 0


def _cmd_lint(args) -> int:
    plan = planmod.load_plan(args.plan)
    duration = rendermod.ffprobe_meta(args.video)["duration"]
    errors, warnings = lint_beats(plan["beats"], duration)
    for w in warnings:
        print(f"warning: {w}")
    if errors:
        raise EditError("plan lint failed:\n  " + "\n  ".join(errors))
    print(f"lint OK — {len(plan['beats'])} beats, {len(warnings)} warning(s)")
    return 0


def _cmd_align(args) -> int:
    plan = planmod.load_plan(args.plan)
    wd = workdir_for(args.video)
    words_path = transcribemod.run(args.video)
    aligned = alignmod.run(plan, words_path, wd / "edit_plan.aligned.json")
    print(json.dumps(aligned, indent=2))
    return 0


def _cmd_render(args) -> int:
    if not args.plan.exists():
        raise EditError(f"plan not found: {args.plan}")
    out = rendermod.render(args.video, args.plan, quality=args.quality,
                           brand_dir=args.brand, force=args.force)
    verifymod.run(args.video, out)
    print(out)
    return 0


def _cmd_verify(args) -> int:
    verifymod.run(args.video, args.output)
    return 0


def add_parser(sub) -> None:
    p = sub.add_parser("edit", help="edit a pre-recorded video "
                                    "(plan-driven Remotion engine)")
    es = p.add_subparsers(dest="edit_command", required=True)

    sp = es.add_parser("workdir", help="print the per-video cache workdir")
    sp.add_argument("video", type=Path)
    sp.set_defaults(func=_cmd_workdir)

    sp = es.add_parser("transcribe", help="word-timestamped transcript → words.json")
    sp.add_argument("video", type=Path)
    sp.add_argument("--model", default="small")
    sp.set_defaults(func=_cmd_transcribe)

    sp = es.add_parser("lint", help="deterministic plan checks (no render)")
    sp.add_argument("video", type=Path)
    sp.add_argument("plan", type=Path)
    sp.set_defaults(func=_cmd_lint)

    sp = es.add_parser("align", help="snap beats to spoken words (transcribes first if needed)")
    sp.add_argument("video", type=Path)
    sp.add_argument("plan", type=Path)
    sp.set_defaults(func=_cmd_align)

    sp = es.add_parser("render", help="lint + align + render + verify")
    sp.add_argument("video", type=Path)
    sp.add_argument("plan", type=Path)
    # No argparse `choices` on purpose: argparse would exit(2) with its own
    # message; rendermod.render raises EditError so the clean-error contract
    # holds (rc 1, 'Error:' prefix, no traceback).
    sp.add_argument("--quality", default="preview")
    sp.add_argument("--brand", type=Path, default=None,
                    help="brand pack dir containing tokens.json")
    sp.add_argument("--force", action="store_true",
                    help="ignore the render fingerprint cache")
    sp.set_defaults(func=_cmd_render)

    sp = es.add_parser("verify", help="re-check an existing output")
    sp.add_argument("video", type=Path)
    sp.add_argument("output", type=Path)
    sp.set_defaults(func=_cmd_verify)
