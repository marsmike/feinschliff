"""Slotify pass: decompiled layouts carry literal text — to use a pack as a
real template, every text label becomes a `{{ text_N | default("literal") }}`
slot (the default keeps the bare showcase render identical; a deck build
overrides via ctx). Image placeholders are already slotified at decompile
time (`{{ image | default("…") }}`)."""
from __future__ import annotations

from feinschliff_builder.decompile.slotify import slotify_dsl


def test_simple_text_becomes_slot_with_default():
    dsl = 'canvas 1920x1080\ntext 76,76 style:body size:20pt "Hello World"\n'
    out, slots = slotify_dsl(dsl)
    assert slots == ["text_1"]
    assert 'text 76,76 style:body size:20pt "{{ text_1 | default(\\"Hello World\\") }}"' in out


def test_numbering_is_sequential_per_file():
    dsl = 'text 0,0 "A"\nrect 0,0 10x10 fill:ink\ntext 0,40 "B"\n'
    out, slots = slotify_dsl(dsl)
    assert slots == ["text_1", "text_2"]
    assert 'default(\\"A\\")' in out and "text_2" in out


def test_escaped_ascii_quotes_are_curlified():
    # The expander's default("...") grammar cannot hold ASCII quotes — they
    # are typographically curlified so the slot still parses.
    dsl = 'text 0,0 "click \\"more colors\\" now"\n'
    out, slots = slotify_dsl(dsl)
    assert slots == ["text_1"]
    assert '\\"more colors\\"' not in out.replace('default(\\"', "").replace('\\") }}', "")
    assert "“more colors”" in out or "”more colors”" in out


def test_already_slotified_label_untouched():
    line = 'text 0,0 "{{ title }}"\n'
    out, slots = slotify_dsl(line)
    assert slots == []
    assert out == line


def test_picture_and_native_lines_untouched():
    dsl = ('picture 0,0 100x100 path:"{{ image | default(\\"x.png\\") }}" cover:true\n'
           'native pic1 b64:"QUJD" media:"QUJD"\n')
    out, slots = slotify_dsl(dsl)
    assert slots == []
    assert out == dsl


def test_multiline_and_kwargs_preserved():
    dsl = 'text 75,208 style:body-sm weight:bold align:center "255 / 104 / 64\\n100%"\n'
    out, slots = slotify_dsl(dsl)
    assert slots == ["text_1"]
    assert out.startswith("text 75,208 style:body-sm weight:bold align:center ")
    assert 'default(\\"255 / 104 / 64\\n100%\\")' in out


def test_label_with_braces_is_left_literal():
    # `{`/`}` inside a slot body would break the expander's slot regex —
    # leave such labels untouched rather than emit a broken slot.
    dsl = 'text 0,0 "Cache {warm}"\n'
    out, slots = slotify_dsl(dsl)
    assert slots == []
    assert out == dsl


def test_roundtrip_through_parser_and_interpolation():
    """End-to-end: slotified line parses, the default fills with empty ctx,
    and a ctx override replaces the text."""
    from feinschliff.dsl.parser import parse_lines
    from feinschliff.dsl.expander import interpolate_nodes

    dsl = 'text 0,0 "click \\"more colors\\" and\\nwin"\n'
    out, slots = slotify_dsl(dsl)
    nodes, _ = parse_lines(out)
    [node] = [n for n in nodes if n.kind == "text"]

    [filled] = interpolate_nodes([node], {})
    assert "more colors" in filled.label and "\n" in filled.label
    assert '"' not in filled.label  # curlified
    assert "{{" not in filled.label

    nodes2, _ = parse_lines(out)
    [node2] = [n for n in nodes2 if n.kind == "text"]
    [overridden] = interpolate_nodes([node2], {"text_1": "World Cup 2026"})
    assert overridden.label == "World Cup 2026"
