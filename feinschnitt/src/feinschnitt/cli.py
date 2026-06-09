"""feinschnitt CLI — argparse wiring + clean-error dispatch only (no logic).

Subcommands:
  record   <recipe.toml>        drive a CLI session into an asciicast (recorder.py)
  analyze  <video> [out]        video -> .storyboard.md via Gemini (analyze.py)
"""
from __future__ import annotations

import argparse
import sys

from feinschnitt import __version__, analyze, recorder
from feinschnitt.env import load_home_env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="feinschnitt",
        description="Video tooling for the feinschmiede family.",
    )
    parser.add_argument("--version", action="version",
                        version=f"feinschnitt {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    recorder.add_parser(sub)
    analyze.add_parser(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_home_env()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (recorder.RecorderError, analyze.AnalyzeError,
            FileNotFoundError, OSError, ValueError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
