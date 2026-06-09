#!/usr/bin/env bash
# Rebuild feinklang/wheels/ — the offline wheelhouse the bin/ launcher installs
# from on first run. Re-runnable: safe to delete wheels/ and regenerate.
#
# Prerequisites: `uv` (builds the feinklang wheel) and `pip` (downloads the
# dependency closure; uv has no `pip download`).
#
# Wheels are gitignored (repo-size discipline). For local plugin testing they
# must exist on disk; Phase 3 (PyPI via Trusted Publishing) removes the
# vendoring entirely. The platform-specific binary wheels target the machine
# this runs on; we also vendor the pure-python fallbacks (see step 2b) so the
# wheelhouse still installs under a different interpreter ABI.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS="$HERE/wheels"
BUILD="$HERE/.debug/build"  # intermediate; gitignored

rm -rf "$WHEELS" "$BUILD"
mkdir -p "$WHEELS" "$BUILD"

# 1) Build the feinklang wheel from this package.
uv build --wheel --out-dir "$BUILD" "$HERE"
cp "$BUILD"/feinklang-*.whl "$WHEELS"/

# 2) Vendor the runtime dependency closure (requests + transitive) as wheels.
#    uv has no `pip download`; use pip, which resolves the full closure for this
#    interpreter/platform (charset-normalizer arrives as a binary ABI wheel).
python3 -m pip download --only-binary=:all: --dest "$WHEELS" requests

# 2b) Also vendor the pure-python (py3-none-any) fallback for the one binary
#     dependency, so the wheelhouse is not locked to this interpreter's ABI.
#     Best-effort: keep going if the universal wheel can't be fetched.
python3 -m pip download --no-deps --only-binary=:all: \
  --implementation py --abi none --platform any --python-version 3 \
  --dest "$WHEELS" charset-normalizer \
  || echo "feinklang: note — universal charset-normalizer wheel unavailable; wheelhouse is ABI-specific." >&2

echo "feinklang: wheelhouse ready ($(find "$WHEELS" -name '*.whl' | wc -l | tr -d ' ') wheels) in $WHEELS"
