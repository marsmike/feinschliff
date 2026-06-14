"""Regression: brand atlas mtime cache must walk the `extends:` chain.

Original bug (commit a823729): after PR #19 modified ink/graphite/steel in
the dark brands' tokens.json, `render_brand_atlas.py` reported "164 cached"
on a stale fleet. Root cause: `_cache_inputs_mtime` only looked at the
brand's own tokens.json, but every brand inherits via DESIGN.md
`extends:` — modifying the parent silently leaves the child cached.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent / "feinschliff-builder"
SCRIPT = REPO_ROOT / "scripts" / "render_brand_atlas.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("render_brand_atlas", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_brand_atlas"] = module
    spec.loader.exec_module(module)
    return module


def _make_brand(root: Path, name: str, *, extends: str | None = None) -> Path:
    brand = root / name
    brand.mkdir(parents=True, exist_ok=True)
    (brand / "tokens.json").write_text('{"colors": {}}')
    frontmatter = "---\nname: x\n"
    if extends:
        frontmatter += f"extends: {extends}\n"
    frontmatter += "---\n"
    (brand / "DESIGN.md").write_text(frontmatter)
    return brand


def _set_mtime(path: Path, mtime: float) -> None:
    os.utime(path, (mtime, mtime))


def test_brand_chain_walks_extends_to_root(tmp_path):
    mod = _load_script_module()
    brands = tmp_path / "brands"
    parent = _make_brand(brands, "feinschliff")
    child = _make_brand(brands, "feinschliff-dark", extends="feinschliff")
    chain = mod._brand_chain(child)
    assert [p.name for p in chain] == ["feinschliff-dark", "feinschliff"]
    chain_root = mod._brand_chain(parent)
    assert [p.name for p in chain_root] == ["feinschliff"]


def test_cache_invalidated_when_parent_tokens_change(tmp_path):
    """The bug: modifying parent tokens.json must invalidate child's cache."""
    mod = _load_script_module()
    brands = tmp_path / "brands"
    parent = _make_brand(brands, "feinschliff")
    child = _make_brand(brands, "feinschliff-dark", extends="feinschliff")

    layout = tmp_path / "layout.slide.dsl"
    layout.write_text("# layout")
    content = tmp_path / "content.yaml"
    content.write_text("title: x")
    out_png = tmp_path / "out.png"
    out_png.write_text("png-bytes")

    t0 = time.time() - 1000
    for p in [layout, content, out_png,
              parent / "tokens.json", parent / "DESIGN.md",
              child / "tokens.json", child / "DESIGN.md"]:
        _set_mtime(p, t0)

    _set_mtime(parent / "tokens.json", t0 + 500)

    job = mod.LayoutJob(
        brand="feinschliff-dark",
        layout_id="x",
        layout_path=layout,
        content_path=content,
        out_png=out_png,
        index=1,
    )
    inputs_mtime = mod._cache_inputs_mtime(job, child)
    assert inputs_mtime > out_png.stat().st_mtime, (
        "parent tokens.json mtime should propagate via extends chain; "
        f"got inputs_mtime={inputs_mtime}, png_mtime={out_png.stat().st_mtime}"
    )


def test_cache_invalidated_when_child_tokens_change(tmp_path):
    mod = _load_script_module()
    brands = tmp_path / "brands"
    _make_brand(brands, "feinschliff")
    child = _make_brand(brands, "feinschliff-dark", extends="feinschliff")

    layout = tmp_path / "layout.slide.dsl"
    layout.write_text("# layout")
    content = tmp_path / "content.yaml"
    content.write_text("title: x")
    out_png = tmp_path / "out.png"
    out_png.write_text("png-bytes")

    t0 = time.time() - 1000
    for p in [layout, content, out_png,
              brands / "feinschliff" / "tokens.json",
              brands / "feinschliff" / "DESIGN.md",
              child / "tokens.json", child / "DESIGN.md"]:
        _set_mtime(p, t0)

    _set_mtime(child / "tokens.json", t0 + 500)

    job = mod.LayoutJob(
        brand="feinschliff-dark",
        layout_id="x",
        layout_path=layout,
        content_path=content,
        out_png=out_png,
        index=1,
    )
    assert mod._cache_inputs_mtime(job, child) > out_png.stat().st_mtime


def test_cache_stable_when_unrelated_brand_changes(tmp_path, monkeypatch):
    """Touching sibling brand's tokens.json must NOT invalidate child's cache.

    Pins REPO_ROOT to an empty tmp dir so the shared-compound glob
    (REPO_ROOT/compounds/*.dsl) doesn't pick up the real repo's compound
    files — those carry recent checkout mtimes on CI and would dominate
    the max(...) returning a value newer than the synthetic baseline.
    """
    mod = _load_script_module()
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    brands = tmp_path / "brands"
    _make_brand(brands, "feinschliff")
    sibling = _make_brand(brands, "nord", extends="feinschliff")
    child = _make_brand(brands, "feinschliff-dark", extends="feinschliff")

    layout = tmp_path / "layout.slide.dsl"
    layout.write_text("# layout")
    content = tmp_path / "content.yaml"
    content.write_text("title: x")
    out_png = tmp_path / "out.png"
    out_png.write_text("png-bytes")

    t0 = time.time() - 1000
    for p in [layout, content, out_png,
              brands / "feinschliff" / "tokens.json",
              brands / "feinschliff" / "DESIGN.md",
              sibling / "tokens.json", sibling / "DESIGN.md",
              child / "tokens.json", child / "DESIGN.md"]:
        _set_mtime(p, t0)

    _set_mtime(sibling / "tokens.json", t0 + 500)

    job = mod.LayoutJob(
        brand="feinschliff-dark",
        layout_id="x",
        layout_path=layout,
        content_path=content,
        out_png=out_png,
        index=1,
    )
    assert mod._cache_inputs_mtime(job, child) == out_png.stat().st_mtime


def test_brand_chain_handles_missing_design_md(tmp_path):
    mod = _load_script_module()
    brands = tmp_path / "brands"
    brand = brands / "rootless"
    brand.mkdir(parents=True)
    (brand / "tokens.json").write_text("{}")
    chain = mod._brand_chain(brand)
    assert [p.name for p in chain] == ["rootless"]
