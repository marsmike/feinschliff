"""bake_palette.py — produce brand artifacts from a brand's DESIGN.md.

# v1 LEGACY — not part of v2 build. tokens.json is hand-authored in v2.

In v2, `tokens.json` is the source of truth and is hand-authored
(optionally with `extends:` chains in DESIGN.md frontmatter for
inheritance). This script's `from-design-md` mode and template-color
rewriting are obsolete — v2 has no `catalog.json` and no
`templates/pptx/` baked outputs.

Kept as a historical record + for one-off DTCG conversions
(retrofit mode can still be useful for back-filling DESIGN.md from
an existing v1 tokens.json). See `feinschliff/docs/brand-system.md`
for the v2 authoring workflow.

Legacy modes (unchanged):

  retrofit [--brand <name>] [--dry-run]
      Existing brand has tokens.json + templates already. Reverse-extract a
      DESIGN.md (colors → frontmatter, $description → markdown body). Write
      brands/<name>/DESIGN.md. Idempotent.

  from-design-md --brand <new-brand> --base <base-brand>
      New brand. Reads brands/<new-brand>/DESIGN.md + brands/<base>/<…>.
      Produces tokens.json, templates/pptx/*.pptx (color-substituted),
      claude-design/<new>-2026.html, catalog.json. All non-color assets
      come from the base unchanged.

Exit codes: 0 ok, 1 author error (bad DESIGN.md, missing slot, hex
collision), 2 IO error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import warnings
import zipfile
from pathlib import Path

warnings.warn(
    "scripts/bake_palette.py is a v1 legacy tool. In v2, tokens.json "
    "is hand-authored — see feinschliff/docs/brand-system.md.",
    DeprecationWarning,
    stacklevel=2,
)

# Allow running from the feinschliff project root.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from lib.brand_discovery import discover_brands  # noqa: E402
from lib.design_md import DesignMd, parse as parse_design_md  # noqa: E402

# srgbClr context only — non-color val=… attrs (transforms, offsets) must NOT match.
_SRGB_RE = re.compile(rb'<a:srgbClr\s+val="([0-9A-Fa-f]{6})"')

# CSS hex literal in HTML/CSS context (#RRGGBB, NOT a hex digit run inside JS).
_CSS_HEX_RE = re.compile(rb"#([0-9A-Fa-f]{6})\b")


# Stable lex-order canonicalisation for retrofit output. We keep tokens.json's
# slot ordering (insertion-ordered in JSON) so DESIGN.md ↔ tokens.json round-trips
# stay diff-friendly.


def _retrofit_one(brand_name: str, brand_root: Path, tokens: dict) -> str:
    """Produce DESIGN.md text for the brand from its existing tokens.json."""
    color_section = tokens.get("color") or {}
    if not color_section:
        raise SystemExit(f"{brand_name}: tokens.json has no 'color' section — cannot retrofit")

    # Frontmatter colors: slot → hex (lower-case for parser symmetry).
    fm_colors = []
    body_color_lines = ["## Colors", ""]
    for slot, entry in color_section.items():
        if not isinstance(entry, dict) or "$value" not in entry:
            continue
        hex_val = entry["$value"].lower()
        desc = (entry.get("$description") or "").strip()
        # Inline-comment the description on the YAML line if it fits, otherwise body.
        comment = f"  # {desc}" if desc and len(desc) <= 60 else ""
        fm_colors.append(f'  {slot}: "{hex_val}"{comment}')
        if desc and len(desc) > 60:
            body_color_lines.append(f"- `{slot}` (`{hex_val}`) — {desc}")

    body_overview_text = (tokens.get("$description") or "").strip()
    body_overview = (
        f"## Overview\n\n{body_overview_text}\n"
        if body_overview_text
        else f"## Overview\n\n_({brand_name} brand — overview pending.)_\n"
    )

    body_typography = (
        "## Typography\n\n"
        "Defined in tokens.json (`font-family`, `font-weight`, `font-size`).\n"
        "Inherits from this brand's tokens for now; future revisions may move\n"
        "typography tokens into DESIGN.md frontmatter.\n"
    )

    body_color_block = (
        "\n".join(body_color_lines).rstrip() + "\n" if len(body_color_lines) > 2 else ""
    )

    # Display name: take first segment of $description before em-dash, strip trailing
    # punctuation. Fall back to title-cased brand slug.
    raw_name = (tokens.get("$description") or brand_name).split("—")[0].strip()
    display_name = raw_name.rstrip(" .") or brand_name.replace("-", " ").title()

    # Frontmatter description: first sentence of $description (no trailing punct dup).
    fm_description: str | None = None
    if tokens.get("$description"):
        first = tokens["$description"].split(".")[0].strip()
        if first and len(first) <= 200 and first != display_name:
            fm_description = first + "."

    fm_lines = ["---", "version: alpha", f"name: {display_name}"]
    if fm_description:
        fm_lines.append(f"description: {fm_description}")
    fm_lines.append("colors:")
    fm_lines.extend(fm_colors)
    fm_lines.append("---")

    parts = [
        "\n".join(fm_lines),
        body_overview.rstrip(),
        body_color_block.rstrip() if body_color_block else None,
        body_typography.rstrip(),
    ]
    return "\n\n".join(p for p in parts if p) + "\n"


def cmd_retrofit(args) -> int:
    import json

    brands = {b.name: b for b in discover_brands()}
    targets = [args.brand] if args.brand else sorted(brands.keys())
    written: list[str] = []
    for name in targets:
        if name not in brands:
            print(f"unknown brand: {name}", file=sys.stderr)
            return 1
        brand = brands[name]
        tokens_path = brand.root / "tokens.json"
        if not tokens_path.is_file():
            print(f"{name}: no tokens.json at {tokens_path}", file=sys.stderr)
            return 2
        tokens = json.loads(tokens_path.read_text(encoding="utf-8"))
        text = _retrofit_one(name, brand.root, tokens)

        # Verify it parses cleanly as a DESIGN.md before writing.
        try:
            from lib.design_md import parse_text
            parse_text(text, source=f"{name}/DESIGN.md (in-memory)")
        except ValueError as exc:
            print(f"{name}: generated DESIGN.md fails its own parser: {exc}", file=sys.stderr)
            return 1

        out = brand.root / "DESIGN.md"
        if args.dry_run:
            print(f"=== {out} ===")
            print(text)
        else:
            out.write_text(text, encoding="utf-8")
            written.append(name)
    if written:
        print(f"wrote {len(written)} DESIGN.md file(s): {', '.join(written)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ret = sub.add_parser("retrofit", help="Reverse-extract DESIGN.md from existing tokens.json")
    p_ret.add_argument("--brand", help="Target a single brand (default: all discovered)")
    p_ret.add_argument("--dry-run", action="store_true", help="Print DESIGN.md instead of writing")
    p_ret.set_defaults(func=cmd_retrofit)

    p_new = sub.add_parser(
        "from-design-md",
        help="Bake a new brand from its DESIGN.md by color-substituting a base brand",
    )
    p_new.add_argument("--brand", required=True, help="Target brand name (must have brands/<brand>/DESIGN.md)")
    p_new.add_argument("--base", required=True, help="Base brand to inherit geometry from (e.g. feinschliff)")
    p_new.add_argument("--dry-run", action="store_true", help="Report planned actions without writing")
    p_new.set_defaults(func=cmd_from_design_md)

    args = p.parse_args(argv)
    return args.func(args)


def _build_replacement_map(
    new_design_md: DesignMd,
    base_tokens: dict,
    new_brand: str,
    base_brand: str,
) -> dict[str, str]:
    """Return a {old_hex_upper_no_hash → new_hex_upper_no_hash} map.

    Validates: every slot in DESIGN.md.colors exists in base.tokens.json with
    a $value, and no two slots in the base palette share the same hex (would
    make the rewrite ambiguous).
    """
    base_color = base_tokens.get("color") or {}
    # First pass: collect base hex per slot, detect collisions.
    base_slot_hex: dict[str, str] = {}
    hex_to_slots: dict[str, list[str]] = {}
    for slot, entry in base_color.items():
        if isinstance(entry, dict) and "$value" in entry:
            up = entry["$value"].upper().lstrip("#")
            base_slot_hex[slot] = up
            hex_to_slots.setdefault(up, []).append(slot)

    overridden_slots = set(new_design_md.colors)
    overridden_hexes = {base_slot_hex[s] for s in overridden_slots if s in base_slot_hex}

    # Collision detection: if two slots in the BASE have the same hex AND at least
    # one of them is being overridden in the new brand, the rewrite is ambiguous.
    collisions = []
    for hex_up, slots in hex_to_slots.items():
        if len(slots) > 1 and hex_up in overridden_hexes:
            ambiguous_overridden = [s for s in slots if s in overridden_slots]
            if len(ambiguous_overridden) >= 1 and len(slots) > len(ambiguous_overridden):
                collisions.append(
                    f"#{hex_up} is shared by {slots} in base brand '{base_brand}'; "
                    f"DESIGN.md only overrides {ambiguous_overridden} — bake cannot disambiguate"
                )
    if collisions:
        raise SystemExit(
            f"{new_brand}: hex collisions block the rewrite:\n  " + "\n  ".join(collisions)
        )

    # Second pass: build the replacement map. Unknown slots in DESIGN.md raise.
    # Multiple slots may share the same base hex; if they map to different NEW
    # hexes, the rewrite is genuinely ambiguous — error.
    rep: dict[str, str] = {}
    rep_origin: dict[str, str] = {}  # base_hex → "first slot that wrote this"
    missing: list[str] = []
    divergent: list[str] = []
    for slot, new_hex in new_design_md.colors.items():
        if slot not in base_slot_hex:
            missing.append(slot)
            continue
        old = base_slot_hex[slot]
        new = new_hex.upper().lstrip("#")
        if old in rep and rep[old] != new:
            divergent.append(
                f"slots {rep_origin[old]!r} and {slot!r} both map from #{old} in base "
                f"'{base_brand}' but DESIGN.md sends them to different targets "
                f"(#{rep[old]} and #{new}) — bake cannot differentiate at the XML level"
            )
        rep[old] = new
        rep_origin[old] = slot
    if missing:
        raise SystemExit(
            f"{new_brand}: DESIGN.md.colors references slots not in base brand '{base_brand}': "
            f"{missing}"
        )
    if divergent:
        raise SystemExit(
            f"{new_brand}: divergent overrides for collided base slots:\n  "
            + "\n  ".join(divergent)
        )
    return rep


def _rewrite_pptx(src: Path, dst: Path, rep: dict[str, str]) -> int:
    """Copy src .pptx → dst with srgbClr hex values substituted per rep. Returns # of replacements."""
    rep_bytes = {k.encode("ascii"): v.encode("ascii") for k, v in rep.items()}

    def _sub_xml(content: bytes) -> tuple[bytes, int]:
        count = 0

        def _repl(m: re.Match) -> bytes:
            nonlocal count
            hex_up = m.group(1).upper()
            if hex_up in rep_bytes:
                count += 1
                return b'<a:srgbClr val="' + rep_bytes[hex_up] + b'"'
            return m.group(0)

        return _SRGB_RE.sub(_repl, content), count

    total = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(
        dst, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename.endswith(".xml") or info.filename.endswith(".rels"):
                data, n = _sub_xml(data)
                total += n
            zout.writestr(info, data)
    return total


def _rewrite_html(src: Path, dst: Path, rep: dict[str, str]) -> int:
    """Copy src HTML → dst with #RRGGBB literals substituted per rep. Returns # of replacements."""
    rep_bytes = {k.encode("ascii"): v.encode("ascii") for k, v in rep.items()}
    content = src.read_bytes()
    count = 0

    def _repl(m: re.Match) -> bytes:
        nonlocal count
        hex_up = m.group(1).upper()
        if hex_up in rep_bytes:
            count += 1
            return b"#" + rep_bytes[hex_up]
        return m.group(0)

    new_content = _CSS_HEX_RE.sub(_repl, content)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(new_content)
    return count


def _generate_tokens_json(
    base_tokens: dict,
    new_design_md: DesignMd,
    new_brand: str,
) -> dict:
    """Produce new brand's tokens.json by overlaying DESIGN.md colors on base."""
    out = json.loads(json.dumps(base_tokens))  # deep copy
    out["$description"] = (
        f"{new_design_md.name} — {new_design_md.description}"
        if new_design_md.description
        else new_design_md.name
    )
    color = out.setdefault("color", {})
    for slot, new_hex in new_design_md.colors.items():
        target = color.get(slot)
        if isinstance(target, dict):
            target["$value"] = new_hex.upper()
            # Note: descriptions stay as base's (palette-only override; brand
            # rationale lives in DESIGN.md body now).
    return out


def _generate_catalog_json(
    base_catalog: dict,
    new_brand: str,
    new_root: Path,
) -> dict:
    """Copy base catalog with brand renamed and per-layout sha256 refreshed."""
    out = json.loads(json.dumps(base_catalog))
    out["brand"] = new_brand
    for entry in out.get("layouts", []):
        renderer = entry.get("renderer", {})
        pptx = renderer.get("pptx")
        if not pptx:
            continue
        # source is relative to brand-root; same path works for new brand.
        src_rel = pptx.get("source")
        if not src_rel:
            continue
        f = new_root / src_rel
        if not f.is_file():
            raise SystemExit(f"{new_brand}: rebaked template missing: {f}")
        pptx["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def cmd_from_design_md(args) -> int:
    brand_name = args.brand
    base_name = args.base

    brands_root = REPO_ROOT / "brands"
    new_root = brands_root / brand_name
    base_root = brands_root / base_name

    design_md_path = new_root / "DESIGN.md"
    if not design_md_path.is_file():
        print(f"{brand_name}: DESIGN.md not found at {design_md_path}", file=sys.stderr)
        return 2
    if not base_root.is_dir():
        print(f"base brand not found: {base_root}", file=sys.stderr)
        return 2
    base_tokens_path = base_root / "tokens.json"
    base_catalog_path = base_root / "catalog.json"
    if not base_tokens_path.is_file() or not base_catalog_path.is_file():
        print(f"{base_name}: tokens.json or catalog.json missing", file=sys.stderr)
        return 2

    new_dm = parse_design_md(design_md_path)
    base_tokens = json.loads(base_tokens_path.read_text(encoding="utf-8"))
    base_catalog = json.loads(base_catalog_path.read_text(encoding="utf-8"))

    rep = _build_replacement_map(new_dm, base_tokens, brand_name, base_name)
    print(f"{brand_name}: {len(rep)} color slot(s) overridden from {base_name}")

    if args.dry_run:
        print("dry-run: skipping writes")
        return 0

    # Mirror the base brand's tree to the new brand, except:
    #  - DESIGN.md (already at dest)
    #  - tokens.json (regenerated)
    #  - catalog.json (regenerated)
    #  - templates/pptx/*.pptx (color-rewritten)
    #  - claude-design/<base>-2026.html (renamed + color-rewritten)
    #  - any pre-existing port-verify / port-needs-review (skip)
    skip_files = {
        "DESIGN.md",
        "tokens.json",
        "catalog.json",
        f"claude-design/{base_name}-2026.html",
        ".port-needs-review.txt",
    }
    skip_dirs = {".port-verify", "templates/pptx"}  # templates handled separately

    new_template_dir = new_root / "templates" / "pptx"
    new_template_dir.mkdir(parents=True, exist_ok=True)

    # Walk base tree.
    for src in base_root.rglob("*"):
        rel = src.relative_to(base_root)
        rel_str = str(rel)
        if str(rel) in skip_files:
            continue
        if any(rel_str.startswith(d + "/") or rel_str == d for d in skip_dirs):
            continue
        dst = new_root / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Rewrite templates.
    base_template_dir = base_root / "templates" / "pptx"
    total_template_subs = 0
    template_count = 0
    for src in sorted(base_template_dir.glob("*.pptx")):
        dst = new_template_dir / src.name
        n = _rewrite_pptx(src, dst, rep)
        total_template_subs += n
        template_count += 1
    print(f"{brand_name}: rewrote {template_count} templates ({total_template_subs} color subs)")

    # Rewrite claude-design HTML.
    base_html = base_root / "claude-design" / f"{base_name}-2026.html"
    if base_html.is_file():
        new_html = new_root / "claude-design" / f"{brand_name}-2026.html"
        n = _rewrite_html(base_html, new_html, rep)
        print(f"{brand_name}: rewrote claude-design HTML ({n} color subs)")

    # Generate tokens.json and catalog.json.
    new_tokens = _generate_tokens_json(base_tokens, new_dm, brand_name)
    (new_root / "tokens.json").write_text(
        json.dumps(new_tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    new_catalog = _generate_catalog_json(base_catalog, brand_name, new_root)
    (new_root / "catalog.json").write_text(
        json.dumps(new_catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"{brand_name}: wrote tokens.json, catalog.json, templates/, claude-design/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
