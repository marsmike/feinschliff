"""Upload `docs/brand-previews/<brand>/*.png` to Cloudflare R2.

Walks every PNG under `docs/brand-previews/` and pushes it to the bucket
referenced by the gallery site builder
(``feinschliff/scripts/build_brand_gallery_site.py``):

    bucket: marsmike-assets
    key   : feinschliff/brand-previews/<brand>/<filename>.png

Files are sent via ``wrangler r2 object put`` so the script reuses the
operator's existing wrangler authentication (no extra R2 API tokens to
manage). Uploads run in parallel via a thread pool — wrangler itself is
single-file but ``concurrent.futures`` gives us 8× wall-time speedup.

Run::

    uv run python scripts/upload_brand_previews_to_r2.py             # all brands
    uv run python scripts/upload_brand_previews_to_r2.py feinschliff # subset
    uv run python scripts/upload_brand_previews_to_r2.py --workers 4
    uv run python scripts/upload_brand_previews_to_r2.py --dry-run

Skips ``*-private`` / ``*-client`` directories (those are local-only
client brand packs and must never leave the dev machine — same rule the
root ``.gitignore`` enforces).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PREVIEWS_DIR = REPO.parent / "docs" / "brand-previews"
R2_BUCKET = "marsmike-assets"
R2_PREFIX = "feinschliff/brand-previews"
# CDN cache: 5 minutes so a fresh render surfaces quickly. The gallery
# HTML appends `?v=<build-stamp>` for hard busts, but a short TTL keeps
# the no-querystring fetches from going stale for too long either.
CACHE_CONTROL = "public, max-age=300"


@dataclass(frozen=True)
class Job:
    brand: str
    local: Path
    key: str  # R2 object path: feinschliff/brand-previews/<brand>/<file>


def _discover(selected_brands: list[str] | None) -> list[Job]:
    if not PREVIEWS_DIR.is_dir():
        raise SystemExit(f"no brand previews at {PREVIEWS_DIR} — render first.")
    jobs: list[Job] = []
    for brand_dir in sorted(PREVIEWS_DIR.iterdir()):
        if not brand_dir.is_dir():
            continue
        brand = brand_dir.name
        if brand.endswith("-private") or brand.endswith("-client"):
            continue
        if selected_brands and brand not in selected_brands:
            continue
        for png in sorted(brand_dir.glob("*.png")):
            jobs.append(Job(
                brand=brand,
                local=png,
                key=f"{R2_PREFIX}/{brand}/{png.name}",
            ))
    return jobs


def _upload_one(job: Job) -> tuple[Job, bool, str]:
    cmd = [
        "wrangler", "r2", "object", "put",
        f"{R2_BUCKET}/{job.key}",
        "--file", str(job.local),
        "--content-type", "image/png",
        "--cache-control", CACHE_CONTROL,
        "--remote",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return job, True, ""
    # Surface wrangler's stderr so the caller can spot auth / quota issues.
    err = (result.stderr or result.stdout or "").strip().splitlines()
    tail = err[-3:] if err else ["(no output)"]
    return job, False, " | ".join(tail)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brands", nargs="*",
                    help="brand name(s) to upload; default = all")
    ap.add_argument("--workers", "-w", type=int, default=8,
                    help="concurrent wrangler invocations (default: 8)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list intended uploads but skip wrangler")
    args = ap.parse_args()

    jobs = _discover(args.brands or None)
    if not jobs:
        print("no PNGs to upload — nothing to do.", file=sys.stderr)
        return 0

    bytes_total = sum(j.local.stat().st_size for j in jobs)
    print(
        f"discovered {len(jobs)} PNG(s) across "
        f"{len({j.brand for j in jobs})} brand(s), "
        f"{bytes_total / 1024 / 1024:.1f} MiB total.",
        file=sys.stderr,
    )

    if args.dry_run:
        for job in jobs:
            print(f"DRY  {job.key}  ({job.local.stat().st_size} B)")
        return 0

    failures: list[tuple[Job, str]] = []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for job, ok, err in pool.map(_upload_one, jobs):
            done += 1
            if ok:
                print(f"  [{done:03d}/{len(jobs)}] ✓ {job.key}", flush=True)
            else:
                failures.append((job, err))
                print(f"  [{done:03d}/{len(jobs)}] ✗ {job.key}  ← {err}",
                      flush=True, file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} upload(s) failed:", file=sys.stderr)
        for job, err in failures:
            print(f"  {job.key}\n    {err}", file=sys.stderr)
        return 1

    print(f"\n✓ uploaded {len(jobs)} PNG(s) to "
          f"r2://{R2_BUCKET}/{R2_PREFIX}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
