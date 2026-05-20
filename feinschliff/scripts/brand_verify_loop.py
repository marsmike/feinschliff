#!/usr/bin/env python3
"""End-to-end source → render → diff orchestrator for brand-pack verification.

Any brand pack with a `verify-map.yaml` can run a single command to:

  1. **Export source PNGs** — converts the source deck (.pptx) to a single
     PDF via LibreOffice, then rasters every page referenced in
     `verify-map.yaml` to a 1920×1080 PNG.
  2. **Render derived layouts** — for each layout in `verify-map.yaml`,
     runs `feinschliff build` on `<brand>/layouts/<layout>.slide.dsl` →
     `.pptx` → `.pdf` → PNG. Slot defaults take over so the layout's own
     placeholder text/illustration appears in the render.
  3. **Diff** — delegates to `scripts/brand_visual_diff.py` to write
     per-layout 3-panel overlays, ghost masks, `report.json`, and an
     append-only `score-trace.jsonl` for plateau detection.

Everything caches under `<output-dir>/` keyed by file mtime, so re-runs
after a single DSL edit only rebuild the affected layout.

Drop-in usage:

  uv run python scripts/brand_verify_loop.py \\
      --brand-pack brands/<brand> \\
      --source-pptx path/to/source-deck.pptx

  uv run python scripts/brand_verify_loop.py \\
      --brand-pack brands/<brand> \\
      --source-pptx path/to/source-deck.pptx \\
      --only quote table cover-orange

  uv run python scripts/brand_verify_loop.py \\
      --brand-pack brands/<brand> \\
      --source-pptx path/to/source-deck.pptx \\
      --output-dir out/<brand>/verify-loop \\
      --skip-source-export

The pipeline is brand-agnostic; it only assumes the brand pack has a
`verify-map.yaml` mapping `<layout-name>: <source-slide-number>` and that
each layout exists at `<brand>/layouts/<layout-name>.slide.dsl`.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent

SOFFICE = "/usr/bin/soffice" if Path("/usr/bin/soffice").exists() else "soffice"


def _run(cmd: list[str], **kw) -> None:
    subprocess.run(cmd, check=True, **kw)


def _newer(target: Path, *srcs: Path) -> bool:
    if not target.exists():
        return True
    t = target.stat().st_mtime
    return any(s.exists() and s.stat().st_mtime > t for s in srcs)


def export_source_pngs(source_pptx: Path, source_pdf: Path,
                       source_png_dir: Path, slide_nos: list[int]) -> None:
    """Render the source deck once → split into per-slide PNGs at 1920×1080."""
    source_png_dir.mkdir(parents=True, exist_ok=True)
    if _newer(source_pdf, source_pptx):
        source_pdf.parent.mkdir(parents=True, exist_ok=True)
        print(f"[source] {source_pptx.name} → {source_pdf.name}")
        _run([SOFFICE, "--headless", "--convert-to", "pdf",
              "--outdir", str(source_pdf.parent), str(source_pptx)],
             capture_output=True)
        produced = source_pdf.parent / (source_pptx.stem + ".pdf")
        if produced != source_pdf:
            produced.rename(source_pdf)
    for n in slide_nos:
        out_png = source_png_dir / f"slide-{n:02d}.png"
        if not _newer(out_png, source_pdf):
            continue
        stem = source_png_dir / f"_p{n}"
        _run(["pdftoppm", "-png", "-f", str(n), "-l", str(n),
              "-scale-to-x", "1920", "-scale-to-y", "1080",
              str(source_pdf), str(stem)])
        produced = list(source_png_dir.glob(f"_p{n}-*.png"))
        if not produced:
            sys.exit(f"pdftoppm produced no file for page {n}")
        produced[0].rename(out_png)
        print(f"[source] slide {n:02d} → {out_png.name}")


def render_derived_pngs(brand_pack: Path, brand_name: str, work_root: Path,
                        render_png_dir: Path, layouts: list[str]) -> list[str]:
    """Build each layout's .slide.dsl → PPTX → PDF → PNG. Returns failures."""
    render_png_dir.mkdir(parents=True, exist_ok=True)
    layouts_dir = brand_pack / "layouts"
    # Make the brand pack's enclosing root discoverable for the build
    # subprocess. `feinschliff build --brand <name>` resolves the pack via
    # brand_discovery, which honours FEINSCHLIFF_BRAND_PATH (colon-separated
    # list of brand-root directories — each path is iterated for brand
    # subdirs, so it must point at the dir CONTAINING the pack, not its
    # grandparent). For out-of-tree packs this is the only way
    # --brand-pack is honoured end-to-end.
    enclosing = brand_pack.parent
    existing = os.environ.get("FEINSCHLIFF_BRAND_PATH", "")
    brand_env_path = (
        f"{enclosing}{os.pathsep}{existing}" if existing else str(enclosing)
    )
    build_env = {**os.environ, "FEINSCHLIFF_BRAND_PATH": brand_env_path}
    failures: list[str] = []
    for layout in layouts:
        dsl = layouts_dir / f"{layout}.slide.dsl"
        out_png = render_png_dir / f"{layout}.png"
        if not dsl.is_file():
            failures.append(f"{layout}: missing {dsl}")
            continue
        if not _newer(out_png, dsl):
            continue
        work = work_root / layout
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        pptx = work / f"{layout}.pptx"
        try:
            _run(["uv", "run", "feinschliff", "build",
                  "--brand", brand_name, "-o", str(pptx),
                  "--allow-missing-assets", "--skip-content-lint",
                  "--allow-diagram-warnings", str(dsl)],
                 cwd=REPO, capture_output=True, env=build_env)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            failures.append(f"{layout}: build failed — {stderr[-200:]}")
            continue
        try:
            _run([SOFFICE, "--headless", "--convert-to", "pdf",
                  "--outdir", str(work), str(pptx)],
                 capture_output=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            failures.append(f"{layout}: soffice failed — {stderr[-200:]}")
            continue
        pdf = work / f"{layout}.pdf"
        stem = work / "_p"
        _run(["pdftoppm", "-png", "-scale-to-x", "1920", "-scale-to-y", "1080",
              str(pdf), str(stem)])
        produced = sorted(work.glob("_p-*.png"))
        if not produced:
            failures.append(f"{layout}: pdftoppm produced nothing")
            continue
        produced[0].rename(out_png)
        print(f"[render] {layout} → {out_png.name}")
    return failures


def run_diff(brand_pack: Path, source_png_dir: Path,
             render_png_dir: Path, diff_dir: Path,
             only: list[str] | None = None,
             loupe: bool = False) -> None:
    diff_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["uv", "run", "python", str(SCRIPT_DIR / "brand_visual_diff.py"),
           "--brand-pack", str(brand_pack),
           "--source-dir", str(source_png_dir),
           "--render-dir", str(render_png_dir),
           "--output-dir", str(diff_dir)]
    if only:
        cmd += ["--only", *only]
    if loupe:
        cmd.append("--loupe")
    _run(cmd, cwd=REPO)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--brand-pack", required=True, type=Path,
                    help="Brand pack root (must contain verify-map.yaml + layouts/)")
    ap.add_argument("--source-pptx", required=True, type=Path,
                    help="Source PPTX deck to compare against")
    ap.add_argument("--output-dir", type=Path,
                    help="Where to write source-png/, render-png/, diff/. "
                         "Defaults to out/<brand>/verify-loop")
    ap.add_argument("--only", nargs="*",
                    help="Restrict to a subset of layouts (by name)")
    ap.add_argument("--skip-source-export", action="store_true",
                    help="Reuse cached source PNGs as-is")
    ap.add_argument("--skip-render", action="store_true",
                    help="Reuse cached render PNGs as-is")
    ap.add_argument("--snapshot-baseline", action="store_true",
                    help="Copy the post-render PNGs into render-png.before/ "
                         "before scoring. Use on the first run of an "
                         "improve-brand loop so brand_before_after_pdf.py "
                         "can compose source ↔ baseline ↔ final overlays.")
    ap.add_argument("--loupe", action="store_true",
                    help="Also emit a loupe PDF (per-layout top-N "
                         "connected-component diff hotspots, each cropped + "
                         "scaled). Use when the redline shows residual "
                         "mismatches too small to diagnose at slide scale.")
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

    brand_name = brand_pack.name
    out_root: Path = (args.output_dir or REPO / "out" / brand_name / "verify-loop").resolve()
    source_pdf = out_root / "source.pdf"
    source_png_dir = out_root / "source-png"
    render_png_dir = out_root / "render-png"
    diff_dir = out_root / "diff"
    work_root = out_root / "work"

    mapping: dict[str, int] = yaml.safe_load(verify_map.read_text())["layouts"]
    if args.only:
        wanted = set(args.only)
        mapping = {k: v for k, v in mapping.items() if k in wanted}
        if not mapping:
            sys.exit(f"--only matched no layouts (have: "
                     f"{sorted(yaml.safe_load(verify_map.read_text())['layouts'])})")

    if not args.skip_source_export:
        export_source_pngs(source_pptx, source_pdf, source_png_dir,
                           sorted(set(mapping.values())))
    if not args.skip_render:
        failures = render_derived_pngs(brand_pack, brand_name, work_root,
                                       render_png_dir, list(mapping))
        if failures:
            for f in failures:
                print(f"  ✗ {f}", file=sys.stderr)
            print(f"\n{len(failures)} render failure(s); aborting before diff.",
                  file=sys.stderr)
            return 1

    if args.snapshot_baseline:
        baseline_dir = out_root / "render-png.before"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        for layout in mapping:
            src = render_png_dir / f"{layout}.png"
            if src.is_file():
                shutil.copy2(src, baseline_dir / src.name)
        print(f"[baseline] snapshotted {len(mapping)} renders → "
              f"{baseline_dir.name}/")

    only = list(mapping) if args.only else None
    run_diff(brand_pack, source_png_dir, render_png_dir, diff_dir, only=only,
             loupe=args.loupe)
    print(f"\n→ overlays: {diff_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
