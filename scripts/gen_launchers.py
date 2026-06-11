#!/usr/bin/env python3
"""Generate every plugin's bin/<name> launcher and build-wheels.sh from one
manifest + two templates — the single source of truth for the feinschmiede
family's bootstrap layer.

The launchers/build-wheels scripts used to be hand-mirrored across five plugins
(G7 in the suite review): a fix to the venv-bootstrap or wheelhouse logic had to
be copied five times and drifted in between. They now derive from PLUGINS +
LAUNCHER_TMPL + BUILD_WHEELS_TMPL below, so a bootstrap change is one edit here.

Usage:
    python3 scripts/gen_launchers.py            # (re)write all generated files
    python3 scripts/gen_launchers.py --check    # CI: fail if any file is stale

The generated files are committed (they must be on PATH/executable at install
time, before this generator could ever run). CI runs --check to keep them in
sync with this manifest.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# REGISTRY — single source of truth for every package / plugin in the suite.
#
# Flags:
#   has_cli              — ships a bin/<name> launcher and build-wheels.sh
#                          (must match PLUGINS keys exactly).
#   is_workspace_member  — listed under [tool.uv.workspace] members in root
#                          pyproject.toml.
#   is_plugin            — listed in .claude-plugin/marketplace.json plugins[]
#                          and has its own .claude-plugin/plugin.json.
#
# feinschmiede: shared engine package — workspace member, NOT a plugin.
# feinschliff-extra: pure-data plugin — plugin but NOT a workspace member
#                    (no pyproject.toml) and NOT a CLI plugin (no launcher).
# ---------------------------------------------------------------------------
REGISTRY: dict[str, dict] = {
    "feinschmiede": {
        "has_cli": False,
        "is_workspace_member": True,
        "is_plugin": False,
    },
    "feinschliff": {
        "has_cli": True,
        "is_workspace_member": True,
        "is_plugin": True,
    },
    "feinschliff-builder": {
        "has_cli": True,
        "is_workspace_member": True,
        "is_plugin": True,
    },
    "feinschliff-extra": {
        "has_cli": False,
        "is_workspace_member": False,
        "is_plugin": True,
    },
    "feinbild": {
        "has_cli": True,
        "is_workspace_member": True,
        "is_plugin": True,
    },
    "feinklang": {
        "has_cli": True,
        "is_workspace_member": True,
        "is_plugin": True,
    },
    "feinschnitt": {
        "has_cli": True,
        "is_workspace_member": True,
        "is_plugin": True,
    },
}

# Derived projections (used both for generation and for the --check manifests).
_CLI_NAMES   = {n for n, r in REGISTRY.items() if r["has_cli"]}
_WS_MEMBERS  = {n for n, r in REGISTRY.items() if r["is_workspace_member"]}
_PLUGIN_NAMES = {n for n, r in REGISTRY.items() if r["is_plugin"]}

# name -> bootstrap spec.
#   builds:      workspace dirs to `uv build` (first entry is the plugin itself;
#                wheel basenames use underscores, dirs use hyphens).
#   third_party: pip-download closure (charset-normalizer's universal fallback
#                is appended by the template for every plugin).
#   env_tail:    extra `export`s appended after the bootstrap, before exec.
PLUGINS: dict[str, dict] = {
    "feinschliff": {
        "builds": ["feinschliff", "feinschmiede"],
        "third_party": ["python-pptx", "lxml", "pillow", "cairosvg",
                        "pyphen", "jsonschema", "pyyaml", "rough"],
        "env_tail": "office",
    },
    "feinbild": {
        "builds": ["feinbild", "feinschmiede"],
        "third_party": ["requests", "cairosvg", "rough", "jsonschema", "pyyaml"],
        "env_tail": "none",
    },
    "feinklang": {
        "builds": ["feinklang"],
        "third_party": ["requests"],
        "env_tail": "none",
    },
    "feinschnitt": {
        "builds": ["feinschnitt"],
        "third_party": ["google-generativeai"],
        "env_tail": "recorder",
    },
    "feinschliff-builder": {
        "builds": ["feinschliff-builder", "feinschliff", "feinschmiede"],
        "third_party": ["python-pptx", "lxml", "pillow", "cairosvg", "pyphen",
                        "jsonschema", "pyyaml", "rough", "anthropic"],
        "env_tail": "none",
    },
}

# Verify PLUGINS keys == _CLI_NAMES at import time (programmer error guard).
assert set(PLUGINS) == _CLI_NAMES, (
    f"PLUGINS keys {set(PLUGINS)} != registry has_cli set {_CLI_NAMES}"
)

ENV_TAILS = {
    "none": "",
    "office": (
        "\n"
        "# Make this plugin's bundled toolkit layouts + brand packs discoverable by\n"
        "# the engine/office discovery (additive — a user's own paths still win).\n"
        'export FEINSCHLIFF_LAYOUT_PATH="${FEINSCHLIFF_LAYOUT_PATH:+$FEINSCHLIFF_LAYOUT_PATH:}$PLUGIN_ROOT/layouts"\n'
        'export FEINSCHLIFF_BRAND_PATH="${FEINSCHLIFF_BRAND_PATH:+$FEINSCHLIFF_BRAND_PATH:}$PLUGIN_ROOT/brands"\n'
        "\n"
        "# Register brand packs + layouts from sibling feinschliff-* plugin\n"
        "# directories (third-party plugins can ship their own brands/ and layouts/).\n"
        '_repo_root="$(cd "$PLUGIN_ROOT/.." && pwd)"\n'
        'for _sibling in "$_repo_root"/feinschliff-*; do\n'
        '  [[ -d "$_sibling/brands" ]] && \\\n'
        '    export FEINSCHLIFF_BRAND_PATH="${FEINSCHLIFF_BRAND_PATH:+$FEINSCHLIFF_BRAND_PATH:}$_sibling/brands"\n'
        '  [[ -d "$_sibling/layouts" ]] && \\\n'
        '    export FEINSCHLIFF_LAYOUT_PATH="${FEINSCHLIFF_LAYOUT_PATH:+$FEINSCHLIFF_LAYOUT_PATH:}$_sibling/layouts"\n'
        "done\n"
        "unset _sibling _repo_root\n"
    ),
    "recorder": (
        "\n"
        "# Let `feinschnitt record` find the bundled recipe profiles/schema (the\n"
        "# recorder logic lives in the wheel, not under skills/, so it can't\n"
        "# self-locate them).\n"
        'export FEINSCHNITT_RECORDER_HOME="$PLUGIN_ROOT/skills/cli-recorder"\n'
    ),
}

LAUNCHER_TMPL = r'''#!/usr/bin/env bash
# @NAME@ launcher — the reusable "a plugin exposes a CLI" pattern for the
# feinschmiede family. GENERATED by scripts/gen_launchers.py — do not edit by
# hand; edit the template there and re-run it.
#
# First run provisions a self-contained venv from the plugin's bundled wheels
# (offline), then execs the real CLI; later runs just exec the installed CLI.
# This file lives in bin/, so it is on PATH whenever the plugin is enabled —
# sibling plugins/skills call `@NAME@ …` as a bare command, never reaching into
# our files. The venv is keyed on a content signature of the wheelhouse PLUS the
# plugin's pyproject.toml, so a plugin update (new wheels or bumped source)
# rebuilds the persistent venv instead of running stale code; a best-effort
# flock serializes concurrent first runs; the venv is built in place (venvs are
# not relocatable) and rm -rf'd on a partial bootstrap so every retry self-heals.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-"$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"}"
DATA_DIR="${CLAUDE_PLUGIN_DATA:-"${XDG_DATA_HOME:-$HOME/.local/share}/feinschmiede/@NAME@"}"

VENV="$DATA_DIR/venv"
WHEELS="$PLUGIN_ROOT/wheels"
CLI="$VENV/bin/@NAME@"
READY="$VENV/.@NAME@-ready"

_BOOTSTRAPPING=0
_cleanup() { if [[ "$_BOOTSTRAPPING" -eq 1 && ! -f "$READY" ]]; then rm -rf "$VENV"; fi; }
trap _cleanup EXIT

_have_wheels() {
  [[ -d "$WHEELS" ]] || return 1
  local w
  for w in "$WHEELS"/*.whl; do [[ -e "$w" ]] && return 0; done
  return 1
}

_wheelhouse_sig() {
  # Sorted wheel filenames + byte sizes. Empty-glob-safe: returns a fixed token
  # when no wheels are present (so `set -e`/pipefail can't kill the launcher on
  # an unmatched glob), which simply forces a (re)build.
  _have_wheels || { printf 'no-wheels'; return 0; }
  { for w in "$WHEELS"/*.whl; do printf '%s %s\n' "${w##*/}" "$(wc -c <"$w")"; done | sort; } \
    | cksum | awk '{print $1}'
}

_source_sig() {
  # Hash the declared version/deps so an in-place source update that leaves a
  # stale wheelhouse still rebuilds the venv (the "automatic" content-hash).
  [[ -f "$PLUGIN_ROOT/pyproject.toml" ]] || { printf 'no-src'; return 0; }
  cksum < "$PLUGIN_ROOT/pyproject.toml" | awk '{print $1}'
}

_build_wheels_from_source() {
  # A marketplace/git install ships no wheels (they are gitignored). On first run
  # build them from the bundled source — needs uv + network for the dep closure.
  # PyPI Trusted Publishing (Phase 3) will replace this with a plain index install.
  [[ -f "$PLUGIN_ROOT/build-wheels.sh" ]] || return 1
  command -v uv >/dev/null 2>&1 || return 1
  echo "@NAME@: no prebuilt wheels — building from bundled source (first run; needs network)…" >&2
  bash "$PLUGIN_ROOT/build-wheels.sh" >&2
}

_bootstrap() {
  local sig="$1"
  if ! _have_wheels; then
    echo "@NAME@: no bundled wheels at $WHEELS and could not build them." >&2
    echo "@NAME@: needs 'uv' + network (or run build-wheels.sh in the plugin dir)." >&2
    exit 1
  fi

  mkdir -p "$DATA_DIR"
  exec 9>"$DATA_DIR/.bootstrap.lock" || true
  if command -v flock >/dev/null 2>&1; then flock 9 || true; fi
  if [[ -f "$READY" && "$(cat "$READY" 2>/dev/null)" == "$sig" ]]; then
    exec 9>&-
    return 0
  fi

  echo "@NAME@: first run — provisioning venv at $VENV (offline, from bundled wheels)…" >&2
  _BOOTSTRAPPING=1
  rm -rf "$VENV"

  local pyver=""
  [[ -f "$WHEELS/.python-version" ]] && pyver="$(cat "$WHEELS/.python-version")"

  if command -v uv >/dev/null 2>&1; then
    uv venv ${pyver:+--python "$pyver"} "$VENV" >&2
    uv pip install --reinstall --python "$VENV/bin/python" --no-index --find-links "$WHEELS" @NAME@ >&2
  else
    local py=""
    [[ -n "$pyver" ]] && py="$(command -v "python$pyver" || true)"
    [[ -z "$py" ]] && py="$(command -v python3 || true)"
    if [[ -z "$py" ]]; then
      echo "@NAME@: need 'uv' or 'python3' (with venv support); neither was found." >&2
      exit 1
    fi
    "$py" -m venv "$VENV" >&2
    if ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
      "$VENV/bin/python" -m ensurepip --upgrade >&2 || {
        echo "@NAME@: the venv has no pip and ensurepip failed — install 'uv' or python3-venv." >&2
        exit 1
      }
    fi
    "$VENV/bin/python" -m pip install --force-reinstall --no-index --find-links "$WHEELS" @NAME@ >&2
  fi

  printf '%s\n' "$sig" > "$READY"
  _BOOTSTRAPPING=0
  exec 9>&-
}

# Build the wheelhouse from bundled source whenever none is present (fresh
# marketplace/git install, or an update that dropped the gitignored wheels).
if ! _have_wheels; then
  _build_wheels_from_source || true
fi

SIG="$(_wheelhouse_sig).$(_source_sig)"
if [[ ! -f "$READY" || "$(cat "$READY" 2>/dev/null)" != "$SIG" ]]; then
  _bootstrap "$SIG"
fi
@ENV_TAIL@
exec "$CLI" "$@"
'''

BUILD_WHEELS_TMPL = r'''#!/usr/bin/env bash
# Rebuild @NAME@/wheels/ — the offline wheelhouse the bin/ launcher installs.
# GENERATED by scripts/gen_launchers.py — do not edit by hand; edit the template
# there and re-run it. Wheels are gitignored; Phase 3 (PyPI) removes vendoring.
# Requires uv and pip.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WHEELS="$HERE/wheels"
STAGE="$HERE/.debug/wheels.stage"   # assembled here; swapped into wheels/ only on success
BUILD="$HERE/.debug/build"
rm -rf "$STAGE" "$BUILD"; mkdir -p "$STAGE" "$BUILD"
# A failed build (network/resolution) must never leave a half-populated wheels/
# that the launcher would treat as complete and refuse to rebuild.
trap 'rm -rf "$STAGE"' EXIT

# Pin the third-party closure to the CI-tested lockfile when present, so a fresh
# install resolves the same versions CI did rather than "latest".
CONSTRAINTS=()
[[ -f "$ROOT/constraints.txt" ]] && CONSTRAINTS=(-c "$ROOT/constraints.txt")

@BUILD_STEPS@
@CP_STEP@
@THIRD_PARTY_BLOCK@
# Record the interpreter the (ABI-specific) binary wheels target so the bin/
# launcher pins its venv to a matching Python.
python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' > "$STAGE/.python-version"

# Swap the fully-built stage into place; set -e aborts before here on any failure.
rm -rf "$WHEELS"; mv "$STAGE" "$WHEELS"
trap - EXIT

echo "@NAME@: wheelhouse ready ($(find "$WHEELS" -name '*.whl' | wc -l | tr -d ' ') wheels, py$(cat "$WHEELS/.python-version")) in $WHEELS"
'''


def _wheel_base(dir_name: str) -> str:
    return dir_name.replace("-", "_")


def render_launcher(name: str, spec: dict) -> str:
    return (LAUNCHER_TMPL
            .replace("@ENV_TAIL@", ENV_TAILS[spec["env_tail"]])
            .replace("@NAME@", name))


def render_build_wheels(name: str, spec: dict) -> str:
    builds = spec["builds"]
    lines = []
    for i, d in enumerate(builds):
        src = '"$HERE"' if i == 0 else f'"$ROOT/{d}"'
        comment = "this plugin" if i == 0 else d
        lines.append(f'uv build --wheel --out-dir "$BUILD" {src}   # {comment}')
    build_steps = "\n".join(lines)
    globs = " ".join(f'"$BUILD"/{_wheel_base(d)}-*.whl' for d in builds)
    cp_step = f'cp {globs} "$STAGE"/'
    third = spec["third_party"]
    if third:
        third_block = (
            "\n# Vendor the third-party runtime closure (resolves the full closure for this platform).\n"
            'python3 -m pip download "${CONSTRAINTS[@]}" --only-binary=:all: --dest "$STAGE" \\\n'
            f'  {" ".join(third)}\n'
            "# Pure-python fallback for the one universal binary dep (ABI portability; best-effort).\n"
            "python3 -m pip download --no-deps --only-binary=:all: \\\n"
            "  --implementation py --abi none --platform any --python-version 3 \\\n"
            '  --dest "$STAGE" charset-normalizer || true\n'
        )
    else:
        third_block = "\n# stdlib-only: no third-party closure to vendor.\n"
    return (BUILD_WHEELS_TMPL
            .replace("@BUILD_STEPS@", build_steps)
            .replace("@CP_STEP@", cp_step)
            .replace("@THIRD_PARTY_BLOCK@", third_block)
            .replace("@NAME@", name))


def targets() -> list[tuple[Path, str, bool]]:
    """(path, content, executable) for every generated file."""
    out: list[tuple[Path, str, bool]] = []
    for name, spec in PLUGINS.items():
        out.append((ROOT / name / "bin" / name, render_launcher(name, spec), True))
        out.append((ROOT / name / "build-wheels.sh", render_build_wheels(name, spec), True))
    return out


# ---------------------------------------------------------------------------
# Manifest drift checks — called from main() when --check is passed.
# Each function returns a list of error strings (empty = passed).
# They operate on file CONTENTS passed in, not reading files themselves,
# which makes them unit-testable with tampered strings.
# ---------------------------------------------------------------------------

def _fmt_diff(label: str, expected: set[str], actual: set[str]) -> list[str]:
    errors = []
    missing = expected - actual
    extra   = actual - expected
    if missing:
        errors.append(f"  {label}: missing {sorted(missing)}")
    if extra:
        errors.append(f"  {label}: unexpected {sorted(extra)}")
    return errors


def check_marketplace(marketplace_text: str, plugin_jsons: dict[str, str]) -> list[str]:
    """Verify marketplace.json plugins[].name ↔ registry is_plugin set.

    Also verifies each listed plugin's source dir contains a plugin.json
    whose 'name' field matches the marketplace entry.

    Args:
        marketplace_text: raw text of .claude-plugin/marketplace.json
        plugin_jsons: mapping of plugin_name -> raw text of its plugin.json
                      (keyed by the dir name, not the JSON 'name')
    """
    errors: list[str] = []
    try:
        mkt = json.loads(marketplace_text)
    except json.JSONDecodeError as exc:
        return [f"  marketplace.json: JSON parse error: {exc}"]

    mkt_names = {p["name"] for p in mkt.get("plugins", [])}
    errors.extend(_fmt_diff("marketplace.json plugins vs registry is_plugin", _PLUGIN_NAMES, mkt_names))

    # Each plugin listed in marketplace should have a matching plugin.json
    for entry in mkt.get("plugins", []):
        name = entry["name"]
        source_dir = entry.get("source", f"./{name}").lstrip("./")
        raw = plugin_jsons.get(source_dir)
        if raw is None:
            errors.append(f"  {source_dir}/.claude-plugin/plugin.json: file missing")
            continue
        try:
            pj = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"  {source_dir}/.claude-plugin/plugin.json: JSON parse error: {exc}")
            continue
        if pj.get("name") != name:
            errors.append(
                f"  {source_dir}/.claude-plugin/plugin.json: "
                f"name={pj.get('name')!r} != marketplace entry {name!r}"
            )
    return errors


def check_pyproject_workspace(pyproject_text: str) -> list[str]:
    """Verify root pyproject.toml workspace members ↔ registry is_workspace_member."""
    errors: list[str] = []
    try:
        data = tomllib.loads(pyproject_text)
    except Exception as exc:
        return [f"  pyproject.toml: TOML parse error: {exc}"]
    members = set(data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", []))
    errors.extend(_fmt_diff("pyproject.toml workspace members vs registry is_workspace_member",
                            _WS_MEMBERS, members))
    return errors


def _parse_ci_yml(ci_text: str) -> dict[str, set[str]]:
    """Extract the four name-lists from ci.yml using targeted regex.

    ci.yml uses no YAML library at parse time here (gen_launchers.py is
    stdlib-only); we extract each list with a pattern matched against the
    known structural context.

    Returns a dict with keys:
      'members_heredoc'  — the inline Python list in the "All workspace packages"
                           step (lines 69-70 in the original file).
      'cli_regex'        — the alternation in the "Skill docs" grep step.
      'packages_matrix'  — the strategy.matrix.pkg list in the `packages` job.
      'wheel_matrix'     — the strategy.matrix.plugin list in the `wheel-install` job.
    """
    result: dict[str, set[str]] = {}

    # 1. members heredoc — Python list literal inside the heredoc block.
    #    Pattern: members = ["...", "...", ...]
    m = re.search(r'members\s*=\s*\[([^\]]+)\]', ci_text)
    if m:
        result["members_heredoc"] = {
            s.strip().strip('"').strip("'")
            for s in m.group(1).split(",")
            if s.strip().strip('"').strip("'")
        }
    else:
        result["members_heredoc"] = set()

    # 2. CLI-name regex alternation — the grep -E pattern for 'uv run <cli>'.
    #    Pattern: uv run (a|b|c)\b
    m = re.search(r"uv run \(([^)]+)\)\\b", ci_text)
    if m:
        result["cli_regex"] = {s.strip() for s in m.group(1).split("|")}
    else:
        result["cli_regex"] = set()

    # 3. packages matrix — pkg: [a, b, c, d]
    #    We look for the `packages:` job block and find its matrix.pkg list.
    pkg_block = re.search(r'packages:\s*\n.*?matrix:\s*\n.*?pkg:\s*\[([^\]]+)\]',
                          ci_text, re.DOTALL)
    if pkg_block:
        result["packages_matrix"] = {
            s.strip() for s in pkg_block.group(1).split(",") if s.strip()
        }
    else:
        result["packages_matrix"] = set()

    # 4. wheel-install matrix — plugin: [a, b, c, ...]
    whl_block = re.search(r'wheel-install:\s*\n.*?matrix:\s*\n.*?plugin:\s*\[([^\]]+)\]',
                          ci_text, re.DOTALL)
    if whl_block:
        result["wheel_matrix"] = {
            s.strip() for s in whl_block.group(1).split(",") if s.strip()
        }
    else:
        result["wheel_matrix"] = set()

    return result


def check_ci_yml(ci_text: str) -> list[str]:
    """Verify ci.yml name-lists against registry projections.

    Parsing strategy: stdlib regex against known structural anchors
    (gen_launchers.py is a stdlib-only script — no pyyaml in its runtime).
    Each pattern is documented in _parse_ci_yml above.

    Expected projections:
      members_heredoc  = is_workspace_member
      cli_regex        = has_cli
      packages_matrix  = is_workspace_member minus {feinschliff, feinschliff-builder}
                         (those two have dedicated CI jobs)
      wheel_matrix     = has_cli
    """
    errors: list[str] = []
    parsed = _parse_ci_yml(ci_text)

    if not parsed["members_heredoc"]:
        errors.append("  ci.yml: could not parse workspace members heredoc list")
    else:
        errors.extend(_fmt_diff(
            "ci.yml members heredoc vs registry is_workspace_member",
            _WS_MEMBERS, parsed["members_heredoc"],
        ))

    if not parsed["cli_regex"]:
        errors.append("  ci.yml: could not parse CLI-name regex alternation")
    else:
        errors.extend(_fmt_diff(
            "ci.yml CLI-name regex vs registry has_cli",
            _CLI_NAMES, parsed["cli_regex"],
        ))

    # packages matrix = workspace members minus the two dedicated jobs
    _DEDICATED_JOBS = {"feinschliff", "feinschliff-builder"}
    expected_pkg_matrix = _WS_MEMBERS - _DEDICATED_JOBS
    if not parsed["packages_matrix"]:
        errors.append("  ci.yml: could not parse packages matrix")
    else:
        errors.extend(_fmt_diff(
            "ci.yml packages matrix vs registry (is_workspace_member minus dedicated jobs)",
            expected_pkg_matrix, parsed["packages_matrix"],
        ))

    if not parsed["wheel_matrix"]:
        errors.append("  ci.yml: could not parse wheel-install matrix")
    else:
        errors.extend(_fmt_diff(
            "ci.yml wheel-install matrix vs registry has_cli",
            _CLI_NAMES, parsed["wheel_matrix"],
        ))

    return errors


def run_manifest_checks() -> list[str]:
    """Load all manifests from disk and run all drift checks.

    Returns a flat list of error strings; empty = all checks passed.
    """
    errors: list[str] = []

    marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"
    ci_path = ROOT / ".github" / "workflows" / "ci.yml"
    pyproject_path = ROOT / "pyproject.toml"

    # Collect plugin.json files for every plugin listed in marketplace
    try:
        mkt = json.loads(marketplace_path.read_text())
    except Exception as exc:
        return [f"Cannot read marketplace.json: {exc}"]

    plugin_jsons: dict[str, str] = {}
    for entry in mkt.get("plugins", []):
        source_dir = entry.get("source", f"./{entry['name']}").lstrip("./")
        pj_path = ROOT / source_dir / ".claude-plugin" / "plugin.json"
        plugin_jsons[source_dir] = pj_path.read_text() if pj_path.exists() else ""

    errors.extend(check_marketplace(marketplace_path.read_text(), plugin_jsons))
    errors.extend(check_pyproject_workspace(pyproject_path.read_text()))
    errors.extend(check_ci_yml(ci_path.read_text()))

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if any generated file is out of date")
    args = ap.parse_args()

    stale: list[Path] = []
    for path, content, executable in targets():
        current = path.read_text() if path.exists() else None
        if current == content:
            continue
        if args.check:
            stale.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if executable:
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"wrote {path.relative_to(ROOT)}")

    if args.check and stale:
        print("Out-of-date generated files (run scripts/gen_launchers.py):", file=sys.stderr)
        for p in stale:
            print(f"  {p.relative_to(ROOT)}", file=sys.stderr)
        return 1

    if args.check:
        manifest_errors = run_manifest_checks()
        if manifest_errors:
            print("Manifest drift detected:", file=sys.stderr)
            for e in manifest_errors:
                print(e, file=sys.stderr)
            return 1
        print("manifest checks passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
