"""Native-carry payloads above the inline threshold must ride as brand-pack
sidecar files, not inline base64 — a 33 MB carried group inlined as base64
produced a 44 MB .slide.dsl. Sidecars are sha-named for cross-slide dedupe
(the same template logo carried on 99 slides lands on disk exactly once)."""
from __future__ import annotations

import base64
import json
import re

from feinschliff_builder.decompile.pptx_svg_decompile import (
    NATIVE_INLINE_MAX,
    CanvasMap,
    Shape,
    emit_dsl,
)

_EMU_W, _EMU_H = 12192000, 6858000  # 16:9


def _cmap() -> CanvasMap:
    return CanvasMap(_EMU_W, _EMU_H, 1920, 1080)


def _sp(name: str, pad: int = 0) -> str:
    return (
        '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        f'<p:nvSpPr><p:cNvPr id="9" name="{name}"/></p:nvSpPr>'
        + ("<!--" + "x" * pad + "-->" if pad else "")
        + "</p:sp>"
    )


def test_big_native_xml_goes_to_sidecar(tmp_path):
    native_dir = tmp_path / "assets" / "native"
    big = _sp("Huge", pad=NATIVE_INLINE_MAX)
    small = _sp("Tiny")
    shapes = [
        Shape(kind="shape", x=0, y=0, w=100, h=100, native_xml=big),
        Shape(kind="shape", x=0, y=0, w=100, h=100, native_xml=small),
    ]
    dsl = emit_dsl(shapes, _cmap(), "t", native_dir=native_dir, native_rel="native")
    m = re.search(r'xml_file:"(native/[0-9a-f]{12}\.xml)"', dsl)
    assert m, f"big fragment not referenced as sidecar:\n{dsl}"
    sidecar = tmp_path / "assets" / m.group(1)
    assert sidecar.read_text(encoding="utf-8") == big
    assert 'b64:"' in dsl, "small fragment should stay inline"
    assert base64.b64encode(small.encode()).decode() in dsl


def test_big_native_media_goes_to_sidecar_raw(tmp_path):
    native_dir = tmp_path / "assets" / "native"
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * (NATIVE_INLINE_MAX + 1)
    shapes = [Shape(kind="pic", x=0, y=0, w=100, h=100, is_picture=True,
                    native_xml=_sp("Logo"),
                    native_media=base64.b64encode(png).decode())]
    dsl = emit_dsl(shapes, _cmap(), "t", native_dir=native_dir, native_rel="native")
    m = re.search(r'media_file:"(native/[0-9a-f]{12}\.png)"', dsl)
    assert m, f"big media not referenced as sidecar:\n{dsl}"
    assert (tmp_path / "assets" / m.group(1)).read_bytes() == png
    assert 'media:"' not in dsl


def test_big_native_parts_go_to_sidecar_json(tmp_path):
    native_dir = tmp_path / "assets" / "native"
    parts = [{"partname": "/ppt/charts/chart1.xml",
              "content_type": "application/vnd.openxmlformats-officedocument.drawingml.chart+xml",
              "blob": "A" * (NATIVE_INLINE_MAX + 1),
              "reltype": "rel", "parent": "slide", "src_rid": "rId3"}]
    shapes = [Shape(kind="graphic", x=0, y=0, w=100, h=100,
                    native_xml=_sp("Chart"), native_parts=parts)]
    dsl = emit_dsl(shapes, _cmap(), "t", native_dir=native_dir, native_rel="native")
    m = re.search(r'parts_file:"(native/[0-9a-f]{12}\.json)"', dsl)
    assert m, f"big parts not referenced as sidecar:\n{dsl}"
    loaded = json.loads((tmp_path / "assets" / m.group(1)).read_text(encoding="utf-8"))
    assert loaded == parts
    assert 'parts:"' not in dsl


def test_identical_payloads_dedupe_to_one_file(tmp_path):
    native_dir = tmp_path / "assets" / "native"
    big = _sp("Repeated", pad=NATIVE_INLINE_MAX)
    shapes = [Shape(kind="shape", x=0, y=0, w=100, h=100, native_xml=big),
              Shape(kind="shape", x=0, y=0, w=100, h=100, native_xml=big)]
    dsl = emit_dsl(shapes, _cmap(), "t", native_dir=native_dir, native_rel="native")
    refs = re.findall(r'xml_file:"(native/[0-9a-f]{12}\.xml)"', dsl)
    assert len(refs) == 2 and len(set(refs)) == 1
    assert len(list(native_dir.iterdir())) == 1


def test_without_native_dir_everything_stays_inline(tmp_path):
    big = _sp("Huge", pad=NATIVE_INLINE_MAX)
    shapes = [Shape(kind="shape", x=0, y=0, w=100, h=100, native_xml=big)]
    dsl = emit_dsl(shapes, _cmap(), "t")
    assert "xml_file:" not in dsl
    assert base64.b64encode(big.encode()).decode() in dsl
