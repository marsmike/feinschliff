"""`feinschliff-builder audit` — slot-coverage acceptance check for a brand pack.

  feinschliff-builder audit <brand-pack> [--max-mark-px 64]

Reports, per layout and in total:
  * unslotified text — literal `text` labels and literal `<a:t>` runs in
    non-chart native payloads (everything a deck author cannot bind);
  * photo natives — JPEG-media pics carried as fixed chrome although they
    exceed mark size (min dimension > --max-mark-px): photographs are
    topical content and must be picture slots. PNG/SVG natives of any size
    are legitimate corporate-design graphics (icon sets, illustration
    bands, supergraphics) — the source author placed them OUTSIDE a
    placeholder, which is the template's own "not replaceable" marker;
  * page-number slot presence (informational — absence is legitimate when
    the source slide carries no slide number).

Exit code 0 when the pack is fully covered (no unslotified text, no
photo natives), 1 otherwise — wire it into CI or run it as the
convergence gate after a decompile round.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path

from feinschliff_builder.decompile.cleanup import unslotified_text_report

_NATIVE_PIC_RE = re.compile(r"^native\s+\w+\b")
_KW_RE = re.compile(r'(\w+):"([^"]*)"')
_EXT_RE = re.compile(r'<a:ext cx="(\d+)" cy="(\d+)"/>')


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("brand_pack", type=Path,
                        help="Brand pack root (contains layouts/)")
    parser.add_argument("--max-mark-px", type=int, default=64,
                        help="JPEG native pics with min(w, h) above this are "
                             "flagged as unslotted photos (default 64)")
    parser.add_argument("--strict-rail", action="store_true",
                        help="Fail when any layout has rail-drift text "
                             "(non-strict mode only warns).")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable report on stdout")
    parser.set_defaults(func=cmd_audit)


def _rail_drift_for_layout(path: Path, brand_pack: Path) -> list[str]:
    """Lint pass that imports the brand's tokens and runs the engine's
    rail_drift_report against the layout's DSL nodes. Mirrors the snap
    pass exactly: the same node kinds, threshold, and shoulder semantics
    decide what's drift and what's intentional indent."""
    try:
        from feinschliff.dsl.parser import parse_lines
        from feinschliff.dsl.expander import rail_drift_report
        from feinschmiede.dsl.tokens import load_tokens
    except Exception:
        return []
    try:
        tokens = load_tokens(brand_pack)
    except Exception:
        return []
    try:
        body = path.read_text(encoding="utf-8")
        if body.startswith("---"):
            body = body.split("---\n", 2)[2]
        nodes, _ = parse_lines(body, source=str(path))
    except Exception:
        return []
    try:
        return rail_drift_report(nodes, tokens)
    except Exception:
        return []


def _width_emu(brand_pack: Path) -> float:
    try:
        raw = json.loads((brand_pack / "tokens.json").read_text(encoding="utf-8"))
        return float(raw["slide"]["width_emu"]["$value"])
    except Exception:
        return 12192000.0


def cmd_audit(args) -> int:
    brand_pack: Path = args.brand_pack.resolve()
    layouts_dir = brand_pack / "layouts"
    if not layouts_dir.is_dir():
        print(f"error: no layouts/ in {brand_pack}")
        return 2
    asset_root = brand_pack / "assets"
    px_per_emu = 1920.0 / _width_emu(brand_pack)

    report: dict[str, dict] = {}
    total_unslot = total_pics = total_drift = 0
    for path in sorted(layouts_dir.glob("*.slide.dsl")):
        text = path.read_text(encoding="utf-8")
        body = text.split("---\n", 2)[2] if text.startswith("---") else text
        name = path.name[: -len(".slide.dsl")]

        unslot = unslotified_text_report(body, asset_root)
        rail_drift = _rail_drift_for_layout(path, brand_pack)
        total_drift += len(rail_drift)

        content_pics: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("native pic"):
                continue
            kwargs = dict(_KW_RE.findall(line))
            # Only JPEG media counts as a wrongly-baked photo. PNG/SVG
            # natives are corporate-design graphics by source provenance
            # (the decompiler carries plain non-JPEG pics natively on
            # purpose) — flagging them by size produced 140+ false
            # positives per pack on icon sets and illustration bands.
            if kwargs.get("media_file"):
                if not kwargs["media_file"].lower().endswith((".jpg", ".jpeg")):
                    continue
            elif kwargs.get("media"):
                if not kwargs["media"].startswith("/9j/"):    # base64 of JPEG FFD8 magic
                    continue
            else:
                continue
            xml = None
            if kwargs.get("b64"):
                try:
                    xml = base64.b64decode(kwargs["b64"]).decode("utf-8", "replace")
                except ValueError:
                    continue
            elif kwargs.get("xml_file"):
                sidecar = asset_root / kwargs["xml_file"]
                if sidecar.is_file():
                    xml = sidecar.read_text(encoding="utf-8", errors="replace")
            if not xml:
                continue
            ext = _EXT_RE.search(xml)
            if ext is None:
                continue
            w = int(ext.group(1)) * px_per_emu
            h = int(ext.group(2)) * px_per_emu
            if min(w, h) > args.max_mark_px:
                content_pics.append(f"{line.split()[1]} {w:.0f}x{h:.0f}px (jpeg)")

        has_pagenum = '"page-number"' in text or "role: page-number" in text
        if unslot or content_pics or rail_drift:
            report[name] = {"unslotified": unslot, "content_native_pics": content_pics,
                            "rail_drift": rail_drift,
                            "page_number_slot": has_pagenum}
        total_unslot += len(unslot)
        total_pics += len(content_pics)

    if args.json:
        print(json.dumps({"layouts": report, "total_unslotified": total_unslot,
                          "total_content_native_pics": total_pics,
                          "total_rail_drift": total_drift}, indent=2))
    else:
        for name, entry in report.items():
            for u in entry["unslotified"]:
                print(f"  {name}: unslotified {u}")
            for p in entry["content_native_pics"]:
                print(f"  {name}: photo carried as native chrome {p}")
            for d in entry.get("rail_drift") or []:
                tag = "rail-drift" if args.strict_rail else "rail-drift (warn)"
                print(f"  {name}: {tag} {d}")
        n_layouts = len(list(layouts_dir.glob("*.slide.dsl")))
        print(f"audit: {n_layouts} layouts — {total_unslot} unslotified text(s), "
              f"{total_pics} photo native(s), {total_drift} rail-drift text(s)")
    bad_drift = total_drift if args.strict_rail else 0
    return 0 if (total_unslot == 0 and total_pics == 0 and bad_drift == 0) else 1
