# feinschmiede Engine Extraction + feinbild Plugin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the shared diagram/brand engine out of the `feinschliff` monolith into a new `feinschmiede` package, then build an independent `feinbild` (image/2D) plugin that consumes it via a bundled wheel — proving the engine-wheel-in-a-venv path and fixing the broken `lib.diagrams` invocation.

**Architecture:** `feinschmiede` becomes the shared engine Python package (brand/look system + diagram engine + dsl-ast + diagnostics + jsonwalk) — common things only. Office (`feinschliff`) is refactored to import `feinschmiede`. Each media plugin (`feinklang`, `feinbild`, …) lives at repo root, installs independently, and auto-loads its `bin/` CLI from a self-contained venv; the engine rides along as a vendored wheel. Cross-plugin links are CLI calls guaranteed by plugin `dependencies`.

**Tech Stack:** Python 3.11+, `uv` (workspace + build + venv), setuptools, argparse CLIs, `requests`; engine deps `jsonschema`/`pyyaml`/`cairosvg`/`rough`; Claude Code plugin manifests + bundled-wheel `bin/` launchers (Phase-0 sentinel/atomic template).

**Design doc:** `docs/superpowers/specs/2026-06-09-feinschmiede-architecture-design.md`

**Conventions used throughout:**
- Repo root `R = /home/mike/work/feinschliff/.claude/worktrees/cli-loose-coupling`. All paths below are relative to `R`.
- Branch `worktree-cli-loose-coupling` (already current). Every commit uses DCO sign-off: `git commit -s`.
- Intermediates go under a plugin's `.debug/` (gitignored), never `/tmp` (repo CLAUDE.md discipline).
- The required CI check is named **`feinschliff lib tests`** — its name must not change.

---

## File Structure (what gets created / moved / modified)

**Moved wholesale to the new engine package** (`feinschliff/feinschliff/…` → `feinschmiede/feinschmiede/…`):
`diagrams/` (entire dir), `brand/` (entire dir), `brand_discovery.py`, `diagnostics.py`, `jsonwalk.py`, `dsl/ast.py`, `dsl/tokens.py`.

**New (engine):** `feinschmiede/pyproject.toml`, `feinschmiede/feinschmiede/__init__.py`, `feinschmiede/feinschmiede/dsl/__init__.py`, `feinschmiede/tests/test_engine_smoke.py`.

**Modified (office, stays in `feinschliff`):** `feinschliff/feinschliff/__init__.py`, `defects.py`, `layout_validator.py`, `pipeline.py`, `slot_budget.py`, all of `cli/`, `deck/`, `dsl/{parser,expander,pptx_emit}.py` (import-prefix rewrites); `deck/picker.py` + `brand/pack.py` (back-edge severance); `feinschliff/pyproject.toml` (add `feinschmiede` dep); `feinschliff/tests/**` (import-prefix rewrites).

**New (feinbild plugin, repo root):** `feinbild/` with `.claude-plugin/plugin.json`, `pyproject.toml`, `bin/feinbild`, `build-wheels.sh`, `src/feinbild/{__init__,cli,images,diagrams_cli,env}.py`, `brands/feinschliff/` (bundled pack), `skills/{imagine,svg,excalidraw}/SKILL.md`, `commands/{imagine,svg,excalidraw}.md`, `README.md`.

**Moved (Phase-0 tidy):** `feinschmiede/feinklang` → `feinklang`, `feinschmiede/feinklang-consumer` → `feinklang-consumer`; root `.claude-plugin/marketplace.json` becomes the umbrella marketplace; root `.gitignore` gains the plugin artifact patterns.

---

## Task 1: Phase-0 layout tidy — move plugins to repo root

**Files:**
- Move: `feinschmiede/feinklang` → `feinklang`, `feinschmiede/feinklang-consumer` → `feinklang-consumer`
- Modify: `.claude-plugin/marketplace.json` (root), `.gitignore` (root)
- Delete: `feinschmiede/.claude-plugin/marketplace.json`, `feinschmiede/.gitignore`, `feinschmiede/README.md` (the `feinschmiede/` dir is reused as the engine package next task)

- [ ] **Step 1: Move the two plugins to root**

```bash
cd "$R"
git mv feinschmiede/feinklang feinklang
git mv feinschmiede/feinklang-consumer feinklang-consumer
git rm feinschmiede/.claude-plugin/marketplace.json feinschmiede/.gitignore feinschmiede/README.md
rmdir feinschmiede/.claude-plugin 2>/dev/null || true
```

- [ ] **Step 2: Fold the Phase-0 ignore patterns into the root `.gitignore`**

Append to `.gitignore` (root):

```gitignore

# feinschmiede plugin family — regenerable artifacts (vendored wheels, venvs, debug)
*/wheels/
*/.debug/
*/dist/
*/build/
*/venv/
```

- [ ] **Step 3: Make the root marketplace the umbrella, listing root-level plugins**

Replace `.claude-plugin/marketplace.json` (root) with:

```json
{
  "name": "feinschmiede",
  "owner": { "name": "Mike Mueller", "email": "mike@objektarium.de" },
  "metadata": {
    "description": "Feinschmiede — branded media plugins for Claude Code, coupled by CLI capabilities (never file paths): decks, image/2D, video, and audio, over a shared engine."
  },
  "plugins": [
    { "name": "feinschliff", "description": "Office / decks (PowerPoint) — brand-pluggable design system.", "source": "./feinschliff" },
    { "name": "feinschliff-builder", "description": "Brand-pack authoring toolkit (compile-html, decompile, verify, improve-brand). Requires feinschliff.", "source": "./feinschliff-builder" },
    { "name": "feinschliff-extra", "description": "Extra brand packs for feinschliff: 10 additional themes.", "source": "./feinschliff-extra" },
    { "name": "feinklang", "description": "Audio voiceover — ElevenLabs text-to-speech via the clean `feinklang` CLI.", "source": "./feinklang" },
    { "name": "feinklang-consumer", "description": "Throwaway Phase-0 smoke test: depends on feinklang and calls it as a bare command. Not for distribution.", "source": "./feinklang-consumer" }
  ]
}
```

- [ ] **Step 4: Update feinklang's marketplace-relative wheelhouse + rebuild it at the new location**

`feinklang`'s launcher derives `PLUGIN_ROOT` from its own location, so no edit is needed there. Rebuild the gitignored wheelhouse at the new path:

```bash
cd "$R/feinklang" && ./build-wheels.sh
```
Expected: `feinklang: wheelhouse ready (7 wheels) in …/feinklang/wheels`.

- [ ] **Step 5: Verify the move is clean**

