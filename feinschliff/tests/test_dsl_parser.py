"""Unit tests for `lib.dsl.parser`."""
from __future__ import annotations

import pytest

from lib.dsl.parser import (
    CompoundDef,
    DSLNode,
    parse_lines,
    parse_wh,
    parse_xy,
)


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
