#!/usr/bin/env python3
"""Bulk decompile every layout in a brand's verify-map.yaml from a source PPTX.

Reads `<brand>/verify-map.yaml`, then for each `<layout-name>: <slide-no>`
pair calls the hybrid PPTX+SVG decompiler
(`lib.dsl.pptx_svg_decompile.derive`) and writes
`<brand>/layouts/<layout-name>.slide.dsl`. Existing layout files are
snapshotted into `<brand>/layouts.bak/` before being overwritten.

Use this as the first step of brand bootstrapping when you have a
multi-slide source PPTX that maps 1:1 to your intended layout pool:

    1. Author `<brand>/tokens.json` (extends a parent brand + adds palette)
    2. Author `<brand>/verify-map.yaml` mapping layout names to slide numbers
    3. Run this script → first-pass DSLs land in `<brand>/layouts/`
    4. Run `scripts/brand_verify_loop.py` → see how close the first pass is
    5. Use the `improve-brand` skill to drive each layout to ≤5% struct_diff

Usage:
  uv run python scripts/brand_decompile_all.py \\
      --brand-pack brands/<brand> \\
      --source-pptx path/to/source-deck.pptx

  uv run python scripts/brand_decompile_all.py \\
      --brand-pack brands/<brand> \\
      --source-pptx path/to/source-deck.pptx \\
      --only quote table cover-orange --dry-run
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from lib.dsl.pptx_svg_decompile import derive


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand-pack", required=True, type=Path,
                    help="Brand pack root (must contain verify-map.yaml and tokens.json)")
    ap.add_argument("--source-pptx", required=True, type=Path,
                    help="Source PPTX deck to decompile")
    ap.add_argument("--canvas", default="1920x1080",
                    help="Target DSL canvas size (default: 1920x1080)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the layouts that would be derived, don't write")
    ap.add_argument("--only", nargs="*",
                    help="Restrict to a subset of layout names")
    ap.add_argument("--carry-images", action="store_true",
                    help="Pipeline-optimization mode: extract every <p:pic> "
                         "binary from the source slide into "
                         "<brand-pack>/assets/decompile/<layout>/imageN.<ext> "
                         "and emit DSL `default:` paths pointing at those, so "
                         "the verify loop renders the real picture (not a "
                         "placeholder) and struct_diff_ratio reflects shape/"
                         "text mismatch only, not picture-region noise.")
    args = ap.parse_args()

    brand_pack: Path = args.brand_pack.resolve()
    if not brand_pack.is_dir():
        sys.exit(f"brand pack not found: {brand_pack}")
    verify_map = brand_pack / "verify-map.yaml"
    if not verify_map.is_file():
        sys.exit(f"missing verify-map.yaml in {brand_pack}")
    source_pptx: Path = args.source_pptx.resolve()
    if not source_pptx.is_file():
        sys.exit(f"source pptx not found: {source_pptx}")

    tokens_path = brand_pack / "tokens.json"
    brand_name = brand_pack.name
    canvas_w, canvas_h = (int(x) for x in args.canvas.split("x"))

    mapping = yaml.safe_load(verify_map.read_text(encoding="utf-8"))["layouts"]
    requested = set(args.only) if args.only else None

    layouts_dir = brand_pack / "layouts"
    backup_dir = brand_pack / "layouts.bak"
    if not args.dry_run:
        layouts_dir.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

    derived = 0
    for layout_name, slide_no in mapping.items():
        if requested is not None and layout_name not in requested:
            continue
        target = layouts_dir / f"{layout_name}.slide.dsl"
        if args.dry_run:
            print(f"  would derive {layout_name} ← p{slide_no} → {target}")
            continue
        if target.exists():
            shutil.copy2(target, backup_dir / target.name)
        image_extract_dir = None
        image_extract_rel = None
        if args.carry_images:
            # The build resolves picture paths against `<brand>/assets` as
            # the asset root (see cli/build.py:asset_root), so the DSL
            # `default:` carries the relative path WITHOUT the `assets/`
            # prefix. Filesystem path includes it.
            image_extract_dir = brand_pack / "assets" / "decompile" / layout_name
            image_extract_rel = f"decompile/{layout_name}"
        dsl = derive(
            source_pptx,
            slide_idx=slide_no,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            tokens_path=tokens_path if tokens_path.exists() else None,
            layout_name=layout_name,
            theme_name=brand_name,
            image_extract_dir=image_extract_dir,
            image_extract_rel=image_extract_rel,
        )
        target.write_text(dsl, encoding="utf-8")
        size = target.stat().st_size
        print(f"  ✓ {layout_name} ← p{slide_no} ({size} bytes)")
        derived += 1

    print(f"\nderived {derived} layouts" if not args.dry_run
          else f"(dry-run: {derived} layouts planned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
