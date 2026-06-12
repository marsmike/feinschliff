#!/usr/bin/env python3
"""Bulk decompile every layout in a brand's verify-map.yaml from a source PPTX.

Reads `<brand>/verify-map.yaml`, then for each `<layout-name>: <slide-no>`
pair calls the hybrid PPTX+SVG decompiler
(`feinschliff_builder.decompile.pptx_svg_decompile.derive`) and writes
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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from feinschliff_builder.decompile.cleanup import cleanup_dsl, native_pic_rects, unslotified_text_report
from feinschliff_builder.decompile.pptx_svg_decompile import derive
from feinschliff_builder.decompile.slotify import clip_text_to_images, slotify_dsl, slotify_native_text
from feinschliff_builder.verify.verify_map import load_verify_map


def _cleanup_and_slotify_loop(dsl: str, *, asset_root, layout_name: str,
                              width_emu: float = 0.0, canvas_w: float = 1920.0,
                              max_rounds: int = 4) -> tuple[str, list[str]]:
    """Per-slide decompile loop: cleanup -> slotify (text lines + native
    payloads) -> re-check, until the unslotified-text report stops shrinking.

    Every pass is idempotent, so the loop normally converges in one round;
    the cap is a safety net. Returns ``(dsl, leftover report)`` — leftovers
    are texts that CANNOT be slotified (chart/SmartArt part labels, labels
    with braces), surfaced as warnings for the operator.
    """
    dsl, stats = cleanup_dsl(dsl, asset_root, width_emu=width_emu,
                             canvas_w=canvas_w)
    noise = {k: v for k, v in stats.items() if v}
    if noise:
        print(f"    cleanup {layout_name}: " +
              ", ".join(f"{k}={v}" for k, v in noise.items()))
    prev = None
    for _ in range(max_rounds):
        dsl, _slots = slotify_dsl(dsl)
        dsl, clips = clip_text_to_images(
            dsl, extra_images=native_pic_rects(
                dsl, asset_root, width_emu=width_emu, canvas_w=canvas_w))
        for line in clips:
            print(f"    clip {layout_name}: {line}")
        dsl, native_slots, logs = slotify_native_text(dsl, asset_root)
        for line in logs:
            print(f"    native-slotify {layout_name}: {line}")
        report = unslotified_text_report(dsl, asset_root)
        if prev is not None and len(report) >= len(prev):
            break
        prev = report
    return dsl, prev or []


def _derive_one(layout_name: str, slide_no: int, *, source_pptx: Path,
                canvas_w: int, canvas_h: int, tokens_path: Path | None,
                brand_pack: Path, brand_name: str, carry_images: bool,
                raw: bool, src_w_emu: int) -> tuple[str, int, list[str]]:
    """Derive + clean + slotify ONE slide and write its layout file.

    Module-level (picklable) so a ProcessPoolExecutor can fan slides out
    across workers — every slide is independent: it reads the shared source
    PPTX, writes only its own `layouts/<name>.slide.dsl` and per-layout
    asset dirs, and sha-named native sidecars are written atomically.
    Returns (layout_name, bytes_written, log lines) for ordered printing
    in the parent.
    """
    import contextlib
    import io
    log = io.StringIO()
    image_extract_dir = image_extract_rel = None
    if carry_images:
        image_extract_dir = brand_pack / "assets" / "decompile" / layout_name
        image_extract_rel = f"decompile/{layout_name}"
    with contextlib.redirect_stdout(log):
        dsl = derive(
            source_pptx,
            slide_idx=slide_no,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            tokens_path=tokens_path,
            layout_name=layout_name,
            theme_name=brand_name,
            image_extract_dir=image_extract_dir,
            image_extract_rel=image_extract_rel,
            native_extract_dir=brand_pack / "assets" / "native",
            native_extract_rel="native",
        )
        if not raw:
            dsl, leftovers = _cleanup_and_slotify_loop(
                dsl, asset_root=brand_pack / "assets",
                layout_name=layout_name,
                width_emu=float(src_w_emu), canvas_w=canvas_w)
            for msg in leftovers:
                print(f"    ⚠ {layout_name}: unslotified {msg}")
    target = brand_pack / "layouts" / f"{layout_name}.slide.dsl"
    target.write_text(dsl, encoding="utf-8")
    return layout_name, target.stat().st_size, log.getvalue().splitlines()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand-pack", required=True, type=Path,
                    help="Brand pack root (must contain verify-map.yaml and tokens.json)")
    ap.add_argument("--source-pptx", required=True, type=Path,
                    help="Source PPTX deck to decompile")
    ap.add_argument("--workers", type=int, default=16,
                    help="Parallel derive workers (default 16; 0 = auto: "
                         "min(8, cpu/2); 1 = sequential)")
    ap.add_argument("--canvas", default="1920x1080",
                    help="Target DSL canvas size (default: 1920x1080)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the layouts that would be derived, don't write")
    ap.add_argument("--only", nargs="*",
                    help="Restrict to a subset of layout names")
    ap.add_argument("--raw", action="store_true",
                    help="Skip the per-slide cleanup + slotify loop and emit the "
                         "decompiler's raw first pass (for fidelity debugging). "
                         "Default: each slide is cleaned (dup text lines, prompt "
                         "copies, helper captions, stacked native pics), slotified "
                         "(text lines AND native payload text runs), and checked "
                         "until no bindable placeholder text is left unslotified.")
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
    try:
        _vm = load_verify_map(brand_pack)
    except FileNotFoundError:
        sys.exit(f"missing verify-map.yaml in {brand_pack}")
    except ValueError as exc:
        sys.exit(str(exc))
    source_pptx: Path = args.source_pptx.resolve()
    if not source_pptx.is_file():
        sys.exit(f"source pptx not found: {source_pptx}")

    tokens_path = brand_pack / "tokens.json"
    brand_name = brand_pack.name
    canvas_w, canvas_h = (int(x) for x in args.canvas.split("x"))

    mapping = dict(_vm.layouts)
    requested = set(args.only) if args.only else None

    # Capture the source PPTX's physical slide size and record it in the
    # brand pack's tokens.json. The emitter (lib/dsl/pptx_emit.py) honours
    # `slide.width_emu` / `slide.height_emu` and scales EMU_PER_PX +
    # PX_TO_PT off them, so font sizes and shape positions render at the
    # SAME physical scale as the source — without this, an emit at the
    # toolkit default 13.33" wide renders a 42pt source title at ~28pt
    # because the px↔pt conversion bakes in a different DPI.
    import json as _json
    from pptx import Presentation as _Pres
    src_pres = _Pres(str(source_pptx))
    src_w_emu = int(src_pres.slide_width)
    src_h_emu = int(src_pres.slide_height)
    if tokens_path.is_file():
        try:
            tokens_data = _json.loads(tokens_path.read_text(encoding="utf-8"))
        except _json.JSONDecodeError as exc:
            sys.exit(f"unparseable tokens.json in {brand_pack}: {exc} — fix or remove it first")
    else:
        tokens_data = {}
    slide_block = tokens_data.setdefault("slide", {"$type": "dimension"})
    slide_block["width_emu"] = {"$value": str(src_w_emu),
                                "$description": "Source PPTX slide width in EMU — drives emitter scaling."}
    slide_block["height_emu"] = {"$value": str(src_h_emu),
                                 "$description": "Source PPTX slide height in EMU — drives emitter scaling."}

    # Detect the source theme's fonts (majorFont = display/title, minorFont =
    # body) AND its colour scheme, and seed both into tokens.json. The theme
    # part is resolved from the master relationship (decks number themes
    # per-master — a hardcoded `theme1.xml` silently misses decks whose master
    # uses `theme11.xml`, skipping font + colour capture entirely). Capturing
    # the palette here is what lets schemeClr fills (e.g. the bg panel) and
    # strokes reverse-map to tokens instead of being dropped. Existing tokens
    # are never overwritten — the author's semantic names win.
    import re as _re
    from feinschliff_builder.decompile.pptx_svg_decompile import master_theme_blob
    theme_blob = master_theme_blob(src_pres)
    if theme_blob:
        theme_xml = theme_blob.decode("utf-8", "replace")
        majors = _re.findall(r'<a:majorFont>.*?<a:latin[^/]+typeface="([^"]+)"', theme_xml, _re.DOTALL)
        minors = _re.findall(r'<a:minorFont>.*?<a:latin[^/]+typeface="([^"]+)"', theme_xml, _re.DOTALL)
        display_font = majors[0] if majors else None
        body_font = minors[0] if minors else None
        if display_font or body_font:
            ff_block = tokens_data.setdefault("font-family", {"$type": "fontFamily"})
            if display_font:
                ff_block["display"] = {"$value": [display_font, "Helvetica Neue", "Arial", "sans-serif"],
                                       "$description": f"Source theme majorFont: {display_font}"}
            if body_font:
                ff_block["body"] = {"$value": [body_font, "Helvetica Neue", "Arial", "sans-serif"],
                                    "$description": f"Source theme minorFont: {body_font}"}
            print(f"  source fonts: display={display_font!r} body={body_font!r} → tokens.json font-family")

        # Theme colour scheme → seed missing colour tokens (F7 — brand-design
        # capture is core). `theme-*` keys make every schemeClr the decompiler
        # meets reverse-mappable; ink/black/paper/white get safe defaults for a
        # fresh pack. setdefault semantics: an author palette is never clobbered.
        scheme: dict[str, str] = {}
        for m in _re.finditer(r'<a:(dk1|lt1|dk2|lt2|accent[1-6]|hlink|folHlink)>(.*?)</a:\1>',
                              theme_xml, _re.DOTALL):
            hm = (_re.search(r'srgbClr val="([0-9A-Fa-f]{6})"', m.group(2))
                  or _re.search(r'lastClr="([0-9A-Fa-f]{6})"', m.group(2)))
            if hm:
                scheme[m.group(1)] = "#" + hm.group(1).upper()
        if scheme:
            color_block = tokens_data.setdefault("color", {"$type": "color"})

            def _seed(name: str, hexval: str | None, desc: str | None = None) -> bool:
                if hexval and name not in color_block:
                    entry = {"$value": hexval}
                    if desc:
                        entry["$description"] = desc
                    color_block[name] = entry
                    return True
                return False

            seeded = 0
            for k, v in scheme.items():
                seeded += _seed(f"theme-{k}", v, f"Source theme {k}.")
            seeded += _seed("ink", scheme.get("dk1"), "Body/title ink — source theme dk1.")
            seeded += _seed("black", scheme.get("dk1"), "Display / deepest — source theme dk1.")
            seeded += _seed("paper", scheme.get("lt1"), "Canvas on light — source theme lt1.")
            seeded += _seed("white", scheme.get("lt1"))
            if seeded:
                print(f"  source palette: {len(scheme)} theme colours → tokens.json color "
                      f"({seeded} keys seeded; existing tokens kept)")

    if args.dry_run:
        print(f"  would record slide size {src_w_emu} × {src_h_emu} EMU → {tokens_path}")
    else:
        if tokens_path.is_file():
            shutil.copy2(tokens_path, tokens_path.with_name("tokens.json.bak"))
        tokens_path.write_text(_json.dumps(tokens_data, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(f"  source slide size: {src_w_emu/914400:.2f}in × {src_h_emu/914400:.2f}in "
              f"({src_w_emu} × {src_h_emu} EMU) → tokens.json slide.width_emu/height_emu")

    layouts_dir = brand_pack / "layouts"
    backup_dir = brand_pack / "layouts.bak"
    if not args.dry_run:
        layouts_dir.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

    todo: list[tuple[str, int]] = []
    for layout_name, slide_no in mapping.items():
        if requested is not None and layout_name not in requested:
            continue
        target = layouts_dir / f"{layout_name}.slide.dsl"
        if args.dry_run:
            print(f"  would derive {layout_name} ← p{slide_no} → {target}")
            continue
        if target.exists():
            shutil.copy2(target, backup_dir / target.name)
        todo.append((layout_name, slide_no))

    if args.dry_run:
        print(f"(dry-run: {len(todo)} layouts planned)")
        return 0

    import functools
    import os
    work = functools.partial(
        _derive_one,
        source_pptx=source_pptx, canvas_w=canvas_w, canvas_h=canvas_h,
        tokens_path=tokens_path if tokens_path.exists() else None,
        brand_pack=brand_pack, brand_name=brand_name,
        carry_images=args.carry_images, raw=args.raw, src_w_emu=src_w_emu)

    workers = args.workers or min(8, max(1, (os.cpu_count() or 2) // 2))
    workers = min(workers, max(1, len(todo)))
    derived = 0
    if workers <= 1:
        for layout_name, slide_no in todo:
            name, size, lines = work(layout_name, slide_no)
            for line in lines:
                print(line)
            print(f"  ✓ {name} ← p{slide_no} ({size} bytes)")
            derived += 1
    else:
        # Slides are independent (disjoint output paths; sha-named native
        # sidecars rename atomically; soffice rasterization runs with a
        # throwaway profile per call) — fan out across processes. Results
        # print in submission order so logs stay diffable run-to-run.
        from concurrent.futures import ProcessPoolExecutor
        print(f"  deriving {len(todo)} layouts on {workers} workers")
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futs = [(name, no, pool.submit(work, name, no))
                    for name, no in todo]
            for name, slide_no, fut in futs:
                name, size, lines = fut.result()
                for line in lines:
                    print(line)
                print(f"  ✓ {name} ← p{slide_no} ({size} bytes)")
                derived += 1

    print(f"\nderived {derived} layouts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
