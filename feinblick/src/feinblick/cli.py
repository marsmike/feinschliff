"""feinblick CLI entry point. Full subcommand dispatch lands in Task 12."""

from __future__ import annotations

import argparse
import sys

from feinblick import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="feinblick", description="Codebase intelligence: Python + Claude skills."
    )
    p.add_argument("--version", action="version", version=f"feinblick {__version__}")
    p.set_defaults(_handler=None)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
