#!/usr/bin/env python3
"""Slotify every decompiled layout in a brand pack: literal text labels →
`{{ text_N | default("literal") }}` slots, so the pack works as a fillable
template while the bare showcase render stays identical (defaults).

Also reports slot coverage per layout: literal text lines that could NOT be
slotified (braces in label) and picture lines without an image slot.

Usage:
  uv run python scripts/slotify_layouts.py --brand-pack <…/brands/<brand>> [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from feinschliff_builder.decompile.slotify import slotify_dsl


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand-pack", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    layouts_dir = args.brand_pack.resolve() / "layouts"
    if not layouts_dir.is_dir():
        sys.exit(f"no layouts/ in {args.brand_pack}")

    total_slots = 0
    unslotified_text = 0
    unslotified_pics = 0
    for path in sorted(layouts_dir.glob("*.slide.dsl")):
        text = path.read_text(encoding="utf-8")
        new_text, slots = slotify_dsl(text)
        leftovers = [ln for ln in new_text.splitlines()
                     if ln.startswith("text ") and '"' in ln and "{{" not in ln]
        bare_pics = [ln for ln in new_text.splitlines()
                     if ln.startswith("picture ") and "{{" not in ln]
        unslotified_text += len(leftovers)
        unslotified_pics += len(bare_pics)
        total_slots += len(slots)
        flag = ""
        if leftovers:
            flag += f"  [{len(leftovers)} text left literal]"
        if bare_pics:
            flag += f"  [{len(bare_pics)} picture without slot]"
        print(f"  {path.name}: {len(slots)} text slots{flag}")
        if not args.dry_run and slots:
            path.write_text(new_text, encoding="utf-8")

    mode = "(dry-run) " if args.dry_run else ""
    print(f"\n{mode}{total_slots} text slots across "
          f"{len(list(layouts_dir.glob('*.slide.dsl')))} layouts; "
          f"{unslotified_text} text lines left literal, "
          f"{unslotified_pics} pictures without slot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
