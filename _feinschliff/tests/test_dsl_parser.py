"""Unit tests for `lib.dsl.parser`."""
from __future__ import annotations

import pytest

from lib.dsl.parser import (
    CompoundDef,
    DSLNode,
    parse_document,
    parse_lines,
    parse_wh,
    parse_xy,
)
from lib.dsl.ast import Document, Element, ElementKind, Slide


def test_parses_minimal_text_line():
    nodes, compounds = parse_lines('text 0,0 200x40 "hello"')
    assert compounds == []
    assert len(nodes) == 1
    n = nodes[0]
    assert isinstance(n, DSLNode)
    assert n.kind == "text"
    # XY token + WxH token come through as positional args
    assert "0,0" in n.pos_args
    assert "200x40" in n.pos_args
    assert n.label == "hello"


def test_parses_kw_args_with_colons():
    nodes, _ = parse_lines('text 0,0 200x40 "x" color:ink style:title')
    n = nodes[0]
    assert n.kw_args.get("color") == "ink"
    assert n.kw_args.get("style") == "title"
    assert n.label == "x"


def test_parses_quoted_strings_with_newline_escape():
    # \n in the source DSL must decode to a real newline in the label.
    nodes, _ = parse_lines('text 0,0 200x40 "line one\\nline two"')
    assert nodes[0].label == "line one\nline two"


def test_parses_if_kwarg():
    nodes, _ = parse_lines('text 0,0 200x40 "x" if:show_me')
    assert nodes[0].kw_args.get("if") == "show_me"


def test_hex_color_in_attribute_value_is_not_a_comment():
    # `#` inside an attribute value (no whitespace before it) must NOT
    # be treated as a comment marker. The hybrid decompiler emits raw
    # hex like `stroke:#222640` when no palette match exists; previously
    # the parser truncated this to `stroke:` and the build died with a
    # cryptic empty-token KeyError.
    nodes, _ = parse_lines("line 0,0 1,1080 stroke:#222640 stroke-width:1")
    n = nodes[0]
    assert n.kind == "line"
    assert n.kw_args.get("stroke") == "#222640"
    assert n.kw_args.get("stroke-width") == "1"


def test_trailing_inline_comment_still_stripped():
    # A real inline comment (preceded by whitespace) should still strip.
    nodes, _ = parse_lines("line 0,0 1,1080 stroke:#222640  # this is a real comment")
    n = nodes[0]
    assert n.kw_args.get("stroke") == "#222640"
    assert "this" not in n.kw_args
    assert "comment" not in n.kw_args


def test_leading_comment_line_is_skipped():
    nodes, _ = parse_lines("# comment line\ntext 0,0 200x40 \"x\"")
    assert len(nodes) == 1
    assert nodes[0].kind == "text"


def test_indented_comment_line_is_skipped():
    nodes, _ = parse_lines("   # indented comment\ntext 0,0 200x40 \"x\"")
    assert len(nodes) == 1
    assert nodes[0].kind == "text"


def test_parses_compound_definition_with_indented_body():
    src = (
        "compound footer(page, date):\n"
        "  rect 0,1040 1920x4 fill:accent\n"
        '  text 100,1050 style:detail "{{ page }}"\n'
        '  text 200,1050 style:detail "{{ date }}"\n'
    )
    nodes, compounds = parse_lines(src)
    assert nodes == []
    assert len(compounds) == 1
    cd = compounds[0]
    assert isinstance(cd, CompoundDef)
    assert cd.name == "footer"
    assert cd.params == ["page", "date"]
    # Body has three primitives.
    assert [b.kind for b in cd.body] == ["rect", "text", "text"]


def test_compound_with_no_params_parses():
    src = (
        "compound divider():\n"
        "  rect 0,540 1920x2 fill:fog\n"
    )
    _, compounds = parse_lines(src)
    assert compounds[0].params == []
    assert compounds[0].body[0].kind == "rect"


