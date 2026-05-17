"""Perceptual-hash diff between two brand-preview trees.

Walks `current` (default: docs/brand-previews/) and `previous`
(default: /tmp/brand-previews-prev/), computes phash distance per
matched PNG, and reports:

  - Missing (in previous but not current): renders that disappeared.
  - New (in current but not previous): renders that appeared.
  - Changed: phash distance >= --threshold (default 6).
  - Unchanged: phash distance < --threshold.

Use this as a lightweight, dependency-free replacement for the
LLM-rating verification pipeline (Gemma 400s) — phash catches layout,
color, and structural regressions without external API calls.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import imagehash
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
DEFAULT_CURRENT = REPO / "docs" / "brand-previews"
DEFAULT_PREVIOUS = Path("/tmp/brand-previews-prev")


def _phash(p: Path) -> imagehash.ImageHash:
    with Image.open(p) as im:
        return imagehash.phash(im.convert("RGB"))


def _walk(root: Path) -> dict[str, Path]:
    """Map 'brand/file.png' → absolute path."""
    out: dict[str, Path] = {}
    for png in root.rglob("*.png"):
        rel = png.relative_to(root).as_posix()
        out[rel] = png
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    ap.add_argument("--previous", type=Path, default=DEFAULT_PREVIOUS)
    ap.add_argument("--threshold", type=int, default=6,
                    help="phash distance >= threshold counts as Changed (default: 6)")
    ap.add_argument("--json", type=Path, default=None,
                    help="Write structured report to this path")
    args = ap.parse_args()

    if not args.current.is_dir():
        print(f"current dir missing: {args.current}", file=sys.stderr)
        return 2
    if not args.previous.is_dir():
        print(f"previous dir missing: {args.previous}", file=sys.stderr)
        return 2

    cur = _walk(args.current)
    prev = _walk(args.previous)

    keys_cur, keys_prev = set(cur), set(prev)
    missing = sorted(keys_prev - keys_cur)
    new = sorted(keys_cur - keys_prev)
    common = sorted(keys_cur & keys_prev)

    changed: list[tuple[str, int]] = []
    unchanged: list[tuple[str, int]] = []
    errors: list[tuple[str, str]] = []
    for rel in common:
        try:
            d = int(_phash(cur[rel]) - _phash(prev[rel]))
        except Exception as exc:
            errors.append((rel, str(exc)))
            continue
        if d >= args.threshold:
            changed.append((rel, d))
        else:
            unchanged.append((rel, d))
    changed.sort(key=lambda t: -t[1])

    print(f"diff_brand_previews: threshold={args.threshold}")
    print(f"  unchanged: {len(unchanged)}")
    print(f"  changed:   {len(changed)}")
    print(f"  new:       {len(new)}")
    print(f"  missing:   {len(missing)}")
    if errors:
        print(f"  errors:    {len(errors)}")

    if changed:
        print("\nChanged (phash distance):")
        for rel, d in changed:
            print(f"  {d:>3}  {rel}")
    if new:
        print("\nNew (only in current):")
        for rel in new:
            print(f"       {rel}")
    if missing:
        print("\nMissing (only in previous):")
        for rel in missing:
            print(f"       {rel}")
    if errors:
        print("\nErrors:")
        for rel, msg in errors:
            print(f"  {rel}: {msg}")

    if args.json:
        args.json.write_text(json.dumps({
            "threshold": args.threshold,
            "changed": [{"file": r, "distance": d} for r, d in changed],
            "unchanged": [{"file": r, "distance": d} for r, d in unchanged],
            "new": new,
            "missing": missing,
            "errors": [{"file": r, "message": m} for r, m in errors],
        }, indent=2) + "\n")

    return 1 if changed or missing or errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
