"""Top-level CLI entry. Dispatches to subcommands."""
from __future__ import annotations

import argparse
import sys

from cli import brand as brand_cmd
from cli import build as build_cmd
from cli import compile as compile_cmd
from cli import deck as deck_cmd
from cli import decompile as decompile_cmd
from cli import verify as verify_cmd
from cli import verify_diagram as verify_diagram_cmd
from cli import verify_quality as verify_quality_cmd
from cli import ship as ship_cmd


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="feinschliff")
    sub = p.add_subparsers(dest="command", required=True)

    brand_parser = sub.add_parser("brand", help="Brand pack management")
    brand_cmd.register(brand_parser)

    build_parser_cmd = sub.add_parser(
        "build",
        help="Expand a .slide.dsl into a .pptx via the DSL pipeline",
    )
    build_cmd.register(build_parser_cmd)

    compile_parser = sub.add_parser(
        "compile-html",
        help="Parse a claude-design HTML and emit .slide.dsl skeletons",
    )
    compile_cmd.register(compile_parser)

    deck_parser = sub.add_parser(
        "deck",
        help="Multi-slide deck composer + layout picker",
    )
    deck_cmd.register(deck_parser)

    decompile_parser = sub.add_parser(
        "decompile",
        help="Inverse of build: .pptx → per-slide .slide.dsl files",
    )
    decompile_cmd.register(decompile_parser)

    verify_parser = sub.add_parser(
        "verify",
        help="Run layout validator against a .pptx (overlap + out-of-bounds)",
    )
    verify_cmd.register(verify_parser)

    verify_diagram_parser = sub.add_parser(
        "verify-diagram",
        help="Structural lint for an .svg or .excalidraw file",
    )
    verify_diagram_cmd.register(verify_diagram_parser)

    verify_quality_parser = sub.add_parser(
        "verify-quality",
        help="LLM rubric verify with PNG render + report",
    )
    verify_quality_cmd.register(verify_quality_parser)

    ship_parser = sub.add_parser(
        "ship",
        help="One-command build + verify + verify-quality with a single verdict",
    )
    ship_cmd.register(ship_parser)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