```bash
cd "$R"
test -f feinklang/bin/feinklang && test -f feinklang/.claude-plugin/plugin.json && echo "feinklang at root OK"
test ! -d feinschmiede && echo "feinschmiede/ cleared OK"   # will be recreated as the engine package next task
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('marketplace JSON OK')"
git status --short
```
Expected: feinklang present at root, `feinschmiede/` gone, marketplace JSON valid, only renames/edits staged.

- [ ] **Step 6: Commit**

```bash
cd "$R"
git add -A
git commit -s -m "refactor(feinschmiede): move Phase-0 plugins to repo root; umbrella marketplace"
```

---

## Task 2: Create the `feinschmiede` engine package skeleton

**Files:**
- Create: `feinschmiede/pyproject.toml`, `feinschmiede/feinschmiede/__init__.py`, `feinschmiede/feinschmiede/dsl/__init__.py`
- Modify: `pyproject.toml` (root workspace members)

- [ ] **Step 1: Create the engine `pyproject.toml`**

Create `feinschmiede/pyproject.toml`:

```toml
[project]
name = "feinschmiede"
version = "0.1.0"
description = "feinschmiede — shared engine for the feinschmiede media family: brand/look system + diagram engine + DSL AST."
requires-python = ">=3.11"
license = "MIT"
authors = [{ name = "Mike Mueller", email = "mike@objektarium.de" }]
dependencies = [
    "jsonschema>=4.26.0",
    "pyyaml>=6.0.3",
    "cairosvg>=2.9.0",
    "rough>=1.6",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["feinschmiede*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Add `feinschmiede` to the uv workspace**

Replace `pyproject.toml` (root) contents with:

```toml
# Note: feinschliff-extra is a pure-data plugin (no Python, no pyproject.toml)
# and is intentionally NOT a workspace member. It ships brand-pack assets only.
[tool.uv.workspace]
members = ["feinschmiede", "feinschliff", "feinschliff-builder"]
```

- [ ] **Step 3: Create the engine package `__init__` files (empty for now — populated after the move)**

```bash
cd "$R"
mkdir -p feinschmiede/feinschmiede/dsl feinschmiede/tests
: > feinschmiede/feinschmiede/__init__.py
: > feinschmiede/feinschmiede/dsl/__init__.py
```

(The top-level `__init__.py` is populated in Task 4 once the modules exist.)

- [ ] **Step 4: Commit**

```bash
cd "$R"
git add feinschmiede/pyproject.toml feinschmiede/feinschmiede pyproject.toml
git commit -s -m "feat(feinschmiede): scaffold shared engine package + add to uv workspace"
```

---

## Task 3: Move the engine modules with `git mv`

**Files:** moves only (history-preserving).

- [ ] **Step 1: Move the engine closure into the new package**

```bash
cd "$R"
git mv feinschliff/feinschliff/diagrams        feinschmiede/feinschmiede/diagrams
git mv feinschliff/feinschliff/brand           feinschmiede/feinschmiede/brand
git mv feinschliff/feinschliff/brand_discovery.py feinschmiede/feinschmiede/brand_discovery.py
git mv feinschliff/feinschliff/diagnostics.py  feinschmiede/feinschmiede/diagnostics.py
git mv feinschliff/feinschliff/jsonwalk.py     feinschmiede/feinschmiede/jsonwalk.py
git mv feinschliff/feinschliff/dsl/ast.py      feinschmiede/feinschmiede/dsl/ast.py
git mv feinschliff/feinschliff/dsl/tokens.py   feinschmiede/feinschmiede/dsl/tokens.py
```

- [ ] **Step 2: Verify the office `dsl` package still has its office modules and an `__init__`**

```bash
cd "$R"
ls feinschliff/feinschliff/dsl/    # expect: __init__.py parser.py expander.py pptx_emit.py polish.py (NO ast.py/tokens.py)
ls feinschmiede/feinschmiede/dsl/  # expect: __init__.py ast.py tokens.py
```
Expected: `ast.py`/`tokens.py` only under `feinschmiede/`; `parser.py` etc. only under `feinschliff/`.

- [ ] **Step 3: Commit the raw move (imports fixed in the next task)**

```bash
cd "$R"
git commit -s -m "refactor(feinschmiede): git mv engine closure into feinschmiede package (imports fixed next)"
```

---

## Task 4: Rewrite imports `feinschliff.<engine>` → `feinschmiede.<engine>`

**Files:** every `.py` under `feinschmiede/feinschmiede/` (moved engine), `feinschliff/feinschliff/` (office), and `feinschliff/tests/`. Also docstring/`prog=`/legacy-`lib.diagrams` strings.

The 7 rewrite rules (research-confirmed): `feinschliff.diagrams`, `feinschliff.brand_discovery`, `feinschliff.diagnostics`, `feinschliff.jsonwalk`, `feinschliff.dsl.ast`, `feinschliff.dsl.tokens`, and `feinschliff.brand` (word-boundary — must NOT catch `brand_discovery`). Relative `from .` imports inside moved modules need no change. `feinschliff.dsl.parser/expander/pptx_emit/polish` and all other `feinschliff.*` office modules must NOT be rewritten.

- [ ] **Step 1: Apply the prefix rewrites across engine + office + tests**

```bash
cd "$R"
rewrite() {
  sed -i -E \
    -e 's/feinschliff\.diagrams/feinschmiede.diagrams/g' \
    -e 's/feinschliff\.brand_discovery/feinschmiede.brand_discovery/g' \
    -e 's/feinschliff\.diagnostics/feinschmiede.diagnostics/g' \
    -e 's/feinschliff\.jsonwalk/feinschmiede.jsonwalk/g' \
    -e 's/feinschliff\.dsl\.ast/feinschmiede.dsl.ast/g' \
    -e 's/feinschliff\.dsl\.tokens/feinschmiede.dsl.tokens/g' \
    -e 's/feinschliff\.brand\./feinschmiede.brand./g' \
    -e 's/feinschliff\.brand\b/feinschmiede.brand/g' \
    "$1"
}
export -f rewrite
# Engine files (fix their own internal absolute imports, e.g. renderer.py, brand_discovery.py, tokens.py)
find feinschmiede/feinschmiede -name '*.py' -exec bash -c 'rewrite "$0"' {} \;
# Office files (staying) + tests that consume the moved modules
grep -rlE 'feinschliff\.(diagrams|brand_discovery|diagnostics|jsonwalk|brand|dsl\.ast|dsl\.tokens)' \
  feinschliff/feinschliff feinschliff/tests --include='*.py' | while read -r f; do rewrite "$f"; done
