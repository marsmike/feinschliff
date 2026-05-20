"""Top-level CLI entry. Dispatches to subcommands."""
from __future__ import annotations

import argparse
import sys

from feinschliff.cli import build as build_cmd
from feinschliff.cli import deck as deck_cmd
from feinschliff.cli import ship as ship_cmd


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="feinschliff")
    sub = p.add_subparsers(dest="command", required=True)

    build_parser_cmd = sub.add_parser(
        "build",
        help="Expand a .slide.dsl into a .pptx via the DSL pipeline",
    )
    build_cmd.register(build_parser_cmd)

    deck_parser = sub.add_parser(
        "deck",
        help="Multi-slide deck composer + layout picker",
    )
    deck_cmd.register(deck_parser)

    ship_parser = sub.add_parser(
        "ship",
        help="One-command build + verify + verify-quality with a single verdict",
    )
    ship_cmd.register(ship_parser)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = args.func(args)
    return 0 if rc is None else int(rc)


if __name__ == "__main__":
    sys.exit(main())
