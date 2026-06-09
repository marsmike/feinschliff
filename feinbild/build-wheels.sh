#!/usr/bin/env bash
# Rebuild feinbild/wheels/ — the offline wheelhouse the bin/ launcher installs.
# Builds feinbild + the feinschmiede engine, then vendors the dependency closure
# (requests + cairosvg/rough/jsonschema/pyyaml + transitive). Wheels are
# gitignored; Phase 3 (PyPI) removes the vendoring. Requires uv and pip.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WHEELS="$HERE/wheels"; BUILD="$HERE/.debug/build"
rm -rf "$WHEELS" "$BUILD"; mkdir -p "$WHEELS" "$BUILD"

uv build --wheel --out-dir "$BUILD" "$HERE"                 # feinbild
uv build --wheel --out-dir "$BUILD" "$ROOT/feinschmiede"    # engine
cp "$BUILD"/feinbild-*.whl "$BUILD"/feinschmiede-*.whl "$WHEELS"/

# Vendor third-party deps (resolves the full closure for this platform).
python3 -m pip download --only-binary=:all: --dest "$WHEELS" \
  requests cairosvg rough jsonschema pyyaml
# Pure-python fallback for the one binary dep (ABI portability; best-effort).
python3 -m pip download --no-deps --only-binary=:all: \
  --implementation py --abi none --platform any --python-version 3 \
  --dest "$WHEELS" charset-normalizer || true

# Record the interpreter these (ABI-specific) binary wheels target — pyyaml,
# cffi, and pillow ship as cp3XY wheels. The bin/ launcher reads this to pin its
# venv to a matching Python, so the offline install doesn't fail on an ABI gap
# when uv's default interpreter differs from this build's python3.
python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' > "$WHEELS/.python-version"

echo "feinbild: wheelhouse ready ($(find "$WHEELS" -name '*.whl' | wc -l | tr -d ' ') wheels, py$(cat "$WHEELS/.python-version")) in $WHEELS"
