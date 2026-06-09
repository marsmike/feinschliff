"""Every DSL primitive the expander emits must render through render_rough
without silent unknown-element skipping. If the rough Python port can't
render a primitive, the dispatcher falls through to Playwright — never
silently."""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschmiede.diagrams.excalidraw_expand import expand


REPO_ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = REPO_ROOT / "brands" / "feinschliff"


PRIMITIVES = {
    "box":      'box b1 0,0 100x60 "box"',
    "ellipse":  'ellipse e1 0,0 100x60 "ellipse"',
    "diamond":  'diamond d1 0,0 100x60 "diamond"',
    "dot":      'dot dt1 50,50',
    "line":     'line l1 0,0 100,100',
    "line-dashed": 'line l2 0,0 100,100 dashed',
    "arrow":    'box a1 0,0 50x50 "a"\nbox a2 60,0 50x50 "b"\narrow a1 -> a2 label:"arrow label"',
    "text":     'text t1 50,50 "plain" level:title',
    "group":    'box g1 0,0 50x50 "x"\nbox g2 60,0 50x50 "y"\ngroup g1 g2',
}


@pytest.mark.parametrize("name,primitive_dsl", list(PRIMITIVES.items()),
                          ids=lambda x: x if isinstance(x, str) else "_")
def test_primitive_renders_or_falls_back_cleanly(name, primitive_dsl, tmp_path):
    dsl = f"canvas 800x600\n{primitive_dsl}\n"
    body_json = expand(dsl, brand_dir=BRAND_DIR)
    exc_path = tmp_path / f"{name}.excalidraw"
    exc_path.write_text(body_json)

    out_png = tmp_path / f"{name}.png"

    try:
        from feinschmiede.diagrams.render_rough import render_excalidraw as r_rough
    except ImportError:
        pytest.skip("rough not installed; cannot exercise primary path")

    try:
        r_rough(exc_path, out_png, style="clean")
    except (ImportError, OSError):
        # cairosvg / libcairo system library not available — skip.
        pytest.skip("cairosvg/libcairo not installed; cannot exercise primary path")
    except NotImplementedError:
        # rough refuses → dispatcher SHOULD escalate. Verify the Playwright
        # path is callable; if not installed, skip.
        try:
            from feinschmiede.diagrams.render_playwright import render_excalidraw as r_pw
        except ImportError:
            pytest.skip("playwright not installed; cannot verify fallback")
        r_pw(exc_path, out_png)

    assert out_png.is_file()
    assert out_png.stat().st_size > 1024, (
        f"{name}: PNG suspiciously small ({out_png.stat().st_size} bytes)"
    )
