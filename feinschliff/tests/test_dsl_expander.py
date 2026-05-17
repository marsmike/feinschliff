"""Unit tests for `lib.dsl.expander`."""
from __future__ import annotations

import pytest

from lib.dsl.parser import CompoundDef, DSLNode, parse_lines
from lib.dsl.expander import (
    ExpansionDiagnostic,
    PRIMITIVES,
    _safe_eval,
    expand_compounds,
    interpolate_nodes,
)


# ---------------------------------------------------------------------------
# PRIMITIVES set
# ---------------------------------------------------------------------------

def test_chip_is_not_a_primitive():
    """I5: `chip` used to be in PRIMITIVES without a matching emitter, so any
    `chip` line would print a "no emitter" warning. It's now gone — chips
    are expected to be built via brand compounds (rect + text) or via the
    `style:chip` text style. If someone re-adds `chip` to PRIMITIVES, they
    must also add an emitter."""
    assert "chip" not in PRIMITIVES


# ---------------------------------------------------------------------------
# _safe_eval
# ---------------------------------------------------------------------------

def test_safe_eval_accepts_arithmetic():
    assert _safe_eval("1 + 2", {}) == 3
    assert _safe_eval("10 - 4 * 2", {}) == 2
    assert _safe_eval("8 / 2", {}) == 4.0
    assert _safe_eval("-3 + 5", {}) == 2


def test_safe_eval_resolves_ctx_names():
    ctx = {"x": 100, "w": 50}
    assert _safe_eval("x + w", ctx) == 150
    assert _safe_eval("x + w / 2", ctx) == 125


def test_safe_eval_rejects_unknown_name():
    # Bare names that are not in ctx must raise KeyError, not silently 0.
    with pytest.raises(KeyError):
        _safe_eval("nope", {})


def test_safe_eval_rejects_function_calls():
    # Function-call nodes are not in the allow-list.
    with pytest.raises(ValueError):
        _safe_eval("abs(-1)", {})


def test_safe_eval_rejects_attribute_assignment_or_comparison():
    # Comparisons and boolean ops are not in the allow-list.
    with pytest.raises(ValueError):
        _safe_eval("1 < 2", {})


# ---------------------------------------------------------------------------
# interpolate_nodes
# ---------------------------------------------------------------------------

def test_interpolate_substitutes_simple_slot():
    nodes, _ = parse_lines('text 0,0 200x40 "{{ title }}"')
    out = interpolate_nodes(nodes, {"title": "Hello"})
    assert out[0].label == "Hello"


def test_interpolate_resolves_arithmetic_expressions():
    # The expander supports `{{ x + w - 1 }}` inside any string-valued field
    # — including positional args like the WxH spec.
    nodes, _ = parse_lines('rect 0,0 {{ w-1 }}x{{ h-1 }} fill:accent')
    out = interpolate_nodes(nodes, {"w": 100, "h": 50})
    # Second positional arg is the WxH spec; arithmetic resolved to ints.
    wh = out[0].pos_args[1]
    assert wh == "99x49"


def test_interpolate_missing_slot_resolves_to_empty():
    # Production-safe behavior: missing keys resolve to "" so `if:{{ … }}`
    # guards can suppress nodes whose binding is absent (instead of leaking
    # the literal `{{ … }}` into the rendered slide).
    nodes, _ = parse_lines('text 0,0 200x40 "{{ nope }}"')
    out = interpolate_nodes(nodes, {})
    assert out[0].label == ""


def test_interpolate_indexed_access():
    nodes, _ = parse_lines('text 0,0 200x40 "{{ items[1].title }}"')
    ctx = {"items": [{"title": "first"}, {"title": "second"}]}
    out = interpolate_nodes(nodes, ctx)
    assert out[0].label == "second"


# ---------------------------------------------------------------------------
# expand_compounds
# ---------------------------------------------------------------------------

def _parse_compounds(src: str) -> dict[str, CompoundDef]:
    """Helper — parse compound defs from a DSL string into a name → def map."""
    _, defs = parse_lines(src)
    return {cd.name: cd for cd in defs}


def test_expand_replaces_compound_call_with_body():
    compounds = _parse_compounds(
        "compound greet(who):\n"
        '  text 10,10 200x40 "Hello {{ who }}"\n'
    )
    nodes, _ = parse_lines('greet who:"World"')
    out, diags = expand_compounds(nodes, compounds)
    # The compound call resolved to a single `text` primitive.
    assert [n.kind for n in out] == ["text"]
    assert out[0].label == "Hello World"
    assert diags == []


def test_expand_recursion_depth_limit_raises():
    # Two compounds that call each other → cycle → RecursionError.
    compounds = _parse_compounds(
        "compound a():\n"
        "  b\n"
        "compound b():\n"
        "  a\n"
    )
    nodes, _ = parse_lines("a")
    with pytest.raises(RecursionError):
        expand_compounds(nodes, compounds, max_depth=8)


def test_expand_unknown_compound_emits_diagnostic_and_drops():
    """I3: unknown compounds collect into the returned diagnostics list
    instead of just printing to stderr. The CLI decides whether to fail."""
    nodes, _ = parse_lines("does-not-exist arg1 arg2")
    out, diags = expand_compounds(nodes, {})
    assert out == []
    assert len(diags) == 1
    d = diags[0]
    assert isinstance(d, ExpansionDiagnostic)
    assert d.kind == "unknown_compound"
    assert "does-not-exist" in d.message
    # `format()` produces a useful one-line representation.
    assert "unknown_compound" in d.format()


def test_expand_passes_primitives_through_unchanged():
    nodes, _ = parse_lines('text 0,0 200x40 "x"\nrect 0,40 100x10 fill:accent')
    out, diags = expand_compounds(nodes, {})
    assert [n.kind for n in out] == ["text", "rect"]
    assert diags == []


def test_expand_compound_params_default_to_empty_string():
    # When a caller omits a declared param, the binding falls back to "".
    compounds = _parse_compounds(
        "compound greet(who):\n"
        '  text 10,10 200x40 "Hello {{ who }}"\n'
    )
    nodes, _ = parse_lines("greet")
    out, _diags = expand_compounds(nodes, compounds)
    # Empty string replaces the slot — no leaked `{{ who }}` placeholder.
    assert out[0].label == "Hello "


def test_expand_unknown_kwarg_warns_and_records_diagnostic():
    """I2: a caller passing an undeclared kwarg (typo like `vlaue:` instead of
    `value:`) must surface a UserWarning and an `unknown_param` diagnostic —
    not silently leak through."""
    compounds = _parse_compounds(
        "compound greet(x):\n"
        '  text 10,10 200x40 "x={{ x }}"\n'
    )
    nodes, _ = parse_lines('greet x:1 y:2')
    with pytest.warns(UserWarning, match=r"unknown parameter 'y'"):
        out, diags = expand_compounds(nodes, compounds)
    # Expansion still succeeds.
    assert [n.kind for n in out] == ["text"]
    # Diagnostic captures the typo with the compound + line context.
    unknown_param = [d for d in diags if d.kind == "unknown_param"]
    assert len(unknown_param) == 1
    assert "greet" in unknown_param[0].message
    assert "'y'" in unknown_param[0].message


def test_expand_default_max_depth_matches_docs():
    """I4: the documented default `max_depth` is 8 (see docs/dsl-grammar.md).
    Confirm the code default matches by checking the signature."""
    import inspect
    sig = inspect.signature(expand_compounds)
    assert sig.parameters["max_depth"].default == 8
