"""
Reachability analysis for feinschliff carve-out.
Computes carve manifests: which modules go to core, builder, extra.
Run from repo root: python _feinschliff/.debug/reachability.py
"""
from __future__ import annotations

import ast
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "_feinschliff"

# ── Builder-side modules (explicitly assigned) ──────────────────────────────
BUILDER_MODULES = {
    # CLI
    "cli/brand.py",
    "cli/compile.py",
    "cli/decompile.py",
    "cli/verify.py",
    "cli/verify_diagram.py",
    "cli/verify_quality.py",
    # DSL decompile helpers
    "lib/dsl/pptx_decompile.py",
    "lib/dsl/pptx_svg_decompile.py",
    "lib/dsl/svg_wireframe.py",
    # Diagrams
    "lib/diagrams/structural_validator.py",
}

# All of lib/verify/, lib/diagrams/refurbish/ go to builder
def _is_builder_path(rel: str) -> bool:
    return (
        rel in BUILDER_MODULES
        or rel.startswith("lib/verify/")
        or rel.startswith("lib/diagrams/refurbish/")
        or rel.startswith("scripts/")
        or rel.startswith("skills/compile/")
        or rel.startswith("skills/improve-brand/")
    )

# ── Core modules (explicitly assigned) ──────────────────────────────────────
CORE_CLI = {"cli/main.py", "cli/build.py", "cli/deck.py", "cli/ship.py"}
CORE_LIB_TOPS = {
    "lib/__init__.py",
    "lib/brand_discovery.py",
    "lib/content_validator.py",
    "lib/defects.py",
    "lib/design_md.py",
    "lib/diagnostics.py",
    "lib/jsonwalk.py",
    "lib/layout_budget.py",
    "lib/layout_discovery.py",
    "lib/layout_picker.py",
    "lib/layout_validator.py",
    "lib/pipeline_log.py",
    "lib/pipeline.py",
    "lib/slot_budget.py",
    "lib/textfit.py",
}

# ── Walk all Python files ────────────────────────────────────────────────────
def all_py_files():
    for root, _, files in os.walk(SRC):
        for f in files:
            if not f.endswith(".py"):
                continue
            full = Path(root) / f
            rel = full.relative_to(SRC).as_posix()
            # Skip egg-info, __pycache__
            if ".egg-info" in rel or "__pycache__" in rel or ".debug" in rel:
                continue
            yield rel


def classify():
    core, builder, other = [], [], []
    for rel in sorted(all_py_files()):
        if _is_builder_path(rel):
            builder.append(rel)
        elif (
            rel in CORE_CLI
            or rel in CORE_LIB_TOPS
            or rel.startswith("lib/brand/")
            or rel.startswith("lib/book/")
            or rel.startswith("lib/deck/")
            or rel.startswith("lib/dsl/")  # minus the decompile ones above
            or rel.startswith("lib/diagrams/")  # minus builder ones
            or rel.startswith("lib/io/")
            or rel.startswith("lib/schemas/")
            or rel.startswith("skills/deck/")
            or rel.startswith("skills/excalidraw/")
            or rel.startswith("skills/svg/")
        ):
            core.append(rel)
        else:
            other.append(rel)
    return core, builder, other


if __name__ == "__main__":
    core, builder, other = classify()
    print("=== CORE ===")
    for f in core:
        print(f"  {f}")
    print(f"\n  Total: {len(core)}")

    print("\n=== BUILDER ===")
    for f in builder:
        print(f"  {f}")
    print(f"\n  Total: {len(builder)}")

    print("\n=== OTHER (unclassified) ===")
    for f in other:
        print(f"  {f}")
    print(f"\n  Total: {len(other)}")

    # Extra brands
    print("\n=== EXTRA brands ===")
    extra_brands = [
        "binance", "catppuccin-latte", "catppuccin-macchiato", "ferrari",
        "feinschliff-dark", "gruvbox-dark", "nord", "solarized-dark",
        "spotify", "gs-ramspau",
    ]
    brands_dir = SRC / "brands"
    for b in sorted(brands_dir.iterdir()) if brands_dir.exists() else []:
        tag = "EXTRA" if b.name in extra_brands else "CORE" if b.name in ("feinschliff", "blank", "claude") else "SKIP (bsh/other)"
        print(f"  {b.name}: {tag}")