# Legacy/cosmetic strings: lib.diagrams -> feinschmiede.diagrams, and python -m feinschliff.diagrams -> feinschmiede
grep -rlE 'lib\.diagrams|python -m feinschliff\.diagrams' feinschliff feinschmiede --include='*.py' --include='*.md' \
  | while read -r f; do sed -i -E -e 's/lib\.diagrams/feinschmiede.diagrams/g' -e 's/python -m feinschliff\.diagrams/python -m feinschmiede.diagrams/g' "$f"; done
```

- [ ] **Step 2: Sanity-check that no stale engine import remains and no office module got mis-rewritten**

```bash
cd "$R"
echo "--- stale engine imports left in office/tests (expect none) ---"
grep -rnE 'feinschliff\.(diagrams|brand_discovery|diagnostics|jsonwalk|dsl\.ast|dsl\.tokens)|feinschliff\.brand\b' feinschliff/feinschliff feinschliff/tests --include='*.py' || echo "NONE ✓"
echo "--- office modules wrongly rewritten in engine (expect none) ---"
grep -rnE 'feinschmiede\.dsl\.(parser|expander|pptx_emit|polish)|feinschmiede\.(deck|cli|io|layout_|pipeline|textfit|slot_budget|content_validator|book|defects|schemas)' feinschmiede/feinschmiede feinschliff --include='*.py' || echo "NONE ✓"
```
Expected: both print `NONE ✓`. If the second finds hits, a `feinschmiede.*` office reference was created by an over-broad rule — revert that line by hand.

- [ ] **Step 3: Populate the engine package `__init__.py` (re-export the public API the old `feinschliff/__init__.py` exposed)**

Write `feinschmiede/feinschmiede/__init__.py`:

```python
# feinschmiede — shared engine: brand/look system + diagram engine + DSL AST.

from feinschmiede.brand.pack import BrandPack
from feinschmiede.diagnostics import Defect, DefectKind, DiagnosticBag, Severity
from feinschmiede.dsl.ast import Document, Element, ElementKind, Slide

__all__ = [
    "BrandPack",
    "Defect",
    "DefectKind",
    "DiagnosticBag",
    "Document",
    "Element",
    "ElementKind",
    "Severity",
    "Slide",
]
```

- [ ] **Step 4: Verify the engine imports standalone (no `feinschliff` import) once its venv exists**

Deferred to Task 6 Step 3 (after `uv sync`). For now, eyeball that `feinschmiede/feinschmiede/__init__.py` references only `feinschmiede.*`.

- [ ] **Step 5: Commit**

```bash
cd "$R"
git add -A
git commit -s -m "refactor(feinschmiede): rewrite engine imports feinschliff.* -> feinschmiede.*"
```

---

## Task 5: Sever the engine→office back-edge (`brand/pack.py` layout methods)

The only engine→office imports are two lazy `from feinschliff.layout_discovery import …` inside `BrandPack.find_layout()` and `BrandPack.layout_table()` (`feinschmiede/feinschmiede/brand/pack.py`). Their only callers are office `feinschliff/feinschliff/deck/picker.py` (and `tests/test_brand_pack.py`). Move the logic to the office side.

**Files:**
- Modify: `feinschmiede/feinschmiede/brand/pack.py` (remove the two methods + the office imports), `feinschliff/feinschliff/deck/picker.py` (call `layout_discovery` directly), `feinschliff/tests/test_brand_pack.py` (retarget the test if it exercised those methods).

- [ ] **Step 1: Read the two methods and their callers to capture exact signatures**

```bash
cd "$R"
sed -n '180,230p' feinschmiede/feinschmiede/brand/pack.py
sed -n '85,115p'  feinschliff/feinschliff/deck/picker.py
grep -n "find_layout\|layout_table\|layout_discovery" feinschliff/tests/test_brand_pack.py
```

- [ ] **Step 2: Remove the two office-facing methods + their imports from `brand/pack.py`**

Delete the `find_layout(self, …)` and `layout_table(self)` method bodies (the ones whose first line is `from feinschliff.layout_discovery import …`). Keep `BrandPack.layouts_path` (the brand-local input both methods read). Confirm afterward:

```bash
cd "$R"
grep -n "layout_discovery\|feinschliff" feinschmiede/feinschmiede/brand/pack.py || echo "brand/pack.py is engine-pure ✓"
```
Expected: `brand/pack.py is engine-pure ✓` (no `feinschliff`/`layout_discovery` reference remains).

- [ ] **Step 3: Move the logic into office `deck/picker.py`**

At the two call sites in `feinschliff/feinschliff/deck/picker.py` (formerly `pack.find_layout(...)` / `pack.layout_table()`), inline the discovery via the office module. Add at the top of `picker.py`:

```python
from feinschliff.layout_discovery import find_layout as _find_layout, discover_layout_paths
```

and replace the two calls:

```python
# was: layout = pack.find_layout(name)
layout = _find_layout(name, pack.layouts_path)
# was: table = pack.layout_table()
table = {p.stem: p for p in discover_layout_paths(pack.layouts_path)}
```

Match the real argument shapes you observed in Step 1 (the `layout_discovery` functions take the brand's `layouts_path`); adjust the two lines to the actual signatures if they differ.

- [ ] **Step 4: Retarget `tests/test_brand_pack.py` if needed**

If `test_brand_pack.py` called `pack.find_layout(...)`/`pack.layout_table()`, change it to call the office helpers (`from feinschliff.layout_discovery import find_layout` / `discover_layout_paths`) with `pack.layouts_path`, or move those assertions into a `feinschliff/tests/test_picker.py`. If it didn't touch those methods, no change.

- [ ] **Step 5: Commit**

```bash
cd "$R"
git add -A
git commit -s -m "refactor(feinschmiede): sever engine->office back-edge (move BrandPack layout helpers to office picker)"
```

---

## Task 6: Wire office to depend on `feinschmiede`; sync; full suite green (Phase 1a gate)

**Files:**
- Modify: `feinschliff/pyproject.toml`
- Create: `feinschmiede/tests/test_engine_smoke.py`

- [ ] **Step 1: Add the `feinschmiede` workspace dependency to office**

In `feinschliff/pyproject.toml`, add `"feinschmiede"` to `dependencies` and declare the workspace source. Add under `[project] dependencies` the line `"feinschmiede",`, and add this block:

```toml
[tool.uv.sources]
feinschmiede = { workspace = true }
```

- [ ] **Step 2: Write an engine smoke test (TDD: this is the engine's own regression anchor)**

Create `feinschmiede/tests/test_engine_smoke.py`:

```python
"""Engine imports standalone (no feinschliff) and the public surface resolves."""

import importlib


