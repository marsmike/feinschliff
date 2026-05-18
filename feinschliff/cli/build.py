"""`feinschliff build` — DSL pipeline: layout + brand + content → .pptx.

  feinschliff build <layout.slide.dsl> --brand <id> [--content YAML] [--var k=v]... -o OUT.pptx

The layout file is parsed; the content YAML provides slot values; the
brand pack's tokens + compounds are loaded; the full graph is expanded
to primitives; the emitter writes a .pptx.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from lib.dsl.parser import parse_file
from lib.dsl.tokens import load_tokens
from lib.dsl.expander import load_compounds_for_brand
from lib.dsl.pptx_emit import build_presentation
from lib.content_validator import validate_content, emit_defects_and_abort_message
from lib.slot_budget import compute_slot_budgets
from lib.pipeline import compile_slide
from lib.defects import fatal_kinds, format_defect
from lib.image_provider import discover_providers, get_provider


REPO_ROOT = Path(__file__).resolve().parents[1]
STD_COMPOUNDS = REPO_ROOT / "compounds"
BRANDS_DIR = REPO_ROOT / "brands"


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("layout", help="Path to a .slide.dsl file")
    parser.add_argument("--brand", required=True, help="Brand id (dir name under brands/)")
    parser.add_argument("--content", help="YAML file with slot values")
    parser.add_argument("--var", action="append", help="Override a single slot: --var key=value")
    parser.add_argument("-o", "--output", required=True, help="Output .pptx path")
    parser.add_argument(
        "--skip-content-lint",
        action="store_true",
        help="Skip pre-render content lints (title-length, action-verb-leading). "
             "For emergency overrides only.",
    )
    parser.add_argument(
        "--allow-diagram-warnings",
        action="store_true",
        help="Ship even when diagram-overflow or diagram-text-too-small "
             "defects surface. Otherwise these are fatal by default.",
    )
    parser.add_argument(
        "--allow-missing-assets",
        action="store_true",
        help="Ship even when a picture slot points at a missing file or is "
             "unset. Default: fatal. Mark intentionally-empty slots with "
             "`optional:true` to skip the abort without this flag.",
    )
    parser.set_defaults(func=cmd_build)


def cmd_build(args) -> int:
    from lib.brand_discovery import find_brand

    layout_path = Path(args.layout).resolve()
    try:
        brand = find_brand(args.brand)
    except ValueError as e:
        print(f"feinschliff: {e}", file=sys.stderr)
        return 2
    brand_dir = brand.root

    # Resolve build-time image provider from `$image_provider` in the
    # brand's tokens.json (extends-resolved by `discover_brands`). Absent
    # → provider is None and any `picture query:` raises a loud DSLError
    # inside the emitter; brands that only use `picture path:` build as
    # before. `get_provider` raises KeyError with a registry listing on a
    # typo'd kind, which surfaces as the normal CLI traceback.
    discover_providers()
    provider = None
    if brand.image_provider_config:
        cfg = brand.image_provider_config
        provider = get_provider(cfg["kind"], cfg.get("config"))

    tokens = load_tokens(brand_dir, brands_dir=BRANDS_DIR)
    compounds = load_compounds_for_brand(
        brand_dir, std_dir=STD_COMPOUNDS, brands_dir=BRANDS_DIR
    )

    layout_nodes, layout_compounds = parse_file(layout_path)
    for cd in layout_compounds:
        compounds[cd.name] = cd

    ctx = {}
    if args.content:
        ctx = yaml.safe_load(Path(args.content).read_text()) or {}
    for kv in (args.var or []):
        if "=" not in kv:
            print(f"feinschliff: --var expects key=value, got '{kv}'", file=sys.stderr)
            return 2
        k, _, v = kv.partition("=")
        ctx[k.strip()] = v

    if not args.skip_content_lint:
        # Strip `.slide.dsl` (and any leading path) to get the bare layout
        # name (e.g. "executive-summary") — this is what the structural
        # validators key on.
        layout_name = layout_path.name
        if layout_name.endswith(".slide.dsl"):
            layout_name = layout_name[: -len(".slide.dsl")]
        slot_budgets = compute_slot_budgets(layout_nodes, tokens, compounds=compounds)
        content_defects = validate_content(
            ctx, slide_index=1, layout=layout_name, slot_budgets=slot_budgets,
        )
        if content_defects:
            emit_defects_and_abort_message({1: content_defects}, cli_name="build")
            return 1

    result = compile_slide(
        layout_path=layout_path,
        ctx=ctx,
        brand_dir=brand_dir,
        slide_index=1,
        diagrams_out_dir=Path(args.output).resolve().parent / "diagrams",
    )

    allowed_to_skip: set[str] = set()
    if args.allow_diagram_warnings:
        allowed_to_skip |= {"diagram-overflow", "diagram-text-too-small"}

    blocking = [
        d for d in result.defects
        if d.kind.value in fatal_kinds() and d.kind.value not in allowed_to_skip
    ]
    for d in result.defects:
        print(f"feinschliff build: {format_defect(d)}", file=sys.stderr)
    if blocking:
        print(
            f"feinschliff build: aborting — {len(blocking)} fatal defect(s). "
            f"Pass --allow-diagram-warnings to demote "
            f"diagram-overflow/diagram-text-too-small (if those are the only blockers).",
            file=sys.stderr,
        )
        return 1

    primitives = result.primitives
    tokens = result.tokens

    asset_root = brand_dir / "assets"
    asset_root_fallback = REPO_ROOT / "assets"
    out_path = Path(args.output).resolve()
    prs = build_presentation(
        primitives, tokens,
        asset_root=asset_root,
        asset_root_fallback=asset_root_fallback,
        image_provider=provider,
        deck_dir=out_path.parent,
    )
    missing = getattr(prs, "missing_assets", []) or []
    if missing and not getattr(args, "allow_missing_assets", False):
        for entry in missing:
            kind = entry.get("kind", "missing")
            path = entry.get("path") or "(unset)"
            line = entry.get("line_no", "?")
            print(
                f"feinschliff build: missing asset ({kind}) at "
                f"line {line}: {path}",
                file=sys.stderr,
            )
        print(
            f"feinschliff build: aborting — {len(missing)} missing required "
            f"asset(s). Mark optional slots with `optional:true` or pass "
            f"--allow-missing-assets to ship anyway.",
            file=sys.stderr,
        )
        return 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    print(f"wrote {out_path} ({len(prs.slides)} slide, "
          f"{len(primitives)} primitives expanded from "
          f"{len(layout_nodes)} layout nodes)")
    return 0
