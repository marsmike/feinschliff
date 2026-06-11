"""Content-hash render cache in expand_diagram_blocks.

Artifacts are content-hash-named (`s{idx}-{id}-{hash}.{svg,excalidraw,png}`)
and the hash fully determines the render output, so an unchanged diagram must
reuse its existing artifact + PNG instead of re-rendering (~150 ms rough /
~1.5 s Playwright per diagram, every build). Stale artifacts from a CHANGED
diagram must still be deleted so the structural-lint globs in pipeline.py
never lint an outdated file as current.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.expander import expand_diagram_blocks

BRAND_DIR = Path(__file__).resolve().parent.parent / "brands" / "feinschliff"


def _parse(geom: str = "100,200 800x400",
           body: str = "rect bg 0,0 800x400 paper"):
    src = f"""
canvas 1920x1080
svg chart {geom} {{
  {body}
}}
"""
    nodes, _ = parse_lines(src)
    return nodes


def _parse_two(volatile_body: str):
    """Two diagrams on the SAME slide: `stable` never changes, `volatile`
    varies per test step."""
    src = f"""
canvas 1920x1080
svg stable 100,100 400x300 {{
  rect bg 0,0 400x300 paper
}}
svg volatile 600,100 400x300 {{
  {volatile_body}
}}
"""
    nodes, _ = parse_lines(src)
    return nodes


def _counting_render(monkeypatch):
    """Wrap feinschmiede.diagrams.render.render with a call counter.

    The expander resolves `render` through the module at call time, so this
    intercepts every actual render while preserving real output.
    """
    import feinschmiede.diagrams.render as render_mod

    calls: list[str] = []
    real = render_mod.render

    def counting(src, dst, **kw):
        calls.append(Path(src).name)
        return real(src, dst, **kw)

    monkeypatch.setattr(render_mod, "render", counting)
    return calls


def _expand(nodes, out_dir, slide_index: int = 1):
    # render() requires cairo or playwright which may not be installed
    # locally; skip (same pattern as test_dsl_primitive_diagrams.py) instead
    # of failing on a missing system backend.
    try:
        return expand_diagram_blocks(
            nodes, brand_dir=BRAND_DIR, out_dir=out_dir,
            slide_index=slide_index,
        )
    except (OSError, ImportError, ModuleNotFoundError) as exc:
        pytest.skip(f"rendering backend unavailable ({exc})")


def test_second_expand_skips_render(tmp_path, monkeypatch):
    """Same nodes, same out_dir, same slide: second expansion is a cache hit
    and must not call render() again — but must still produce a full picture
    node (geometry, src, _diagram_meta with wireframe primitives)."""
    calls = _counting_render(monkeypatch)

    _expand(_parse(), tmp_path)
    expanded = _expand(_parse(), tmp_path)

    assert len(calls) == 1, f"expected 1 render, got {len(calls)}: {calls}"

    pics = [n for n in expanded if n.kind == "picture"]
    assert len(pics) == 1
    pic = pics[0]
    assert pic.kw_args["x"] == 100
    assert pic.kw_args["w"] == 800
    src = Path(pic.kw_args["src"])
    assert src.suffix == ".png" and src.exists()
    meta = pic.kw_args["_diagram_meta"]
    assert meta["kind"] == "svg"
    assert meta["internal_primitives"], "prims must be rebuilt on cache hit"


def test_changed_body_rerenders_and_drops_stale(tmp_path, monkeypatch):
    """Changing the body (same id, same slide) re-renders AND removes the
    old-hash artifacts so the structural-lint globs never see them."""
    calls = _counting_render(monkeypatch)

    _expand(_parse(body="rect bg 0,0 800x400 paper"), tmp_path)
    old_files = {p.name for p in tmp_path.glob("s1-chart-*")}
    assert old_files, "first expansion must write artifacts"

    _expand(_parse(body="rect bg 0,0 700x300 paper"), tmp_path)
    assert len(calls) == 2
    assert calls[0] != calls[1], "different bodies must produce different hash names"

    remaining = {p.name for p in tmp_path.glob("s1-chart-*")}
    assert remaining, "second expansion must write new artifacts"
    assert not old_files & remaining, (
        f"stale old-hash artifacts survived cleanup: {old_files & remaining}"
    )


def test_cache_key_change_invalidates(tmp_path, monkeypatch):
    """Same body, different slot geometry (w×h is part of the cache key):
    must re-render rather than reuse the differently-sized PNG."""
    calls = _counting_render(monkeypatch)

    _expand(_parse(geom="100,200 800x400"), tmp_path)
    _expand(_parse(geom="100,200 640x400"), tmp_path)

    assert len(calls) == 2, f"expected 2 renders, got {len(calls)}: {calls}"


def test_unchanged_sibling_survives_partial_change(tmp_path, monkeypatch):
    """Two diagrams on one slide; only one changes. The unchanged sibling's
    artifacts must survive the stale cleanup AND skip re-render."""
    calls = _counting_render(monkeypatch)

    _expand(_parse_two("rect bg 0,0 380x280 paper"), tmp_path)
    assert len(calls) == 2
    stable_files = {p.name for p in tmp_path.glob("s1-stable-*")}
    volatile_old = {p.name for p in tmp_path.glob("s1-volatile-*")}
    assert stable_files and volatile_old

    _expand(_parse_two("rect bg 0,0 200x150 paper"), tmp_path)
    assert len(calls) == 3, (
        f"only the changed diagram should re-render, got {len(calls)}: {calls}"
    )
    assert {p.name for p in tmp_path.glob("s1-stable-*")} == stable_files, (
        "unchanged sibling's artifacts must survive stale cleanup"
    )
    volatile_new = {p.name for p in tmp_path.glob("s1-volatile-*")}
    assert volatile_new and not volatile_old & volatile_new