def test_engine_imports_without_feinschliff():
    for mod in [
        "feinschmiede",
        "feinschmiede.diagrams.svg_expand",
        "feinschmiede.diagrams.excalidraw_expand",
        "feinschmiede.diagrams.render",
        "feinschmiede.diagrams.brand_bridge",
        "feinschmiede.brand_discovery",
        "feinschmiede.dsl.ast",
        "feinschmiede.dsl.tokens",
    ]:
        importlib.import_module(mod)


def test_no_feinschliff_import_in_engine_source():
    # Only IMPORT statements are forbidden — the engine legitimately keeps
    # `feinschliff` string literals (default brand name, the Excalidraw
    # `"source": "feinschliff"` field, the FEINSCHLIFF_BRAND* env vars).
    import pathlib
    import re

    pat = re.compile(r"^\s*(from|import)\s+feinschliff\b", re.MULTILINE)
    root = pathlib.Path(__file__).resolve().parents[1] / "feinschmiede"
    offenders = [
        str(p.relative_to(root))
        for p in root.rglob("*.py")
        if pat.search(p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"engine imports feinschliff: {offenders}"
```

- [ ] **Step 3: Sync the workspace and run the engine smoke test**

```bash
cd "$R"
uv sync
uv run --package feinschmiede pytest feinschmiede/tests/test_engine_smoke.py -v
```
Expected: both tests PASS. If `test_no_feinschliff_import_in_engine_source` fails, fix the named files (a residual `feinschliff` reference in an engine module — likely a missed back-edge or a docstring) and re-run.

- [ ] **Step 4: Run the FULL existing office suite — the Phase 1a gate**

```bash
cd "$R"
uv run --package feinschliff pytest feinschliff/tests -q
```
Expected: the entire suite PASSES (same count as before the extraction). Investigate and fix any failure before proceeding — do not continue with a red suite. Common causes: a missed import rewrite (grep the traceback's module), or the `deck/picker.py` back-edge inlining signature mismatch.

- [ ] **Step 5: Lint**

```bash
cd "$R"
uvx ruff check feinschmiede feinschliff/feinschliff
```
Expected: `All checks passed!` (fix any unused-import left by the back-edge severance).

- [ ] **Step 6: Commit the Phase 1a gate**

```bash
cd "$R"
git add -A
git commit -s -m "feat(feinschmiede): office depends on feinschmiede engine; full suite green (Phase 1a gate)"
```

---

## Task 7: Scaffold the `feinbild` plugin + launcher (reuse the feinklang template)

**Files:**
- Create: `feinbild/.claude-plugin/plugin.json`, `feinbild/pyproject.toml`, `feinbild/bin/feinbild`, `feinbild/build-wheels.sh`, `feinbild/src/feinbild/__init__.py`, `feinbild/src/feinbild/env.py`

- [ ] **Step 1: Copy feinklang's launcher + env helper as the feinbild template**

```bash
cd "$R"
mkdir -p feinbild/bin feinbild/src/feinbild feinbild/.claude-plugin feinbild/skills feinbild/commands
sed 's/feinklang/feinbild/g' feinklang/bin/feinklang > feinbild/bin/feinbild
chmod +x feinbild/bin/feinbild
cp feinklang/src/feinklang/env.py feinbild/src/feinbild/env.py
```

- [ ] **Step 2: Make the launcher export the bundled brand path**

In `feinbild/bin/feinbild`, immediately before the final `exec "$CLI" "$@"` line, insert (so the engine's brand discovery finds feinbild's bundled packs without requiring user setup):

```bash
# Make feinbild's bundled brand packs discoverable by the engine (additive — keep any user path).
export FEINSCHLIFF_BRAND_PATH="${FEINSCHLIFF_BRAND_PATH:+$FEINSCHLIFF_BRAND_PATH:}$PLUGIN_ROOT/brands"
```

- [ ] **Step 3: Write `feinbild/pyproject.toml`**

```toml
[project]
name = "feinbild"
version = "0.1.0"
description = "Image / 2D for Claude Code — AI images, SVG, and Excalidraw diagrams via the `feinbild` CLI."
requires-python = ">=3.11"
license = "MIT"
authors = [{ name = "Mike Mueller", email = "mike@objektarium.de" }]
dependencies = [
    "feinschmiede",
    "requests>=2.31",
]

[project.scripts]
feinbild = "feinbild.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
include = ["feinbild*"]

[tool.uv.sources]
feinschmiede = { workspace = true }
```

- [ ] **Step 4: Add `feinbild` to the workspace members**

In root `pyproject.toml`, extend the members list to:

```toml
members = ["feinschmiede", "feinschliff", "feinschliff-builder", "feinbild"]
```

- [ ] **Step 5: Write `feinbild/.claude-plugin/plugin.json`**

```json
{
  "name": "feinbild",
  "description": "Image & 2D for Claude Code — AI image generation (Replicate/Gemini), SVG diagrams, and Excalidraw diagrams via the clean `feinbild` CLI. Part of the feinschmiede family.",
  "author": { "name": "Mike Mueller", "email": "mike@objektarium.de" },
  "license": "MIT",
  "keywords": ["image-generation", "diagram", "svg", "excalidraw", "replicate", "gemini", "claude-code", "claude-skills", "feinschmiede"]
}
```

- [ ] **Step 6: Write `feinbild/src/feinbild/__init__.py`**

```python
"""feinbild — image / 2D (AI images, SVG, Excalidraw) for the feinschmiede family.

The public surface is the `feinbild` console CLI, not these modules.
"""

__version__ = "0.1.0"
```

- [ ] **Step 7: Commit the scaffold**

```bash
cd "$R"
git add feinbild pyproject.toml
git commit -s -m "feat(feinbild): scaffold image plugin + launcher (feinschmiede engine consumer)"
```

---

## Task 8: feinbild diagram subcommands (`svg`/`excalidraw expand|render`)

**Files:**
- Create: `feinbild/src/feinbild/diagrams_cli.py`
- Test: `feinbild/tests/test_diagrams_cli.py`

- [ ] **Step 1: Write a failing test for the expand→render flow**

Create `feinbild/tests/test_diagrams_cli.py`:

```python
from pathlib import Path

from feinbild import diagrams_cli

OTA = """canvas 1720x480
text title 100,40 "How a Device Gets Updated" size:title
ellipse cloud 80,180 280x160 "Cloud" fill:start
box check    480,180 280x160 "Device\\nChecks" fill:primary
box install  880,180 280x160 "Device\\nInstalls" fill:secondary
box restart  1280,180 320x160 "Device\\nRestarts" fill:end
arrow cloud -> check    label:"sends update"
arrow check -> install  label:"OK"
arrow install -> restart label:"safely"
"""


def test_excalidraw_expand_then_render(tmp_path: Path):
    src = tmp_path / "ota.exc.dsl"
    src.write_text(OTA)
    exc = tmp_path / "ota.excalidraw"
    png = tmp_path / "ota.png"
    assert diagrams_cli.cmd_excalidraw_expand(src, exc, brand="feinschliff") == 0
    assert exc.read_text().startswith("{")  # Excalidraw JSON
    assert diagrams_cli.cmd_render(exc, png) == 0
    assert png.stat().st_size > 200  # real PNG bytes
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd "$R" && uv run --package feinbild pytest feinbild/tests/test_diagrams_cli.py -q
```
Expected: FAIL (`ModuleNotFoundError: feinbild.diagrams_cli` / `cmd_* not defined`).

- [ ] **Step 3: Implement `diagrams_cli.py` calling the engine functions directly**

Create `feinbild/src/feinbild/diagrams_cli.py`:

```python
"""feinbild diagram subcommands — thin wrappers over the feinschmiede engine.

`expand` resolves brand colors (DSL string -> SVG/Excalidraw string); `render`
rasterizes an already-expanded .svg/.excalidraw to PNG (brand-agnostic). We call
the engine's public functions directly — never shell out, never import the
render backends (render keeps its lazy rough-first / playwright-fallback logic).
"""

from __future__ import annotations

import sys
from pathlib import Path

from feinschmiede.diagrams import excalidraw_expand, svg_expand
from feinschmiede.diagrams.brand_bridge import resolve_brand_dir, strip_brand_directive
from feinschmiede.diagrams.render import render as _render


def _expand(expander, src: Path, out: Path | None, brand: str | None, expanded_suffix: str, dsl_suffix: str) -> int:
    dsl, directive = strip_brand_directive(src.read_text())
    brand_dir = resolve_brand_dir(directive=directive, cli_flag=brand)
    out = out or src.with_name(src.name.replace(dsl_suffix, expanded_suffix))
    out.write_text(expander.expand(dsl, brand_dir))
    print(f"feinbild: wrote {out}", file=sys.stderr)
    return 0


def cmd_svg_expand(src: Path, out: Path | None = None, brand: str | None = None) -> int:
    return _expand(svg_expand, src, out, brand, ".svg", ".svg.dsl")


def cmd_excalidraw_expand(src: Path, out: Path | None = None, brand: str | None = None) -> int:
    return _expand(excalidraw_expand, src, out, brand, ".excalidraw", ".exc.dsl")


def cmd_render(src: Path, out: Path | None = None) -> int:
    out = out or src.with_suffix(".png")
    _render(src, out)
    print(f"feinbild: wrote {out}", file=sys.stderr)
    return 0
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
cd "$R" && uv run --package feinbild pytest feinbild/tests/test_diagrams_cli.py -q
```
Expected: PASS (renders a real PNG via the pure rough+cairosvg path). If it errors with a cairo/`OSError` about libcairo, the engine deps are present in the workspace venv — confirm `uv sync` ran.

- [ ] **Step 5: Commit**

```bash
cd "$R"
git add feinbild/src/feinbild/diagrams_cli.py feinbild/tests/test_diagrams_cli.py
git commit -s -m "feat(feinbild): svg/excalidraw expand+render subcommands over the engine"
```

---

## Task 9: feinbild `imagine` subcommand (Replicate + Gemini, requests-based)

**Files:**
- Create: `feinbild/src/feinbild/images.py`
- Test: `feinbild/tests/test_images.py`

- [ ] **Step 1: Write a failing unit test for provider dispatch + key-missing behavior**

Create `feinbild/tests/test_images.py`:

```python
import pytest

from feinbild import images


def test_unknown_provider_raises():
    with pytest.raises(images.ImagineError):
        images.generate(prompt="x", provider="nope", model=None, aspect_ratio="1:1", out_path=None, api_keys={})


def test_replicate_requires_key():
    with pytest.raises(images.ImagineError) as e:
        images.generate(prompt="x", provider="replicate", model=None, aspect_ratio="1:1", out_path=None, api_keys={})
    assert "REPLICATE_API_KEY" in str(e.value)


def test_default_models():
    assert images.default_model("replicate") == "black-forest-labs/flux-schnell"
    assert images.default_model("gemini") == "gemini-2.5-flash-image"
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd "$R" && uv run --package feinbild pytest feinbild/tests/test_images.py -q
```
Expected: FAIL (`ModuleNotFoundError: feinbild.images`).

- [ ] **Step 3: Implement `images.py` (faithful port of `imagine.sh`)**

Create `feinbild/src/feinbild/images.py`:

```python
"""AI image generation — Replicate + Gemini providers (ported from imagine.sh).

`requests` instead of curl/jq; same endpoints, defaults, and output behavior.
Diagnostic lines go to stderr; the machine-readable result line goes to stdout.
No Unsplash provider exists; an absent UNSPLASH_ACCESS_KEY costs nothing.
"""

from __future__ import annotations

import base64
from pathlib import Path

import requests

_DEFAULT_MODEL = {"replicate": "black-forest-labs/flux-schnell", "gemini": "gemini-2.5-flash-image"}


class ImagineError(RuntimeError):
    """Usage/API error; the CLI prints it to stderr and exits 1."""


def default_model(provider: str) -> str:
    try:
        return _DEFAULT_MODEL[provider]
    except KeyError:
        raise ImagineError(f"Unknown provider '{provider}'. Use: replicate, gemini")


def _replicate_format(model: str) -> str:
    return "png" if any(t in model for t in ("kontext", "fill", "redux")) else "webp"


def generate(*, prompt: str, provider: str, model: str | None, aspect_ratio: str, out_path: Path | None, api_keys: dict) -> Path:
    if provider not in _DEFAULT_MODEL:
        raise ImagineError(f"Unknown provider '{provider}'. Use: replicate, gemini")
    model = model or default_model(provider)
    if provider == "replicate":
        return _replicate(prompt, model, aspect_ratio, out_path, api_keys.get("REPLICATE_API_KEY"))
    return _gemini(prompt, model, aspect_ratio, out_path, api_keys.get("GEMINI_API_KEY"))


def _replicate(prompt, model, aspect_ratio, out_path, key) -> Path:
    if not key:
        raise ImagineError("REPLICATE_API_KEY not set in ~/.env")
    fmt = _replicate_format(model)
    resp = requests.post(
        f"https://api.replicate.com/v1/models/{model}/predictions",
        headers={"Prefer": "wait", "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"input": {"prompt": prompt, "aspect_ratio": aspect_ratio, "output_format": fmt, "go_fast": True}},
        timeout=300,
    )
    data = resp.json()
    if data.get("status") != "succeeded":
        raise ImagineError(f"Replicate returned status '{data.get('status', 'unknown')}': {data.get('error') or data.get('detail') or data}")
    output = data.get("output")
    url = output[0] if isinstance(output, list) else output
    if not url:
        raise ImagineError("No image URL in Replicate response")
    out = out_path or Path(f"/tmp/imagine.{fmt}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(requests.get(url, timeout=120).content)
    return out


def _gemini(prompt, model, aspect_ratio, out_path, key) -> Path:
    if not key:
        raise ImagineError("GEMINI_API_KEY not set in ~/.env")
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect_ratio}},
        },
        timeout=300,
    )
    data = resp.json()
    if data.get("error", {}).get("message"):
        raise ImagineError(f"Gemini API: {data['error']['message']}")
    b64 = None
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if part.get("inlineData"):
            b64 = part["inlineData"]["data"]
            break
    if not b64:
        raise ImagineError("No image data in Gemini response")
    out = out_path or Path("/tmp/imagine.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(b64))
    return out
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
cd "$R" && uv run --package feinbild pytest feinbild/tests/test_images.py -q
```
Expected: PASS (no network — only dispatch + key-missing paths are exercised).

- [ ] **Step 5: Commit**

```bash
cd "$R"
git add feinbild/src/feinbild/images.py feinbild/tests/test_images.py
git commit -s -m "feat(feinbild): imagine subcommand (Replicate + Gemini, requests-based)"
```

---

## Task 10: feinbild CLI entry point (argparse wiring all subcommands)

**Files:**
- Create: `feinbild/src/feinbild/cli.py`
- Test: `feinbild/tests/test_cli.py`

- [ ] **Step 1: Write a failing test for argument wiring**

Create `feinbild/tests/test_cli.py`:

```python
import pytest

from feinbild import cli


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0
    assert "feinbild" in capsys.readouterr().out


def test_imagine_unknown_provider_exits_1(capsys):
    rc = cli.main(["imagine", "--prompt", "x", "--provider", "nope"])
    assert rc == 1
    assert "Unknown provider" in capsys.readouterr().err


def test_svg_subcommands_parse():
    parser = cli.build_parser()
    args = parser.parse_args(["svg", "expand", "chart.svg.dsl", "--brand", "feinschliff"])
    assert args.command == "svg" and args.sub == "expand"
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd "$R" && uv run --package feinbild pytest feinbild/tests/test_cli.py -q
```
Expected: FAIL (`ModuleNotFoundError: feinbild.cli`).

- [ ] **Step 3: Implement `cli.py`**

Create `feinbild/src/feinbild/cli.py`:

```python
"""feinbild command-line interface.

Subcommands:
  imagine                       — generate an AI image (Replicate / Gemini)
  svg expand|render             — .svg.dsl -> .svg (brand-resolved) -> .png
  excalidraw expand|render      — .exc.dsl -> .excalidraw (brand-resolved) -> .png

This CLI is feinbild's only public surface; other plugins call it as a bare
command. Diagram subcommands shell into the feinschmiede engine; `expand` takes
--brand, `render` does not (render is brand-agnostic). Theme stays in the DSL.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__, diagrams_cli, images
from .env import load_home_env


def _cmd_imagine(args: argparse.Namespace) -> int:
    if not args.prompt:
        print("Error: 'prompt' is required.", file=sys.stderr)
        return 1
    out = Path(args.out) if args.out else None
    keys = {k: os.environ.get(k) for k in ("REPLICATE_API_KEY", "GEMINI_API_KEY")}
    try:
        path = images.generate(prompt=args.prompt, provider=args.provider, model=args.model,
                               aspect_ratio=args.aspect_ratio, out_path=out, api_keys=keys)
    except images.ImagineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    size = path.stat().st_size
    print(f"Generated: {path} ({size} bytes)")
    print(f"Provider: {args.provider} | Model: {args.model or images.default_model(args.provider)}")
    return 0


def _cmd_svg(args: argparse.Namespace) -> int:
    out = Path(args.out) if args.out else None
    if args.sub == "expand":
        return diagrams_cli.cmd_svg_expand(Path(args.input), out, args.brand)
    return diagrams_cli.cmd_render(Path(args.input), out)


def _cmd_excalidraw(args: argparse.Namespace) -> int:
    out = Path(args.out) if args.out else None
    if args.sub == "expand":
        return diagrams_cli.cmd_excalidraw_expand(Path(args.input), out, args.brand)
    return diagrams_cli.cmd_render(Path(args.input), out)


def _add_diagram_group(sub, name: str, dsl_help: str, expanded_help: str) -> None:
    g = sub.add_parser(name, help=f"{name} diagrams: expand a DSL then render to PNG.")
    leaf = g.add_subparsers(dest="sub", required=True)
    e = leaf.add_parser("expand", help=f"Expand {dsl_help} to {expanded_help} (resolves brand colors).")
    e.add_argument("input")
    e.add_argument("-o", "--out", dest="out")
    e.add_argument("--brand", help="Brand override (else @brand directive / FEINSCHLIFF_BRAND / default).")
    r = leaf.add_parser("render", help=f"Render {expanded_help} to PNG.")
    r.add_argument("input")
    r.add_argument("-o", "--out", dest="out")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="feinbild", description="Image / 2D CLI (feinschmiede / feinbild).")
    parser.add_argument("--version", action="version", version=f"feinbild {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    im = sub.add_parser("imagine", help="Generate an AI image.")
    im.add_argument("--prompt", required=True)
    # No argparse choices: an unknown provider must reach images.generate so it
    # raises ImagineError (clean exit 1), matching imagine.sh's dispatch error.
    im.add_argument("--provider", default="replicate")
    im.add_argument("--model", default=None)
    im.add_argument("--aspect-ratio", dest="aspect_ratio", default="1:1")
    im.add_argument("-o", "--out", dest="out")
    im.set_defaults(func=_cmd_imagine)

    _add_diagram_group(sub, "svg", ".svg.dsl", ".svg")
    _add_diagram_group(sub, "excalidraw", ".exc.dsl", ".excalidraw")
    sub.choices["svg"].set_defaults(func=_cmd_svg)
    sub.choices["excalidraw"].set_defaults(func=_cmd_excalidraw)
    return parser


def main(argv: list[str] | None = None) -> int:
    load_home_env()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Run the test to confirm it passes**

```bash
cd "$R" && uv run --package feinbild pytest feinbild/tests/test_cli.py -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd "$R"
git add feinbild/src/feinbild/cli.py feinbild/tests/test_cli.py
git commit -s -m "feat(feinbild): argparse CLI wiring imagine + svg/excalidraw subcommands"
```

---

## Task 11: Bundle a brand pack, build the wheelhouse, write skills/commands/README

**Files:**
- Create: `feinbild/brands/feinschliff/` (copy), `feinbild/build-wheels.sh`, `feinbild/skills/{imagine,svg,excalidraw}/SKILL.md`, `feinbild/commands/{imagine,svg,excalidraw}.md`, `feinbild/README.md`

- [ ] **Step 1: Bundle the baseline brand pack**

```bash
cd "$R"
mkdir -p feinbild/brands
cp -r feinschliff/brands/feinschliff feinbild/brands/feinschliff
test -f feinbild/brands/feinschliff/tokens.json && echo "bundled brand OK"
```

- [ ] **Step 2: Write `feinbild/build-wheels.sh` (feinbild + engine + deps)**

Create `feinbild/build-wheels.sh` (executable). It builds two workspace wheels (`feinbild`, `feinschmiede`) and vendors the runtime dep closure:

```bash
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

echo "feinbild: wheelhouse ready ($(find "$WHEELS" -name '*.whl' | wc -l | tr -d ' ') wheels) in $WHEELS"
```

```bash
cd "$R" && chmod +x feinbild/build-wheels.sh && ./feinbild/build-wheels.sh
```
Expected: builds both wheels, vendors deps, prints `feinbild: wheelhouse ready (… wheels)`. (cairosvg pulls `cairocffi`/`cssselect2`/`tinycss2`/`cffi`/`pycparser`/`defusedxml`/`webencodings`/`pillow`; that's expected.)

- [ ] **Step 3: Write the three SKILL.md files (CLI-only, no file paths)**

Create `feinbild/skills/svg/SKILL.md`:

```markdown
---
name: svg
description: Generate SVG diagrams from a compact DSL with brand-resolved colors. Use for charts, flows, and schematic 2D graphics.
---

# feinbild — SVG diagrams

`feinbild` is a command on your PATH. Two steps: expand a `.svg.dsl` to `.svg`
(brand colors resolved), then render to PNG.

```bash
feinbild svg expand chart.svg.dsl --brand feinschliff   # -> chart.svg
feinbild svg render chart.svg                           # -> chart.png
```

`--brand` (or a leading `@brand <name>` line in the DSL) selects the brand;
`render` takes no brand (it consumes already-resolved colors). Write outputs
into the project so other plugins can consume them.
```

Create `feinbild/skills/excalidraw/SKILL.md`:

```markdown
---
name: excalidraw
description: Generate Excalidraw diagrams from a compact DSL with brand-resolved colors. Use for boxes/arrows flow diagrams.
---

# feinbild — Excalidraw diagrams

`feinbild` is a command on your PATH. Expand a `.exc.dsl` to `.excalidraw`
(brand colors resolved), then render to PNG.

```bash
feinbild excalidraw expand flow.exc.dsl --brand feinschliff   # -> flow.excalidraw
feinbild excalidraw render flow.excalidraw                    # -> flow.png
```

Primitives: `box ellipse diamond dot line zone lane text` and
`arrow <from> -> <to> [label:"…"]`. Set `theme dark` in the DSL for a dark
canvas. `--brand` selects the brand; `render` is brand-agnostic.
```

Create `feinbild/skills/imagine/SKILL.md`:

```markdown
---
name: imagine
description: Generate AI images via Replicate or Gemini. Use to create illustrations, photos, or graphics from a text prompt.
---

# feinbild — AI image generation

`feinbild` is a command on your PATH. Requires a provider key in `~/.env`
(`REPLICATE_API_KEY` or `GEMINI_API_KEY`).

```bash
feinbild imagine --prompt "a calm mountain lake at dawn" --out lake.webp
feinbild imagine --prompt "logo, flat, blue" --provider gemini --aspect-ratio 16:9 --out logo.png
```

Options: `--provider` (`replicate` default, or `gemini`), `--model`
(default `black-forest-labs/flux-schnell` / `gemini-2.5-flash-image`),
`--aspect-ratio` (`1:1` default, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`),
`--out`. Without a key the command prints a clean error and makes no paid call.
```

- [ ] **Step 4: Write the three thin command wrappers**

Create `feinbild/commands/svg.md`:

```markdown
---
name: svg
description: "Generate an SVG diagram from a .svg.dsl. Usage: /svg <file.svg.dsl>"
user_invocable: true
---

# /svg

Expand then render the user's `.svg.dsl` with the `feinbild` CLI:

```bash
feinbild svg expand "<file>.svg.dsl" --brand "${FEINBILD_BRAND:-feinschliff}"
feinbild svg render "<file>.svg"
```

`feinbild` is on PATH — call it as a bare command; never use a file path.
```

Create `feinbild/commands/excalidraw.md`:

```markdown
---
name: excalidraw
description: "Generate an Excalidraw diagram from a .exc.dsl. Usage: /excalidraw <file.exc.dsl>"
user_invocable: true
---

# /excalidraw

Expand then render the user's `.exc.dsl` with the `feinbild` CLI:

```bash
feinbild excalidraw expand "<file>.exc.dsl" --brand "${FEINBILD_BRAND:-feinschliff}"
feinbild excalidraw render "<file>.excalidraw"
```

`feinbild` is on PATH — call it as a bare command; never use a file path.
```

Create `feinbild/commands/imagine.md`:

```markdown
---
name: imagine
description: "Generate an AI image from a prompt. Usage: /imagine <prompt>"
user_invocable: true
---

# /imagine

Generate an image with the `feinbild` CLI:

```bash
feinbild imagine --prompt "<user prompt>" --out "${CLAUDE_PROJECT_DIR:-.}/image.webp"
```

Pass through `--provider`, `--model`, `--aspect-ratio`, `--out` if given. If no
key is set the command prints a clear error and makes no paid call.
```

- [ ] **Step 5: Write `feinbild/README.md`**

```markdown
# feinbild

Image & 2D for Claude Code — AI image generation (Replicate/Gemini), SVG, and
Excalidraw diagrams behind the clean `feinbild` CLI. Part of the feinschmiede
family; consumes the shared `feinschmiede` engine as a bundled wheel.

```bash
feinbild imagine --prompt "a red bicycle" --out bike.webp
feinbild svg expand chart.svg.dsl --brand feinschliff && feinbild svg render chart.svg
feinbild excalidraw expand flow.exc.dsl && feinbild excalidraw render flow.excalidraw
```

Diagram brand colors resolve through the engine; the launcher adds
`feinbild/brands/` to `FEINSCHLIFF_BRAND_PATH`. Rebuild the offline wheelhouse
with `./build-wheels.sh`.
```

- [ ] **Step 6: Commit**

```bash
cd "$R"
git add feinbild/brands feinbild/build-wheels.sh feinbild/skills feinbild/commands feinbild/README.md
git commit -s -m "feat(feinbild): bundled brand, wheelhouse builder, skills/commands/README"
```

---

## Task 12: feinbild gate — verify from a fresh plugin venv

**Files:** none (verification). Writes intermediates to `feinbild/.debug/` (gitignored).

- [ ] **Step 1: Copy a real fixture and run the full chain through the launcher (fresh venv)**

```bash
cd "$R"
mkdir -p feinbild/.debug/gate
cp feinschliff/skills/excalidraw/examples/ota-update-simple-pupil.exc.dsl feinbild/.debug/gate/ota.exc.dsl
rm -rf feinbild/.debug/plugin-data
export CLAUDE_PLUGIN_ROOT="$PWD/feinbild"
export CLAUDE_PLUGIN_DATA="$PWD/feinbild/.debug/plugin-data"

# First run bootstraps the venv offline from bundled wheels, then runs the CLI:
feinbild/bin/feinbild excalidraw expand feinbild/.debug/gate/ota.exc.dsl -o feinbild/.debug/gate/ota.excalidraw --brand feinschliff
feinbild/bin/feinbild excalidraw render feinbild/.debug/gate/ota.excalidraw -o feinbild/.debug/gate/ota.png
file feinbild/.debug/gate/ota.png
```
Expected: first run prints the venv-bootstrap line; `ota.excalidraw` is JSON; `ota.png` is reported by `file` as a PNG image (>10 KB). This proves the **engine wheel runs inside feinbild's own venv** — the Phase-1 risk.

- [ ] **Step 2: SVG path + brand resolution**

```bash
cd "$R"
printf '@brand feinschliff\ncanvas 400x200\nrect a 20,20 160x80 fill:primary\ntext t 40,60 "Hi" \n' > feinbild/.debug/gate/mini.svg.dsl
feinbild/bin/feinbild svg expand feinbild/.debug/gate/mini.svg.dsl -o feinbild/.debug/gate/mini.svg
feinbild/bin/feinbild svg render feinbild/.debug/gate/mini.svg -o feinbild/.debug/gate/mini.png
grep -q "fill=\"#" feinbild/.debug/gate/mini.svg && echo "brand colors resolved ✓"
file feinbild/.debug/gate/mini.png
```
Expected: the `.svg` contains resolved `fill="#…"` hex (brand tokens resolved), `mini.png` is a PNG. (If the `text` primitive needs different syntax, adjust to a `rect`-only fixture — the goal is a brand-resolved render.)

- [ ] **Step 3: imagine clean key-missing error (no paid call)**

```bash
cd "$R"
env -u REPLICATE_API_KEY HOME="$PWD/feinbild/.debug/nohome" \
  CLAUDE_PLUGIN_ROOT="$PWD/feinbild" CLAUDE_PLUGIN_DATA="$PWD/feinbild/.debug/plugin-data" PATH="$PATH" \
  feinbild/bin/feinbild imagine --prompt "x" --provider replicate; echo "exit=$?"
```
Expected: prints `Error: REPLICATE_API_KEY not set in ~/.env` and `exit=1` — no network call.

- [ ] **Step 4: Confirm no `lib.diagrams` strings and no `cd /path/to/feinschliff` remain in the diagram path**

```bash
cd "$R"
grep -rn "lib\.diagrams" feinbild feinschmiede feinschliff/skills 2>/dev/null && echo "FAIL: lib.diagrams remains" || echo "no lib.diagrams ✓"
```
Expected: `no lib.diagrams ✓`.

- [ ] **Step 5: Run the feinbild unit suite + lint**

```bash
cd "$R"
uv run --package feinbild pytest feinbild/tests -q
uvx ruff check feinbild/src/feinbild
```
Expected: all PASS / `All checks passed!`.

- [ ] **Step 6: Add feinbild to the umbrella marketplace + commit the gate**

Add to `.claude-plugin/marketplace.json` `plugins` array:

```json
{ "name": "feinbild", "description": "Image & 2D — AI images (Replicate/Gemini), SVG, and Excalidraw diagrams via the `feinbild` CLI.", "source": "./feinbild" }
```

```bash
cd "$R"
git add .claude-plugin/marketplace.json
git commit -s -m "feat(feinbild): list in umbrella marketplace; Phase 1b gate verified"
```

---

## Task 13: Final verification (whole-repo regression)

- [ ] **Step 1: Run every workspace package's tests + lint**

```bash
cd "$R"
uv sync
uv run --package feinschmiede pytest feinschmiede/tests -q
uv run --package feinschliff  pytest feinschliff/tests  -q
uv run --package feinbild      pytest feinbild/tests      -q
uvx ruff check feinschmiede feinschliff/feinschliff feinbild/src/feinbild feinklang/src/feinklang
```
Expected: all green. The `feinschliff lib tests` suite count matches pre-extraction.

- [ ] **Step 2: Verify git discipline (no artifacts tracked)**

```bash
cd "$R"
git status --porcelain | grep -E '\.(whl|png|webp|excalidraw)$|/\.debug/|/wheels/|/venv/' && echo "FAIL artifact tracked" || echo "clean ✓"
```
Expected: `clean ✓`.

- [ ] **Step 3: Verify feinklang still passes its Phase-0 gate at the new root location**

```bash
cd "$R"
rm -rf feinklang/.debug/plugin-data
CLAUDE_PLUGIN_ROOT="$PWD/feinklang" CLAUDE_PLUGIN_DATA="$PWD/feinklang/.debug/plugin-data" \
  feinklang/bin/feinklang --version
```
Expected: bootstraps + prints `feinklang 0.1.0`.

---

## Self-review notes (for the executor)

- **Spec coverage:** Phase 1a (engine extraction) = Tasks 2–6; back-edge severance = Task 5; Phase 1b (feinbild) = Tasks 7–12; Phase-0 tidy = Task 1; whole-repo regression = Task 13. The `feinschliff lib tests` check name is untouched (tests stay under `feinschliff/tests/`).
- **Deferred (NOT this plan, per the design):** converting the office `feinschliff` plugin to the launcher/bundled-wheel model; removing the now-duplicated svg/excalidraw/imagine skills from the office plugin; `feinschnitt` (video); PyPI cutover; renaming the `FEINSCHLIFF_BRAND_*` env vars.
- **Watch items:** the `deck/picker.py` back-edge inlining must match the real `layout_discovery` signatures (Task 5 Step 1 reads them first); the import-rewrite sanity greps (Task 4 Step 2) must both print `NONE ✓` before continuing; the Phase-1a gate (Task 6 Step 4) is a hard stop — do not start feinbild with a red office suite.
