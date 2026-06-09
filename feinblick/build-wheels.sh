#!/usr/bin/env bash
# Rebuild feinblick/wheels/ — the offline wheelhouse the bin/ launcher installs
# from on first run. feinblick is stdlib-only, so the wheelhouse is just our own
# wheel. Re-runnable: safe to delete wheels/ and regenerate.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS="$HERE/wheels"
BUILD="$HERE/.debug/build"   # intermediate; gitignored
rm -rf "$WHEELS" "$BUILD"
mkdir -p "$WHEELS" "$BUILD"
uv build --wheel --out-dir "$BUILD" "$HERE"
cp "$BUILD"/feinblick-*.whl "$WHEELS"/
python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' > "$WHEELS/.python-version"
echo "feinblick: wheelhouse ready ($(find "$WHEELS" -name '*.whl' | wc -l | tr -d ' ') wheel, py$(cat "$WHEELS/.python-version")) in $WHEELS"