def test_line_numbers_propagate_to_nodes():
    src = (
        "# header comment\n"
        "\n"
        'text 0,0 200x40 "first"\n'
        'text 0,40 200x40 "second"\n'
    )
    nodes, _ = parse_lines(src, source="example.dsl")
    # line_no tracks the source line, so the two text nodes have different
    # numbers and the source filename is propagated.
    assert nodes[0].source == "example.dsl"
    assert nodes[1].source == "example.dsl"
    assert nodes[0].line_no != nodes[1].line_no


def test_nested_compound_definition_raises_syntax_error():
    src = (
        "compound outer(a):\n"
        "  compound inner(b):\n"
        '    text 0,0 200x40 "nope"\n'
    )
    with pytest.raises(SyntaxError) as exc:
        parse_lines(src, source="bad.dsl")
    # Error message includes the source for diagnostics.
    assert "bad.dsl" in str(exc.value) or "nested" in str(exc.value).lower()


def test_parse_xy_and_parse_wh_round_trip():
    assert parse_xy("100,200") == (100.0, 200.0)
    assert parse_xy("-10,5.5") == (-10.0, 5.5)
    assert parse_wh("1920x1080") == (1920.0, 1080.0)


def test_parse_xy_rejects_malformed():
    with pytest.raises(ValueError):
        parse_xy("not-a-coord")
    with pytest.raises(ValueError):
        parse_wh("1920,1080")


# ---------------------------------------------------------------------------
# parse_document
# ---------------------------------------------------------------------------

def test_parse_document_returns_document():
    dsl = 'canvas 1920x1080\ntext 100,100 "Hello"\n'
    doc = parse_document(dsl)
    assert isinstance(doc, Document)
    assert doc.version == 1


def test_parse_document_creates_one_slide():
    dsl = 'canvas 1920x1080\ntext 100,100 "X"\n'
    doc = parse_document(dsl)
    assert len(doc.slides) == 1
    assert isinstance(doc.slides[0], Slide)


def test_parse_document_canvas_goes_to_meta():
    dsl = "canvas 1920x1080\n"
    doc = parse_document(dsl)
    assert doc.slides[0].meta.get("canvas") == {"size": "1920x1080"}


def test_parse_document_theme_becomes_layout():
    dsl = "canvas 1920x1080\ntheme feinschliff\n"
    doc = parse_document(dsl)
    assert doc.slides[0].layout == "feinschliff"


def test_parse_document_text_node_becomes_element():
    dsl = 'text 100,100 style:title "Title"\n'
    doc = parse_document(dsl)
    elements = doc.slides[0].elements
    assert len(elements) == 1
    assert elements[0].kind is ElementKind.TEXT


def test_parse_document_rect_becomes_shape():
    dsl = "rect 0,0 1920x100 fill:accent\n"
    doc = parse_document(dsl)
    el = doc.slides[0].elements[0]
    assert el.kind is ElementKind.SHAPE


def test_parse_document_picture_becomes_image():
    dsl = "picture 100,100 760x520 path:hero.png\n"
    doc = parse_document(dsl)
    el = doc.slides[0].elements[0]
    assert el.kind is ElementKind.IMAGE


def test_parse_document_unknown_becomes_compound():
    dsl = "footer page:4\n"
    doc = parse_document(dsl)
    el = doc.slides[0].elements[0]
    assert el.kind is ElementKind.COMPOUND


def test_parse_document_source_in_meta():
    dsl = "text 0,0 \"x\"\n"
    doc = parse_document(dsl, source="my-layout.slide.dsl")
    assert doc.slides[0].meta.get("source") == "my-layout.slide.dsl"


def test_parse_document_element_props_contain_label():
    dsl = 'text 100,200 style:title "My Title"\n'
    doc = parse_document(dsl)
    el = doc.slides[0].elements[0]
    assert el.props.get("label") == "My Title"


def test_parse_document_svg_and_excalidraw_become_diagram():
    dsl = (
        "svg flow 0,0 960x540 {}\n"
        "excalidraw arch 960,0 960x540 {}\n"
    )
    doc = parse_document(dsl)
    elements = doc.slides[0].elements
    assert elements[0].kind is ElementKind.DIAGRAM
    assert elements[1].kind is ElementKind.DIAGRAM
