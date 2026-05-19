"""Render every brand × every layout as a PNG — the gallery atlas.

For each brand pack under `brands/`, walks the v2 layout catalog
(shared layouts in `feinschliff/layouts/` plus any brand-specific
`brands/<brand>/layouts/` overrides), runs `feinschliff build` with
the matching content fixture, then converts the .pptx to PNG via
soffice + pdftoppm.

Output:
    docs/brand-previews/<brand>/<NN>-<layout-id>.png

NN is the 1-based alphabetical index of the layout id within the
brand's layout set; it gives stable, sortable filenames that play
nicely with both the gallery grid and Cloudflare R2 listings.

Run:
    uv run python scripts/render_brand_atlas.py                       # all brands
    uv run python scripts/render_brand_atlas.py feinschliff binance   # subset
    uv run python scripts/render_brand_atlas.py --force feinschliff   # rerender even if cached
    uv run python scripts/render_brand_atlas.py --workers 8           # parallel soffice

Content fixtures:
  - Shared layout `<id>.slide.dsl` looks for `tests/fixtures/layouts/<id>.yaml`
    at repo root, falling back to `brands/<brand>/tests/fixtures/layouts/<id>.yaml`.
  - Brand-specific layouts must ship `brands/<brand>/tests/fixtures/layouts/<id>.yaml`.

Caching: a PNG is regenerated only when its mtime is older than the
DSL, content YAML, brand tokens.json, or any compound the brand owns.
Pass --force to bypass.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from lib.soffice import PDFTOPPM, SOFFICE, pptx_to_png

REPO_ROOT = Path(__file__).resolve().parent.parent
BRANDS_DIR = REPO_ROOT / "brands"
SHARED_LAYOUTS = REPO_ROOT / "layouts"
SHARED_CONTENT = REPO_ROOT / "tests" / "fixtures" / "layouts"
GALLERY_DIR = REPO_ROOT.parent / "docs" / "brand-previews"


@dataclass(frozen=True)
class LayoutJob:
    brand: str
    layout_id: str
    layout_path: Path
    content_path: Path
    out_png: Path
    index: int  # 1-based alphabetical for filename


def _discover_layouts(brand: str) -> list[tuple[str, Path]]:
    """Return [(layout_id, layout_dsl_path), ...] for the brand.

    Brand-specific layouts under `brands/<brand>/layouts/` shadow the
    shared layout with the same id. Brand-only layouts (no shared
    sibling) are included too.
    """
    seen: dict[str, Path] = {}
    for dsl in sorted(SHARED_LAYOUTS.glob("*.slide.dsl")):
        seen[dsl.stem.removesuffix(".slide")] = dsl
    brand_layouts = BRANDS_DIR / brand / "layouts"
    if brand_layouts.is_dir():
        for dsl in sorted(brand_layouts.glob("*.slide.dsl")):
            seen[dsl.stem.removesuffix(".slide")] = dsl
    return sorted(seen.items())


def _find_content(brand: str, layout_id: str) -> Path | None:
    """Resolve the content YAML for a (brand, layout_id) pair."""
    brand_yaml = BRANDS_DIR / brand / "tests" / "fixtures" / "layouts" / f"{layout_id}.yaml"
    if brand_yaml.is_file():
        return brand_yaml
    shared_yaml = SHARED_CONTENT / f"{layout_id}.yaml"
    if shared_yaml.is_file():
        return shared_yaml
    return None


def _brand_chain(brand_dir: Path) -> list[Path]:
    """Walk DESIGN.md `extends:` chain; return [brand_dir, parent, grandparent, ...]."""
    chain: list[Path] = []
    seen: set[Path] = set()
    cur: Path | None = brand_dir
    while cur is not None and cur.resolve() not in seen:
        chain.append(cur)
        seen.add(cur.resolve())
        design = cur / "DESIGN.md"
        if not design.exists():
            break
        text = design.read_text()
        if not text.startswith("---"):
            break
        end = text.find("---", 3)
        if end < 0:
            break
        parent_name: str | None = None
        for line in text[3:end].splitlines():
            s = line.strip()
            if s.startswith("extends:"):
                parent_name = s.split(":", 1)[1].strip()
                break
        cur = (cur.parent / parent_name) if parent_name else None
    return chain


def _cache_inputs_mtime(job: LayoutJob, brand_dir: Path) -> float:
    """Newest mtime across the inputs that influence this PNG.

    Walks the brand's `extends:` chain so a parent brand's tokens.json
    (which gets merged at render time) also invalidates the cache.
    """
    candidates: list[Path] = [job.layout_path, job.content_path]
    for ancestor in _brand_chain(brand_dir):
        candidates.append(ancestor / "tokens.json")
        candidates.append(ancestor / "DESIGN.md")
        compounds_dir = ancestor / "compounds"
        if compounds_dir.is_dir():
            candidates.extend(compounds_dir.glob("*.dsl"))
    candidates.extend((REPO_ROOT / "compounds").glob("*.dsl"))
    return max(p.stat().st_mtime for p in candidates if p.exists())


def _build_pptx(job: LayoutJob) -> Path:
    """Run `feinschliff build` → temp .pptx."""
    tmp = Path(tempfile.mkdtemp(prefix=f"atlas-{job.brand}-{job.layout_id}-"))
    pptx = tmp / f"{job.layout_id}.pptx"
    cmd = [
        "uv", "run", "feinschliff", "build",
        str(job.layout_path),
        "--brand", job.brand,
        "--content", str(job.content_path),
        "-o", str(pptx),
        "--skip-content-lint",  # gallery render: skip the Phase-1 content lints
                                # (we want to surface real layout overflow via
                                # `feinschliff verify`, not block on title-length)
        "--allow-missing-assets",  # showcase render: blank slot beats missing
                                   # thumbnail when a brand lacks an illustration
                                   # the layout references
    ]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(
            f"feinschliff build failed for {job.brand}/{job.layout_id}\n"
            f"stderr:\n{res.stderr}\nstdout:\n{res.stdout}"
        )
    return pptx


def _pptx_to_png(pptx: Path, out_png: Path) -> None:
    """Convert pptx → PNG (first page) and copy to `out_png`."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="atlas-pdf-") as work_dir:
        png = pptx_to_png(pptx, Path(work_dir))
        shutil.copy(png, out_png)


