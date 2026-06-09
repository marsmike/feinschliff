"""feinbild command-line interface.

Subcommands:
  imagine                       — generate an AI image (Replicate / Gemini)
  svg expand|render             — .svg.dsl -> .svg (brand-resolved) -> .png
  excalidraw expand|render      — .exc.dsl -> .excalidraw (brand-resolved) -> .png

This CLI is feinbild's only public surface; other plugins call it as a bare
command. Diagram subcommands shell into the feinschmiede engine; `expand` takes
--brand, `render` does not (render is brand-agnostic). Theme stays in the DSL.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__, diagrams_cli, images
from .env import load_home_env


def _cmd_imagine(args: argparse.Namespace) -> int:
    if not args.prompt:
        print("Error: 'prompt' is required.", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else None
    keys = {k: os.environ.get(k) for k in ("REPLICATE_API_KEY", "GEMINI_API_KEY")}
    try:
        path = images.generate(prompt=args.prompt, provider=args.provider, model=args.model,
                               aspect_ratio=args.aspect_ratio, out_path=out, api_keys=keys)
    except images.ImagineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    size = path.stat().st_size
    print(f"Generated: {path} ({size} bytes)")
    print(f"Provider: {args.provider} | Model: {args.model or images.default_model(args.provider)}")
    return 0


def _cmd_svg(args: argparse.Namespace) -> int:
    out = Path(args.out) if args.out else None
    if args.sub == "expand":
        return diagrams_cli.cmd_svg_expand(Path(args.input), out, args.brand)
    return diagrams_cli.cmd_render(Path(args.input), out)


def _cmd_excalidraw(args: argparse.Namespace) -> int:
    out = Path(args.out) if args.out else None
    if args.sub == "expand":
        return diagrams_cli.cmd_excalidraw_expand(Path(args.input), out, args.brand)
    return diagrams_cli.cmd_render(Path(args.input), out)


def _add_diagram_group(sub, name: str, dsl_help: str, expanded_help: str) -> None:
    g = sub.add_parser(name, help=f"{name} diagrams: expand a DSL then render to PNG.")
    leaf = g.add_subparsers(dest="sub", required=True)
    e = leaf.add_parser("expand", help=f"Expand {dsl_help} to {expanded_help} (resolves brand colors).")
    e.add_argument("input")
    e.add_argument("-o", "--out", dest="out")
    e.add_argument("--brand", help="Brand override (else @brand directive / FEINSCHLIFF_BRAND / default).")
    r = leaf.add_parser("render", help=f"Render {expanded_help} to PNG.")
    r.add_argument("input")
    r.add_argument("-o", "--out", dest="out")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="feinbild", description="Image / 2D CLI (feinschmiede / feinbild).")
    parser.add_argument("--version", action="version", version=f"feinbild {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    im = sub.add_parser("imagine", help="Generate an AI image.")
    im.add_argument("--prompt", required=True)
    # No argparse choices: an unknown provider must reach images.generate so it
    # raises ImagineError (clean exit 1), matching imagine.sh's dispatch error.
    im.add_argument("--provider", default="replicate")
    im.add_argument("--model", default=None)
    im.add_argument("--aspect-ratio", dest="aspect_ratio", default="1:1")
    im.add_argument("-o", "--out", dest="out")
    im.set_defaults(func=_cmd_imagine)

    _add_diagram_group(sub, "svg", ".svg.dsl", ".svg")
    _add_diagram_group(sub, "excalidraw", ".exc.dsl", ".excalidraw")
    sub.choices["svg"].set_defaults(func=_cmd_svg)
    sub.choices["excalidraw"].set_defaults(func=_cmd_excalidraw)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_home_env()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
