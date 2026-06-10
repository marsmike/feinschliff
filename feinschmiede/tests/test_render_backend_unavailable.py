"""Missing libcairo surfaces an error naming cairo, not "install Playwright"."""

import builtins
import json

import pytest

from feinschmiede.diagrams import render


@pytest.fixture
def missing_libcairo(monkeypatch):
    """cairosvg installed but libcairo not dlopen-able; playwright absent."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "cairosvg":
            raise OSError("cannot load library 'libcairo.so.2': no such file")
        if name == "playwright" or name.startswith("playwright."):
            raise ImportError("No module named 'playwright'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_svg_render_names_libcairo_not_playwright(tmp_path, missing_libcairo):
    src = tmp_path / "diagram.svg"
    src.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    with pytest.raises(RuntimeError) as exc_info:
        render.render(src, tmp_path / "diagram.png")
    msg = str(exc_info.value)
    assert "libcairo" in msg
    assert "playwright" not in msg.lower()
    assert isinstance(exc_info.value.__cause__, OSError)


def test_excalidraw_render_names_libcairo_not_playwright(tmp_path, missing_libcairo):
    src = tmp_path / "diagram.excalidraw"
    src.write_text(json.dumps({
        "elements": [{"id": "r1", "type": "rectangle", "x": 0, "y": 0,
                      "width": 120, "height": 60, "seed": 1}],
        "appState": {},
    }))
    with pytest.raises(RuntimeError) as exc_info:
        render.render(src, tmp_path / "diagram.png")
    msg = str(exc_info.value)
    assert "libcairo" in msg
    assert "playwright" not in msg.lower()
    assert isinstance(exc_info.value.__cause__, OSError)