def _render_one(job: LayoutJob) -> tuple[LayoutJob, str, str]:
    """Return (job, verdict, message). Verdict ∈ {ok, cached, fail}."""
    brand_dir = BRANDS_DIR / job.brand
    if job.out_png.is_file():
        inputs_mtime = _cache_inputs_mtime(job, brand_dir)
        if job.out_png.stat().st_mtime > inputs_mtime:
            return job, "cached", ""

    t0 = time.time()
    try:
        pptx = _build_pptx(job)
        _pptx_to_png(pptx, job.out_png)
        shutil.rmtree(pptx.parent, ignore_errors=True)
    except Exception as exc:
        return job, "fail", str(exc)
    return job, "ok", f"{(time.time() - t0):.1f}s"


def _collect_jobs(brands: list[str], skip_missing_content: bool) -> tuple[list[LayoutJob], list[str]]:
    jobs: list[LayoutJob] = []
    notes: list[str] = []
    for brand in brands:
        layouts = _discover_layouts(brand)
        for index, (lid, lpath) in enumerate(layouts, start=1):
            cpath = _find_content(brand, lid)
            if cpath is None:
                msg = f"  skip {brand}/{lid}: no content YAML in tests/fixtures/layouts/{lid}.yaml or brand override"
                if skip_missing_content:
                    notes.append(msg)
                    continue
                else:
                    raise SystemExit(msg.strip() + " (use --skip-missing to ignore)")
            out_png = GALLERY_DIR / brand / f"{index:02d}-{lid}.png"
            jobs.append(LayoutJob(brand, lid, lpath, cpath, out_png, index))
    return jobs, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brands", nargs="*", help="Brand ids (default: all)")
    ap.add_argument("--force", action="store_true", help="Rerender even if PNG is newer than inputs")
    ap.add_argument("--workers", type=int, default=4, help="Parallel render workers (soffice profiles isolated)")
    ap.add_argument("--skip-missing", action="store_true", default=True,
                    help="Skip (don't fail on) layouts with no content YAML")
    ap.add_argument("--strict", action="store_true",
                    help="Fail if any layout is missing a content YAML")
    ap.add_argument("--manifest", action="store_true",
                    help="Write docs/brand-previews/<brand>/manifest.json with layout metadata")
    args = ap.parse_args()

    if args.strict:
        args.skip_missing = False

    if not Path(SOFFICE).is_file():
        return print(f"render_brand_atlas: soffice not found at {SOFFICE}", file=sys.stderr) or 2
    if not shutil.which(PDFTOPPM):
        return print("render_brand_atlas: pdftoppm not found (brew install poppler)", file=sys.stderr) or 2

    if args.brands:
        brands = args.brands
    else:
        brands = sorted(b.name for b in BRANDS_DIR.iterdir() if b.is_dir())

    jobs, notes = _collect_jobs(brands, skip_missing_content=args.skip_missing)
    for n in notes:
        print(n)
    print(f"render_brand_atlas: {len(brands)} brands → {len(jobs)} render jobs (workers={args.workers})")

    if args.force:
        for j in jobs:
            j.out_png.unlink(missing_ok=True)

    stats = {"ok": 0, "cached": 0, "fail": 0}
    failures: list[tuple[LayoutJob, str]] = []
    t_start = time.time()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for job, verdict, msg in pool.map(_render_one, jobs):
            stats[verdict] += 1
            tag = {"ok": "✓", "cached": "·", "fail": "✗"}[verdict]
            line = f"  {tag} {job.brand:>22}  {job.layout_id:<22}  {msg}"
            print(line, flush=True)
            if verdict == "fail":
                failures.append((job, msg))
    elapsed = time.time() - t_start
    print(f"\nrender_brand_atlas: {stats['ok']} rendered, "
          f"{stats['cached']} cached, {stats['fail']} failed in {elapsed:.1f}s")

    if args.manifest:
        _write_manifests(brands)

    if failures:
        print("\nFailures:")
        for job, msg in failures:
            print(f"  {job.brand}/{job.layout_id}:\n    {msg.splitlines()[0]}")
        return 1
    return 0


def _write_manifests(brands: list[str]) -> None:
    """Per-brand manifest.json listing rendered layouts in order."""
    for brand in brands:
        out_dir = GALLERY_DIR / brand
        if not out_dir.is_dir():
            continue
        entries = []
        for png in sorted(out_dir.glob("*.png")):
            if png.name.startswith("_"):
                continue
            stem = png.stem  # NN-id
            idx, _, lid = stem.partition("-")
            entries.append({"index": int(idx), "id": lid, "file": png.name})
        manifest = out_dir / "manifest.json"
        manifest.write_text(json.dumps({"brand": brand, "layouts": entries}, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
