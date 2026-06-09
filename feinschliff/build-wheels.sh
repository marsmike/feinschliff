#!/usr/bin/env bash
# Rebuild feinschliff/wheels/ — the offline wheelhouse the bin/ launcher installs.
# Builds feinschliff + the feinschmiede engine, then vendors the runtime dep
# closure (python-pptx + lxml + pillow + cairosvg + pyphen + jsonschema + pyyaml
# + rough + transitive). Wheels are gitignored; Phase 3 (PyPI) removes the
# vendoring. Requires uv and pip.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WHEELS="$HERE/wheels"; BUILD="$HERE/.debug/build"
rm -rf "$WHEELS" "$BUILD"; mkdir -p "$WHEELS" "$BUILD"

uv build --wheel --out-dir "$BUILD" "$HERE"                 # feinschliff (office)
uv build --wheel --out-dir "$BUILD" "$ROOT/feinschmiede"    # engine
cp "$BUILD"/feinschliff-*.whl "$BUILD"/feinschmiede-*.whl "$WHEELS"/

# Vendor the third-party runtime closure for this platform.
python3 -m pip download --only-binary=:all: --dest "$WHEELS" \
  python-pptx lxml pillow cairosvg pyphen jsonschema pyyaml rough
# Pure-python fallback for the one universal binary dep (ABI portability).
python3 -m pip download --no-deps --only-binary=:all: \
  --implementation py --abi none --platform any --python-version 3 \
  --dest "$WHEELS" charset-normalizer || true

# Record the interpreter the (ABI-specific) binary wheels target so the bin/
# launcher pins its venv to a matching Python.
python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' > "$WHEELS/.python-version"

echo "feinschliff: wheelhouse ready ($(find "$WHEELS" -name '*.whl' | wc -l | tr -d ' ') wheels, py$(cat "$WHEELS/.python-version")) in $WHEELS"
