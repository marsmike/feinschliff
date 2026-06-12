"""interpolate_native_text — slot templates inside native payloads resolve
at build time (inline b64 and sidecar xml_file), with XML escaping."""
from __future__ import annotations

import base64

from feinschliff.dsl.expander import interpolate_native_text
from feinschliff.dsl.parser import DSLNode


_XML_TEMPLATE = (
    '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    "<p:txBody><a:p><a:r>"
    "<a:t>{{ text_5 | default(&quot;Headline&quot;) }}</a:t>"
    "</a:r></a:p></p:txBody></p:sp>"
)


def _native_node(xml: str, **extra) -> DSLNode:
    kw = {"b64": base64.b64encode(xml.encode()).decode("ascii")}
    kw.update(extra)
    return DSLNode(kind="native", pos_args=["pic1"], kw_args=kw,
                   label=None, line_no=1, source="native pic1 …")


def _decoded(node: DSLNode) -> str:
    return base64.b64decode(node.kw_args["b64"]).decode()


def test_bound_slot_replaces_text_run():
    node = _native_node(_XML_TEMPLATE)
    interpolate_native_text([node], {"text_5": "Q3 Results"})
    assert "<a:t>Q3 Results</a:t>" in _decoded(node)
    assert "{{" not in _decoded(node)


def test_unbound_slot_falls_back_to_default():
    node = _native_node(_XML_TEMPLATE)
    interpolate_native_text([node], {})
    assert "<a:t>Headline</a:t>" in _decoded(node)


def test_value_is_xml_escaped_and_newlines_flatten():
    node = _native_node(_XML_TEMPLATE)
    interpolate_native_text([node], {"text_5": "A & B <x>\nrow2"})
    assert "<a:t>A &amp; B &lt;x&gt; row2</a:t>" in _decoded(node)


def test_payload_without_markers_untouched():
    xml = _XML_TEMPLATE.replace(
        "{{ text_5 | default(&quot;Headline&quot;) }}", "Fixed chrome")
    node = _native_node(xml)
    before = node.kw_args["b64"]
    interpolate_native_text([node], {"text_5": "ignored"})
    assert node.kw_args["b64"] == before


def test_sidecar_payload_inlined_for_build_only(tmp_path):
    assets = tmp_path / "assets"
    (assets / "native").mkdir(parents=True)
    sidecar = assets / "native" / "abc.xml"
    sidecar.write_text(_XML_TEMPLATE, encoding="utf-8")
    node = DSLNode(kind="native", pos_args=["table"],
                   kw_args={"xml_file": "native/abc.xml"},
                   label=None, line_no=1, source="native table …")
    interpolate_native_text([node], {"text_5": "Bound"}, asset_root=assets)
    assert "xml_file" not in node.kw_args
    assert "<a:t>Bound</a:t>" in _decoded(node)
    # the pack's template file itself is never rewritten
    assert "{{ text_5" in sidecar.read_text(encoding="utf-8")


def test_non_native_nodes_pass_through():
    node = DSLNode(kind="text", pos_args=["76,76"], kw_args={},
                   label="hi", line_no=1, source='text 76,76 "hi"')
    out = interpolate_native_text([node], {"text_5": "x"})
    assert out[0] is node
