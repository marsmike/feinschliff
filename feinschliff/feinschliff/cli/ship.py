"""`feinschliff ship` — one command, three gates, one verdict.

  feinschliff ship <plan.yaml> -o OUT [--llm] [--json]

Runs:
  1. feinschliff deck build (compile_slide pipeline; fatal-defect policy)
  2. feinschliff verify (Layer 1/2 deterministic checks)
  3. feinschliff verify-quality (LLM rubric; offline unless --llm)

Returns 0 only if every gate runs and passes; 2 if the build passes but the
verify gates were skipped (feinschliff-builder not installed). Writes
ship_report.{json,md} alongside the deck.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("plan", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--llm", action="store_true",
                        help="Run the LLM rubric live. Default: --offline.")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Emit JSON-only on stdout instead of human progress.")
    parser.add_argument("--examples-out", type=Path, default=None,
                        help="On pass, mirror polished artifacts into this dir: "
                             "deck.pdf, deck.pptx, thumbnails/slide-N.png. "
                             "Replaces the manual examples-mirror step.")
    parser.set_defaults(func=cmd_ship)


def _tool(name: str, *args: str) -> list[str]:
    # Prefer `uv run <tool>` in a dev checkout; fall back to the bare console
    # script on PATH (real plugin install) so ship does not hard-require uv.
    if shutil.which("uv"):
        return ["uv", "run", name, *args]
    return [name, *args]


def _run(argv: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    import os
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, encoding="utf-8", env=env)
    except FileNotFoundError as exc:
        # The executable (uv or the tool) is not on PATH — surface as rc 127 so
        # the caller's availability heuristic skips the gate instead of crashing.
        return 127, "", str(exc)
    return p.returncode, p.stdout, p.stderr


def cmd_ship(args) -> int:
    out_deck: Path = args.output.resolve()
    out_dir = out_deck.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "plan": str(args.plan),
        "deck": str(out_deck),
        "gates": {},
    }

    # Gate 1: build
    rc, stdout, stderr = _run(_tool(
        "feinschliff", "deck", "build", str(args.plan), "-o", str(out_deck),
    ))
    report["gates"]["build"] = {
        "status": "pass" if rc == 0 else "fail",
        "stdout": stdout, "stderr": stderr,
    }
    if rc != 0:
        return _finalize(report, out_dir, verdict="fail", code=rc, json_out=args.json_out)

    # Gate 2: verify (provided by feinschliff-builder; skip if not installed)
    rc, stdout, stderr = _run(_tool(
        "feinschliff-builder", "verify", str(out_deck),
    ))
    _builder_unavailable = (rc != 0 and (
        "No such command" in stderr or "Could not find" in stderr
        or "unrecognized arguments" in stderr or rc == 127
        or "ModuleNotFoundError" in stderr or "No module named" in stderr
    ))
    if _builder_unavailable:
        # builder not installed — skip gate gracefully
        report["gates"]["verify"] = {"status": "skipped"}
    else:
        report["gates"]["verify"] = {
            "status": "pass" if rc == 0 else "fail",
            "stdout": stdout, "stderr": stderr,
        }
        if rc != 0:
            return _finalize(report, out_dir, verdict="fail", code=rc, json_out=args.json_out)

    # Gate 3: verify-quality (provided by feinschliff-builder; skip if not installed)
    quality_json = out_dir / "verify_report.json"
    cmd = _tool(
        "feinschliff-builder", "verify-quality", str(out_deck),
        "--rubric", "squint,title-body",
        "--json", "--out", str(quality_json),
    )
    if not args.llm:
        cmd.append("--offline")
    rc, stdout, stderr = _run(cmd)
    _quality_unavailable = (rc != 0 and (
        "No such command" in stderr or "Could not find" in stderr
        or "unrecognized arguments" in stderr or rc == 127
        or "ModuleNotFoundError" in stderr or "No module named" in stderr
    ))
    if _quality_unavailable:
        # builder not installed — skip gate gracefully
        report["gates"]["verify-quality"] = {"status": "skipped"}
    else:
        qr = json.loads(quality_json.read_text(encoding="utf-8")) if quality_json.exists() else {"verdict": "fail"}
        gate_status = "pass" if qr.get("verdict") in {"pass", "skipped-llm"} else "fail"
        report["gates"]["verify-quality"] = {
            "status": gate_status,
            "verdict": qr.get("verdict"),
        }
        if gate_status == "fail":
            return _finalize(report, out_dir, verdict="fail", code=1, json_out=args.json_out)

    skipped = [g for g, p in report["gates"].items() if p.get("status") == "skipped"]
    if skipped:
        # Build passed but quality gates could not run (feinschliff-builder not
        # installed). Do NOT report a clean pass and do NOT mirror unverified
        # output to examples; exit non-zero so automation treats it as not-green.
        report["unverified_gates"] = skipped
        return _finalize(report, out_dir, verdict="incomplete", code=2, json_out=args.json_out)

    if args.examples_out is not None:
        _mirror_to_examples(out_deck, out_dir, args.examples_out)
        report["examples_out"] = str(args.examples_out)

    return _finalize(report, out_dir, verdict="pass", code=0, json_out=args.json_out)


def _mirror_to_examples(pptx: Path, out_dir: Path, dst: Path) -> None:
    """Copy the user-facing artifacts (pptx, pdf, thumbnails) into dst.

    Source layout produced by ship:
      out_dir/deck.pptx
      out_dir/deck.pngs/deck.pdf
      out_dir/deck.pngs/slide-*.png

    Destination layout (examples discipline):
      dst/deck.pptx
      dst/deck.pdf
      dst/thumbnails/slide-*.png
    """
    dst.mkdir(parents=True, exist_ok=True)
    thumbs_dst = dst / "thumbnails"
    thumbs_dst.mkdir(exist_ok=True)
    pngs_src = out_dir / f"{pptx.stem}.pngs"

    shutil.copy2(pptx, dst / pptx.name)
    pdf = pngs_src / f"{pptx.stem}.pdf"
    if pdf.exists():
        shutil.copy2(pdf, dst / f"{pptx.stem}.pdf")

    for old in thumbs_dst.glob("slide-*.png"):
        old.unlink()
    for png in sorted(pngs_src.glob("slide-*.png")):
        shutil.copy2(png, thumbs_dst / png.name)


def _finalize(report: dict, out_dir: Path, *, verdict: str, code: int, json_out: bool) -> int:
    report["verdict"] = verdict
    (out_dir / "ship_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "ship_report.md").write_text(_render_md(report), encoding="utf-8")
    if json_out:
        print(json.dumps(report, indent=2))
    else:
        print(f"ship: verdict={verdict} (report: {out_dir / 'ship_report.md'})")
    return code


def _render_md(report: dict) -> str:
    lines = [
        f"# Ship Report — {report['deck']}",
        "",
        f"**Verdict:** {report['verdict']}",
        "",
    ]
    for gate, payload in report["gates"].items():
        lines.append(f"## {gate}")
        lines.append("")
        lines.append(f"Status: **{payload['status']}**")
        if "verdict" in payload:
            lines.append(f"Verdict: {payload['verdict']}")
        lines.append("")
    return "\n".join(lines) + "\n"
