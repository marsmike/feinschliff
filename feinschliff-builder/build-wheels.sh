#!/usr/bin/env bash
# Rebuild feinschliff-builder/wheels/ — the offline wheelhouse the bin/ launcher
# installs. Builds feinschliff-builder + feinschliff + the feinschmiede engine
# (builder Python-imports feinschliff — the office sub-family), then vendors the
# shared runtime closure. Wheels are gitignored; Phase 3 (PyPI) removes vendoring.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WHEELS="$HERE/wheels"; BUILD="$HERE/.debug/build"
rm -rf "$WHEELS" "$BUILD"; mkdir -p "$WHEELS" "$BUILD"

uv build --wheel --out-dir "$BUILD" "$HERE"                 # feinschliff-builder
uv build --wheel --out-dir "$BUILD" "$ROOT/feinschliff"     # feinschliff (imported)
uv build --wheel --out-dir "$BUILD" "$ROOT/feinschmiede"    # engine
cp "$BUILD"/feinschliff_builder-*.whl "$BUILD"/feinschliff-*.whl "$BUILD"/feinschmiede-*.whl "$WHEELS"/

# Vendor the third-party runtime closure (feinschliff + builder deps) for this platform.
python3 -m pip download --only-binary=:all: --dest "$WHEELS" \
  python-pptx lxml pillow cairosvg pyphen jsonschema pyyaml rough
python3 -m pip download --no-deps --only-binary=:all: \
  --implementation py --abi none --platform any --python-version 3 \
  --dest "$WHEELS" charset-normalizer || true

python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' > "$WHEELS/.python-version"

echo "feinschliff-builder: wheelhouse ready ($(find "$WHEELS" -name '*.whl' | wc -l | tr -d ' ') wheels, py$(cat "$WHEELS/.python-version")) in $WHEELS"
