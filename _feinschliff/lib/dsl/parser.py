"""Slide DSL parser — line-oriented, regex-driven.

Grammar (PoC subset). One element per line; '#' starts a comment. Lines
become DSLNodes the expander walks. Compound bodies start with
`compound <name>(<params>):` and capture indented lines underneath.

  canvas 1920x1080
  theme feinschliff

  # primitive: text
  text 100,100 style:title "{{ title }}"
  text 100,200 style:body  "{{ body }}" maxwidth:760

  # primitive: rect
  rect 0,0 1920x100 fill:accent

  # primitive: picture
  picture 80,220 760x520 slot:hero

  # compound call (resolves to primitives recursively)
  footer page:4 date:"2026-05"
  kpi-cell 200,500 value:"62" unit:"k" label:"employees"

  # compound definition (in a compounds/<name>.dsl file)
  compound footer(page, date):
    rect 0,1040 1920x4 fill:accent
    text 100,1050 style:detail "{{ page }}"
    text 200,1050 style:detail "{{ date }}"
    text 1820,1050 style:detail "Feinschliff" align:right

Tokens reach the renderer via `style:<token-name>` refs, not raw values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------

@dataclass
class DSLNode:
    """One parsed line. `kind` is the first token (text/rect/picture/canvas/
    theme/<compound-name>). `args` are positional+keyword from the line.

    `body` is non-None only for block constructs (`_for`): it carries the
    indented body the expander loops over."""
    kind: str
    pos_args: list[str] = field(default_factory=list)
    kw_args: dict[str, str] = field(default_factory=dict)
    label: str | None = None        # the quoted "label" if present
    line_no: int = 0
    source: str | None = None       # filename for error messages
    body: list[DSLNode] | None = None  # for-block body; None for primitives


@dataclass
class CompoundDef:
    name: str
    params: list[str]
    body: list[DSLNode]
    source: Path | None = None


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

# Match a quoted string OR a key:value where value may be a quoted string
# OR a bare token (no whitespace). Order matters — try quoted forms first.
_TOKEN_RE = re.compile(
    r'''
    (?P<kv_quoted>[\w-]+:"(?:[^"\\]|\\.)*") |   # key:"value"
    (?P<kv_bare>[\w-]+:[^\s]+) |                # key:value
    (?P<quoted>"(?:[^"\\]|\\.)*") |             # "string"
    (?P<bare>[^\s]+)                             # any non-space chunk
    ''',
    re.VERBOSE,
)


_BRACES_RE = re.compile(r"\{\{([^{}]*?)\}\}")


def _strip_brace_whitespace(line: str) -> str:
    """Collapse whitespace inside `{{ ... }}` so the tokeniser sees the
    whole interpolation as one token. `{{ x }},{{ y+20 }}` becomes
    `{{x}},{{y+20}}`. Slot resolution still works because `_SLOT_RE` in
    the expander already tolerates the no-whitespace form.

    Whitespace inside `"..."` literals within the slot is preserved —
    needed for `{{ key|default("Supporting narrative") }}` style filters
    whose fallback strings have meaningful spaces.
    """
    def _strip(body: str) -> str:
        out = []
        in_str = False
        i = 0
        while i < len(body):
            ch = body[i]
            # Escaped pair — preserve both chars unchanged. `\"` does NOT
            # toggle in_str (the slot grammar uses outer DSL escapes for
            # inner string literals, e.g. `default(\"Supporting narrative\")`).
            # But the inner `"` after `\` still acts as a string delimiter
            # in the slot expression — strip whitespace between them.
            if ch == "\\" and i + 1 < len(body):
                out.append(ch)
                out.append(body[i + 1])
                if body[i + 1] == '"':
                    in_str = not in_str
                i += 2
                continue
            if ch == '"':
                in_str = not in_str
                out.append(ch)
                i += 1
                continue
            if not in_str and ch.isspace():
                i += 1
                continue
            out.append(ch)
            i += 1
        return "".join(out)

    return _BRACES_RE.sub(lambda m: "{{" + _strip(m.group(1)) + "}}", line)


def _tokenise(line: str) -> list[str]:
    """Split a line into whitespace-separated tokens, preserving quoted
    strings as one token (with quotes intact). Brace-interpolations are
    preserved as a single token even if they originally contained
    whitespace (e.g. `{{ x+20 }}`)."""
    line = _strip_brace_whitespace(line)
    return [m.group(0) for m in _TOKEN_RE.finditer(line)]


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return (
            s[1:-1]
            .replace("\\\\", "\x00")  # protect literal backslash escapes
            .replace('\\"', '"')
            .replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\x00", "\\")
        )
    return s


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_COMPOUND_HEADER_RE = re.compile(r"^compound\s+([\w-]+)\s*\(([^)]*)\)\s*:\s*$")
_FOR_HEADER_RE = re.compile(r"^for\s+([A-Za-z_]\w*)\s+in\s+(.+?)\s*:\s*$")

# Matches: (svg|excalidraw) <id> <x>,<y> <w>x<h> [virtual:<W>x<H>] [from:"<path>"] [{]
#
# `virtual:WxH` decouples the *author's* canvas from the *slide slot* the
# diagram is dropped into. The body is authored as if the canvas were WxH;
# the renderer rasterizes at WxH; PPTX inserts the resulting PNG into the
# slot at w×h and PowerPoint downscales. Used by full-slide layouts that
# want a 4×-scale virtual viewport (e.g. 6880×2880 into a 1720×720 slot)
# so the model has 16× more pixel area to author into without crowding.
_DIAGRAM_HEADER_RE = re.compile(
    r'^(svg|excalidraw)\s+(\S+)\s+(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)'
    r'(?:\s+virtual:(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?))?'
    r'(?:\s+from:"([^"]+)")?'
    r'(\s*\{)?\s*$'
)


def _brace_delta_outside_strings(line: str) -> int:
    """Net brace-depth change for `line`, ignoring braces inside double-quoted
    strings (with `\\"` escapes). Diagram bodies contain labels like
    `box a 0,0 10x10 "Cache {warm}"` — a naive count of `{` minus `}` mis-
    parses the trailing `}` as a block close and corrupts the body.
    """
    delta = 0
    in_str = False
    esc = False
    for ch in line:
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            delta += 1
        elif ch == "}":
            delta -= 1
    return delta


def _collect_brace_body(lines: list[str], i: int, source: str | None) -> tuple[list[str], int]:
    """Collect lines until the closing `}` that matches an opening `{` already
    consumed on the header line. Returns (body_lines_stripped, new_index).
    Braces inside double-quoted strings are skipped — see
    _brace_delta_outside_strings.
    """
    body_lines: list[str] = []
    depth = 1
    while i < len(lines):
        raw = lines[i]
        i += 1
        depth += _brace_delta_outside_strings(raw)
        if depth <= 0:
            break
        body_lines.append(raw.strip())
    else:
        raise SyntaxError(
            f"{source or '<dsl>'}: unclosed diagram block `{{`"
        )
    return body_lines, i


def _parse_diagram_block(
    kind: str,
    diagram_id: str,
    x: str, y: str, w: str, h: str,
    from_path: str | None,
    body_lines: list[str],
    line_no: int,
    source: str | None,
    *,
    virtual_w: str | None = None,
    virtual_h: str | None = None,
) -> DSLNode:
    """Build a DSLNode for an svg/excalidraw block primitive.

    When `virtual_w`/`virtual_h` are supplied, the diagram body is authored
    in that virtual coordinate space; the renderer rasterizes at virtual
    size and the resulting PNG is inserted into the slot (w × h) by the
    PPTX emitter, which PowerPoint then downscales. This gives the author
    more pixel area to compose into without crowding.
    """
    # Lint: forbidden inner `canvas`
    for bl in body_lines:
        stripped = bl.strip()
        if stripped.startswith("canvas ") or stripped == "canvas":
            raise SyntaxError(
                f"{source or '<dsl>'} line {line_no}: diagram '{diagram_id}': "
                f"inner `canvas` is forbidden; region size {w}x{h} is the canvas"
            )
        # Lint: nested diagrams
        if stripped.startswith("svg ") or stripped.startswith("excalidraw "):
            raise SyntaxError(
                f"{source or '<dsl>'} line {line_no}: diagram '{diagram_id}': "
                f"nested diagrams are not allowed"
            )

    raw_body = "\n".join(body_lines)

    # Lint: from: + inline body are mutually exclusive
    if from_path and raw_body.strip():
        raise SyntaxError(
            f"{source or '<dsl>'} line {line_no}: diagram '{diagram_id}': "
            f"cannot combine inline body with from:"
        )

    # Lint: inline block must not be empty (but from: path is fine alone)
    if not from_path and not raw_body.strip():
        raise SyntaxError(
            f"{source or '<dsl>'} line {line_no}: diagram '{diagram_id}': "
            f"inline diagram body must not be empty"
        )

    kw: dict[str, object] = {
        "id": diagram_id,
        "x": int(float(x)),
        "y": int(float(y)),
        "w": int(float(w)),
        "h": int(float(h)),
    }
    if virtual_w is not None and virtual_h is not None:
        kw["virtual_w"] = int(float(virtual_w))
        kw["virtual_h"] = int(float(virtual_h))
    if from_path:
        kw["from"] = from_path
    else:
        kw["body"] = raw_body

    return DSLNode(
        kind=kind,
        kw_args=kw,  # type: ignore[arg-type]
        line_no=line_no,
        source=source,
    )


def _collect_indented_body(lines: list[str], i: int) -> tuple[list[str], int]:
    """Consume the indented block starting at `lines[i]`. Returns
    (body_lines, new_index). Blank lines are included so line numbers
    in error messages stay accurate; non-indented non-blank line ends
    the block."""
    body_lines: list[str] = []
    while i < len(lines):
        bl = lines[i]
        bs = bl.split("#", 1)[0].rstrip()
        if not bs.strip():
            body_lines.append("")
            i += 1
            continue
        if not (bl.startswith("  ") or bl.startswith("\t")):
            break
        body_lines.append(bl)
        i += 1
    return body_lines, i


def parse_lines(text: str, *, source: str | None = None) -> tuple[list[DSLNode], list[CompoundDef]]:
    """Parse a DSL text into (top-level nodes, compound defs).

    Compound defs are recognised by the `compound <name>(<params>):` header
    plus indented body lines. Top-level nodes are everything else.
    """
    nodes: list[DSLNode] = []
    compounds: list[CompoundDef] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        m = _COMMENT_RE.search(raw)
        stripped = (raw[:m.start()] if m else raw).rstrip()
        if not stripped.strip():
            continue

        m = _COMPOUND_HEADER_RE.match(stripped.strip())
        if m:
            name = m.group(1)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            body_lines, i = _collect_indented_body(lines, i)
            body_text = "\n".join(b.lstrip() for b in body_lines)
            body_nodes, nested = parse_lines(body_text, source=source)
            if nested:
                raise SyntaxError(
                    f"{source or '<dsl>'}: nested compound definitions not supported"
                )
            compounds.append(CompoundDef(name=name, params=params, body=body_nodes,
                                         source=Path(source) if source else None))
            continue

        m = _FOR_HEADER_RE.match(stripped.strip())
        if m:
            var = m.group(1)
            iter_expr = m.group(2).strip()
            header_line_no = i
            body_lines, i = _collect_indented_body(lines, i)
            body_text = "\n".join(b.lstrip() for b in body_lines)
            body_nodes, nested = parse_lines(body_text, source=source)
            if nested:
                raise SyntaxError(
                    f"{source or '<dsl>'}: nested compound definitions inside `for` not supported"
                )
            nodes.append(DSLNode(
                kind="_for",
                kw_args={"var": var, "iter": iter_expr},
                line_no=header_line_no,
                source=source,
                body=body_nodes,
            ))
            continue

        m = _DIAGRAM_HEADER_RE.match(stripped.strip())
        if m:
            kind_d, d_id, x, y, w, h, virt_w, virt_h, from_path, open_brace = m.groups()
            header_line_no = i
            if open_brace and open_brace.strip() == "{":
                body_lines, i = _collect_brace_body(lines, i, source)
            else:
                body_lines = []
            node = _parse_diagram_block(
                kind=kind_d,
                diagram_id=d_id,
                x=x, y=y, w=w, h=h,
                virtual_w=virt_w,
                virtual_h=virt_h,
                from_path=from_path,
                body_lines=body_lines,
                line_no=header_line_no,
                source=source,
            )
            nodes.append(node)
            continue

        node = _parse_line(stripped.strip(), line_no=i, source=source)
        if node is not None:
            nodes.append(node)
    return nodes, compounds


def _parse_line(line: str, *, line_no: int, source: str | None) -> DSLNode | None:
    if not line:
        return None
    toks = _tokenise(line)
    if not toks:
        return None
    kind = toks[0]
    pos: list[str] = []
    kw: dict[str, str] = {}
    label: str | None = None
    for t in toks[1:]:
        if _KV_RE.match(t):
            k, _, v = t.partition(":")
            kw[k] = _unquote(v)
        elif t.startswith('"') and t.endswith('"'):
            # the (first) bare quoted token in a line becomes the label
            if label is None:
                label = _unquote(t)
            else:
                # multiple quoted strings: append into pos_args
                pos.append(_unquote(t))
        else:
            pos.append(t)
    return DSLNode(kind=kind, pos_args=pos, kw_args=kw, label=label,
                   line_no=line_no, source=source)


def parse_file(path: Path) -> tuple[list[DSLNode], list[CompoundDef]]:
    return parse_lines(path.read_text(), source=str(path))


# ---------------------------------------------------------------------------
# Typed Document entry points
# ---------------------------------------------------------------------------

def parse_document(text: str, *, source: str | None = None) -> "Document":
    """Parse DSL text and return a typed :class:`~lib.dsl.ast.Document`.

    Wraps :func:`parse_lines` and converts DSL nodes to the typed AST.
    A single-file layout produces a ``Document`` with one ``Slide``.

    The layout name is inferred from any ``theme`` node; other nodes are
    mapped to :class:`~lib.dsl.ast.Element` objects.  The ``source``
    parameter flows into ``Slide.meta['source']`` for traceability.

    Parameters
    ----------
    text:
        Raw DSL source text.
    source:
        Optional filename for error messages.

    Returns
    -------
    Document
        A typed :class:`~lib.dsl.ast.Document` wrapping the parsed nodes.
    """
    from lib.dsl.ast import Document, Slide, Element, ElementKind

    nodes, _compounds = parse_lines(text, source=source)

    # Extract layout/theme name and canvas from directives.
    layout_name = ""
    canvas: dict = {}
    elements: list[Element] = []

    for node in nodes:
        if node.kind == "canvas":
            # e.g. canvas 1920x1080
            if node.pos_args:
                canvas = {"size": node.pos_args[0]}
            continue
        if node.kind == "theme":
            # e.g. theme feinschliff
            if node.pos_args:
                layout_name = node.pos_args[0]
            continue
        elements.append(_node_to_element(node))

    meta: dict = {}
    if canvas:
        meta["canvas"] = canvas
    if source:
        meta["source"] = source

    slide = Slide(layout=layout_name, elements=elements, meta=meta)
    return Document(version=1, slides=[slide])


def parse_document_file(path: Path) -> "Document":
    """Parse a DSL file and return a typed Document.

    Convenience wrapper around :func:`parse_document` that reads the file
    and passes its path as ``source``.
    """
    return parse_document(path.read_text(), source=str(path))


# Mapping from DSL node kind string → ElementKind
_KIND_MAP: dict[str, str] = {
    "text":       "text",
    "picture":    "image",
    "rect":       "shape",
    "shape":      "shape",
    "line":       "shape",
    "polyline":   "shape",
    "svg":        "diagram",
    "excalidraw": "diagram",
    "_for":       "group",
}


def _node_to_element(node: DSLNode) -> "Element":
    """Convert a DSLNode to a typed Element.

    Unknown node kinds (unresolved compound calls) map to
    ``ElementKind.COMPOUND``.
    """
    from lib.dsl.ast import Element, ElementKind

    kind_str = _KIND_MAP.get(node.kind, "compound")
    kind = ElementKind(kind_str)

    # Build props from the DSLNode fields.
    props: dict = {}
    if node.pos_args:
        props["pos_args"] = list(node.pos_args)
    if node.kw_args:
        props.update(node.kw_args)
    if node.label is not None:
        props["label"] = node.label
    if node.source:
        props["source"] = node.source
    if node.line_no:
        props["line_no"] = node.line_no
    # Store the original DSL kind so round-tripping can recover it.
    props["_dsl_kind"] = node.kind

    # For compound calls, store the compound name.
    if kind is ElementKind.COMPOUND:
        props["compound_name"] = node.kind

    # Recurse into for-block bodies.
    children: list = []
    if node.body:
        children = [_node_to_element(child) for child in node.body]

    return Element(kind=kind, props=props, children=children)


# ---------------------------------------------------------------------------
# Position parsing helpers (used by expander + emitter)
# ---------------------------------------------------------------------------

_XY_RE   = re.compile(r"^(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$")
_WH_RE   = re.compile(r"^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$")
# Identifier followed by ':' anchors a key:value kwarg at the start of a token.
# Guards against false-positives like quoted positional strings that contain
# a colon (e.g. `"foo: bar"` would otherwise be split on the colon).
_KV_RE = re.compile(r"^[A-Za-z_][\w-]*:")

# Comment marker: `#` only starts a comment when at start-of-line (after any
# leading whitespace) or preceded by whitespace. Inline `#` inside an
# attribute value like `stroke:#222640` must pass through unchanged — the
# hybrid decompiler emits raw hex when a palette match is unavailable, and
# treating `#hex` as a comment marker truncated those values to empty
# strings, which crashed the build with a cryptic missing-token KeyError.
_COMMENT_RE = re.compile(r"(?:^|(?<=\s))#")


def parse_xy(s: str) -> tuple[float, float]:
    m = _XY_RE.match(s)
    if not m:
        raise ValueError(f"expected 'X,Y' got '{s}'")
    return float(m.group(1)), float(m.group(2))


def parse_wh(s: str) -> tuple[float, float]:
    m = _WH_RE.match(s)
    if not m:
        raise ValueError(f"expected 'WxH' got '{s}'")
    return float(m.group(1)), float(m.group(2))
