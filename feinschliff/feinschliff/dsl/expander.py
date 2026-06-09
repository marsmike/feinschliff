"""DSL expander: resolves slot interpolation + compound calls into a
primitives-only node list.

Two passes:
  1. **Slot interpolation** — replace `{{ slot:NAME }}` in any string
     value with content from the per-slide content map.
  2. **Compound resolution** — recursively replace compound-call nodes
     with their body (param-substituted), until only primitives remain.

Primitives recognised: `canvas`, `theme`, `text`, `rect`, `line`,
`picture`. Anything else is treated as a compound call and looked up
in the union of toolkit-standard compounds + brand-specific compounds.
Brand compounds win on name collision (explicit override).
"""
from __future__ import annotations

import ast
import operator
import re
import warnings
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from .parser import DSLNode, CompoundDef, parse_file
from .tokens import _parse_design_md_frontmatter

if TYPE_CHECKING:
    from feinschmiede.brand import BrandPack
    from feinschmiede.dsl.ast import Document, Element, Slide


@dataclass
class ExpansionDiagnostic:
    """One diagnostic produced during compound expansion.

    `kind` is a machine-readable tag — e.g. `"unknown_compound"` — that
    CLIs can pivot exit codes on. `message` is human-readable. `source`
    + `line_no` come from the DSLNode that triggered it.
    """

    kind: str
    message: str
    source: str = ""
    line_no: int = 0

    def format(self) -> str:
        loc = f"{self.source}:{self.line_no}" if self.source else f"line {self.line_no}"
        return f"[{self.kind}] {self.message} ({loc})"


_AST_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(expr: str, ctx: dict) -> float:
    """Evaluate a small arithmetic expression with ctx-resolved variables.

    Accepts numeric literals, bare names (looked up in ctx), and the four
    binary operators + - * /. Variables resolve via `_lookup` to support
    dotted/indexed paths.
    """
    tree = ast.parse(expr, mode="eval").body

    def walk(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            v = _lookup(node.id, ctx)
            if v is _MISSING:
                raise KeyError(node.id)
            return float(v)
        if isinstance(node, ast.Subscript) or isinstance(node, ast.Attribute):
            # rebuild source-key from the AST so _lookup handles dotted/[i]
            src = ast.unparse(node)
            v = _lookup(src, ctx)
            if v is _MISSING:
                raise KeyError(src)
            return float(v)
        if isinstance(node, ast.BinOp) and type(node.op) in _AST_OPS:
            return _AST_OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _AST_OPS:
            return _AST_OPS[type(node.op)](walk(node.operand))
        raise ValueError(f"unsupported expression node {type(node).__name__}")

    return walk(tree)


PRIMITIVES = {"canvas", "theme", "text", "rect", "line", "polyline", "picture", "shape"}


# ---------------------------------------------------------------------------
# Typed Document entry point
# ---------------------------------------------------------------------------

def expand_document(doc: "Document", pack: "BrandPack") -> "Document":
    """Expand a typed :class:`~feinschmiede.dsl.ast.Document` using brand compounds.

    Wraps :func:`expand_compounds` via per-COMPOUND-element DSLNode
    reconstruction.  Non-compound elements pass through the typed AST
    unchanged.  The input document is not mutated.

    Each slide's elements go through compound expansion; diagram blocks
    are NOT rendered (use :func:`expand_diagram_blocks` for that).  This
    entry point is intended for content-slot interpolation and compound
    resolution on a plan-level Document (one per deck, slides carry
    layout + content metadata).

    Parameters
    ----------
    doc:
        The typed Document to expand.
    pack:
        BrandPack whose compounds/ directory contributes brand-specific
        compound definitions.

    Returns
    -------
    Document
        A new Document with compound-call Elements replaced by their
        expanded primitive children.
    """
    from feinschmiede.dsl.ast import Document, Slide

    std_dir = Path(__file__).resolve().parents[2] / "compounds"
    compounds = load_compounds_for_brand(pack.root, std_dir=std_dir)

    expanded_slides: list[Slide] = []
    for slide in doc.slides:
        expanded_elements = _expand_elements(slide.elements, compounds)
        expanded_slides.append(Slide(
            layout=slide.layout,
            elements=expanded_elements,
            meta=dict(slide.meta),
            notes=slide.notes,
        ))
    return Document(
        version=doc.version,
        slides=expanded_slides,
        meta=dict(doc.meta),
    )


def _expand_elements(
    elements: list["Element"],
    compounds: dict,
) -> list["Element"]:
    """Recursively expand COMPOUND-kind Elements using the compounds map.

    Returns a new flat list of expanded elements.  Non-compound elements
    pass through unchanged.  This mirrors ``expand_compounds`` but operates
    on the typed Element AST rather than DSLNode lists.
    """
    from feinschmiede.dsl.ast import Element, ElementKind

    out: list[Element] = []
    for el in elements:
        if el.kind is ElementKind.COMPOUND:
            compound_name = el.props.get("compound_name") or el.props.get("_dsl_kind", "")
            cd = compounds.get(compound_name)
            if cd is None:
                # Unknown compound — pass through as-is (matches expand_compounds behaviour).
                out.append(el)
            else:
                # Reconstruct a DSLNode, run expand_compounds, convert back.
                from feinschliff.dsl.parser import DSLNode
                call_node = DSLNode(
                    kind=compound_name,
                    pos_args=list(el.props.get("pos_args") or []),
                    kw_args={k: v for k, v in el.props.items()
                             if k not in ("pos_args", "label", "source", "line_no",
                                          "compound_name", "_dsl_kind")},
                    label=el.props.get("label"),
                )
                expanded_nodes, _ = expand_compounds([call_node], compounds)
                from feinschliff.dsl.parser import _node_to_element
                for n in expanded_nodes:
                    out.append(_node_to_element(n))
        elif el.kind is ElementKind.GROUP and el.children:
            out.append(Element(
                kind=el.kind,
                props=dict(el.props),
                children=_expand_elements(el.children, compounds),
            ))
        else:
            out.append(el)
    return out


# ---------------------------------------------------------------------------
# Compound library loading
# ---------------------------------------------------------------------------

def load_compounds(*dirs: Path) -> dict[str, CompoundDef]:
    """Load all `*.dsl` from each dir, latter dirs override earlier on
    name collision (so brand-specific beats toolkit-standard)."""
    out: dict[str, CompoundDef] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.dsl")):
            _nodes, defs = parse_file(f)
            for cd in defs:
                out[cd.name] = cd
    return out


def load_compounds_for_brand(
    brand_root: Path, *, std_dir: Path, brands_dir: Path | None = None
) -> dict[str, CompoundDef]:
    """Resolve brand compounds across the `extends:` chain.

    Mirrors `tokens.load_tokens`: walks parents declared in DESIGN.md
    frontmatter, then layers std → root-of-chain → … → child so child
    overrides win. Lets a brand inherit header/footer (or any other
    compound) from a parent brand without copying the file.
    """
    brands_dir = brands_dir or brand_root.parent
    chain: list[Path] = []
    visited: set[str] = set()
    cur = brand_root
    while True:
        if cur.name in visited:
            raise ValueError(f"cyclic brand inheritance through {cur.name}")
        visited.add(cur.name)
        chain.append(cur)
        design = cur / "DESIGN.md"
        parent_name = None
        if design.is_file():
            fm = _parse_design_md_frontmatter(design.read_text())
            parent_name = fm.get("extends")
        if not parent_name:
            break
        parent = brands_dir / parent_name
        if not parent.is_dir():
            # Cross-plugin extends — same fallback as load_tokens.
            # Walk discovery sources directly (not discover_brands()) to
            # avoid the tokens ↔ brand_discovery recursion path.
            from feinschmiede.brand_discovery import _discovery_sources
            parent = None
            for _src, root in _discovery_sources():
                cand = root / parent_name
                if cand.is_dir():
                    parent = cand
                    brands_dir = root
                    break
            if parent is None:
                raise FileNotFoundError(
                    f"brand '{cur.name}' extends '{parent_name}' but not "
                    f"found in {brands_dir} or via plugin discovery"
                )
        cur = parent

    # std first, then chain from root-of-chain → child (child wins on name).
    dirs: list[Path] = [std_dir]
    for b in reversed(chain):
        dirs.append(b / "compounds")
    return load_compounds(*dirs)


# ---------------------------------------------------------------------------
# Slot interpolation
# ---------------------------------------------------------------------------

# `{{ … }}` captures the full body. Bodies may be a single key path
# (`columns[0].counter`, `kpis[2].value`) or a small arithmetic expression
# (`y+h-1`, `x+w/2`) that mixes ctx names with int literals.
_SLOT_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
_KEY_PART_RE = re.compile(r"(\w+)|\[(\d+)\]")

# `{{ key|default("Fallback") }}` — emit the literal when key is missing or
# empty-string. Single filter only; the rest of the slot grammar stays
# untouched. Used by layouts that want translatable defaults without forcing
# every deck to author the slot.
_DEFAULT_FILTER_RE = re.compile(
    r'^([\w\.\[\]]+)\s*\|\s*default\(\s*"([^"]*)"\s*\)\s*$'
)


def _lookup(key: str, ctx: dict):
    """Walk a dotted/indexed key path against ctx; return the leaf value or
    a sentinel `_MISSING` if any step misses."""
    val = ctx
    for m in _KEY_PART_RE.finditer(key):
        word, idx = m.group(1), m.group(2)
        if word is not None:
            if isinstance(val, dict) and word in val:
                val = val[word]
            else:
                return _MISSING
        else:
            i = int(idx)
            if isinstance(val, (list, tuple)) and 0 <= i < len(val):
                val = val[i]
            else:
                return _MISSING
    return val


_MISSING = object()


def _interp(text: str, ctx: dict) -> str:
    """Replace `{{ … }}` placeholders with ctx-resolved values.

    Body forms:
      - simple key path (`title`, `columns[0].counter`)
      - arithmetic expression (`y+h-1`, `x+w/2`) with ctx names + literals

    Missing keys / unresolvable expressions resolve to an empty string.
    This is the production-safe behavior: it lets `if:{{ optional }}`
    guards suppress nodes whose binding is absent (instead of leaking
    the literal `{{ … }}` token into the rendered slide).
    """
    def repl(m: re.Match) -> str:
        body = m.group(1).strip()
        # `{{ key|default("fallback") }}` — literal fallback for missing slots.
        dm = _DEFAULT_FILTER_RE.match(body)
        if dm is not None:
            key, fallback = dm.group(1), dm.group(2)
            val = _lookup(key, ctx)
            if val is _MISSING or val == "":
                return fallback
            return str(val)
        # Simple key path: no arithmetic operators outside of brackets.
        if not re.search(r"[+\-*/](?![^\[]*\])", body):
            val = _lookup(body, ctx)
            if val is _MISSING:
                return ""
            return str(val)
        try:
            result = _safe_eval(body, ctx)
            return str(int(result)) if result == int(result) else f"{result:g}"
        except (KeyError, ValueError, SyntaxError, ZeroDivisionError):
            return ""
    return _SLOT_RE.sub(repl, text)


def interpolate_nodes(nodes: list[DSLNode], ctx: dict) -> list[DSLNode]:
    """Apply slot interpolation to every string-valued field on every node.

    `_for` nodes unroll here: the iterable is looked up in ctx and the body
    is recursively interpolated once per element, with the loop variable
    and a 0-based `i` index added to ctx. If the iterable is missing or
    empty the block simply emits nothing.
    """
    out: list[DSLNode] = []
    for n in nodes:
        if n.kind == "_for":
            var = n.kw_args.get("var", "item")
            iter_expr = n.kw_args.get("iter", "").strip()
            iterable = _lookup(iter_expr, ctx)
            if iterable is _MISSING or not iterable:
                continue
            for idx, item in enumerate(iterable):
                sub_ctx = dict(ctx)
                sub_ctx[var] = item
                sub_ctx["i"] = idx
                out.extend(interpolate_nodes(n.body or [], sub_ctx))
            continue
        new_pos = [_interp(p, ctx) for p in n.pos_args]
        new_kw = {k: (_interp(v, ctx) if isinstance(v, str) else v) for k, v in n.kw_args.items()}
        new_label = _interp(n.label, ctx) if n.label is not None else None
        out.append(replace(n, pos_args=new_pos, kw_args=new_kw, label=new_label))
    return out


# ---------------------------------------------------------------------------
# Compound resolution
# ---------------------------------------------------------------------------

def expand_compounds(
    nodes: list[DSLNode],
    compounds: dict[str, CompoundDef],
    *,
    depth: int = 0,
    max_depth: int = 8,
    _diagnostics: list[ExpansionDiagnostic] | None = None,
) -> tuple[list[DSLNode], list[ExpansionDiagnostic]]:
    """Recursively replace compound-call nodes with their parameter-
    substituted bodies until only primitives remain.

    A compound call is matched by `kind` against the compounds map. The
    call's `pos_args`/`kw_args`/`label` become a param-binding dict that
    gets interpolated into every body node.

    `max_depth` guards against runaway recursion (compound A calls
    compound B calls compound A …); the default matches docs/dsl-grammar.md.

    Returns `(primitives, diagnostics)`. Diagnostics is a list of
    `ExpansionDiagnostic` describing non-fatal issues (e.g.
    `unknown_compound`, `unknown_param`) gathered during expansion.
    Callers (CLIs) decide whether any diagnostic kind should fail the
    build — `expand_compounds` itself does not raise for them.
    """
    if depth > max_depth:
        raise RecursionError(
            f"compound expansion exceeded depth {max_depth} — cycle?"
        )

    # Top-level caller starts a fresh diagnostics list; recursive frames
    # share it so callers see all diagnostics in one pass.
    diags = _diagnostics if _diagnostics is not None else []

    out: list[DSLNode] = []
    for n in nodes:
        if n.kind in PRIMITIVES:
            out.append(n)
            continue
        if n.kind == "_for":
            # Reached `expand_compounds` only when `interpolate_nodes` was
            # skipped (e.g. wireframe --show-slots). Emit the body once so
            # the layout's structure is still visible; the placeholders
            # inside survive un-interpolated.
            sub_out, _ = expand_compounds(
                n.body or [], compounds,
                depth=depth + 1, max_depth=max_depth,
                _diagnostics=diags,
            )
            out.extend(sub_out)
            continue
        cd = compounds.get(n.kind)
        if cd is None:
            # Not a primitive, not a known compound. Record a diagnostic
            # and drop the node — the CLI decides if this is fatal.
            diags.append(ExpansionDiagnostic(
                kind="unknown_compound",
                message=f"unknown element '{n.kind}' — not a primitive and not a registered compound; skipping",
                source=n.source,
                line_no=n.line_no,
            ))
            continue
        bindings = _bind_params(cd, n, diags)
        body = interpolate_nodes(cd.body, bindings)
        sub_out, _ = expand_compounds(
            body, compounds,
            depth=depth + 1, max_depth=max_depth,
            _diagnostics=diags,
        )
        out.extend(sub_out)
    return out, diags


def expand_diagram_blocks(
    nodes: list[DSLNode],
    brand_dir: Path,
    out_dir: Path,
    layout_dir: Path | None = None,
    *,
    slide_index: int = 1,
) -> list[DSLNode]:
    """Replace svg/excalidraw block nodes with picture primitives pointing at
    rendered PNGs. Carries diagram metadata so wireframe can render the
    internal bbox layer alongside the slide-level wireframe.

    Parameters
    ----------
    nodes:
        Post-parse node list (output of ``parse_lines`` / ``parse_file``).
    brand_dir:
        Path to the active brand directory (passed through to diagram expanders
        for colour resolution).
    out_dir:
        Directory where rendered artifacts (.svg/.excalidraw + .png) are
        written.  Must exist before calling.
    layout_dir:
        Base directory for resolving ``from:`` relative paths.  Defaults to
        ``out_dir.parent`` when not supplied.
    """
    import hashlib
    import json as _json

    from feinschmiede.diagrams import svg_expand, excalidraw_expand
    from feinschmiede.diagrams.render import render
    from feinschmiede.diagrams.diagram_wireframe import (
        primitives_from_svg_dsl,
        primitives_from_excalidraw_dsl,
    )

    # Tokens hash for the diagram cache key. Diagram colours resolve through
    # the FULL `extends:` chain (brand_bridge merges parent tokens), so hashing
    # only the child brand's tokens.json would reuse a stale PNG when a PARENT
    # token is edited — common for a brand that inherits its palette via
    # `extends:`. Hash the merged, extends-resolved tokens instead. Computed
    # once per call (constant across this slide's diagram nodes). Falls back
    # to the child file alone if the chain can't be resolved, so a malformed
    # parent degrades to a stale-cache risk rather than crashing the build.
    try:
        from feinschmiede.dsl.tokens import load_tokens
        _merged_raw = load_tokens(brand_dir).raw
        _tokens_hash = hashlib.sha1(
            _json.dumps(_merged_raw, sort_keys=True,
                        separators=(",", ":")).encode()
        ).hexdigest()[:12]
    except Exception:  # noqa: BLE001 — never block a render on token resolution
        _tj = brand_dir / "tokens.json"
        _tokens_hash = (
            hashlib.sha1(_tj.read_bytes()).hexdigest()[:12]
            if _tj.exists() else ""
        )
    _layout_dir_name = layout_dir.name if layout_dir is not None else ""

    # Clear THIS slide's prior diagram artifacts before writing fresh ones.
    # Artifacts are content-hash-named (`s{slide_index}-{id}-{hash}.{svg,
    # excalidraw,png}`) and out_dir is persistent on the `feinschliff build`
    # path, so a changed diagram leaves the old hash file behind. The
    # structural-lint loops glob `s{slide_index}-*`, so a stale artifact would
    # be linted as if current. The `s{idx}-` prefix is glob-safe (`s5-*` does
    # not match `s50-*`). Only runs when this slide actually has diagrams.
    if out_dir.exists() and any(n.kind in ("svg", "excalidraw") for n in nodes):
        for stale in out_dir.glob(f"s{slide_index}-*"):
            stale.unlink(missing_ok=True)

    out: list[DSLNode] = []
    for n in nodes:
        if n.kind not in ("svg", "excalidraw"):
            out.append(n)
            continue

        # All diagram geometry lives in kw_args (set by _parse_diagram_block,
        # which only runs when the line matched the multi-line block header:
        # `<kind> <id> <x>,<y> <w>x<h> {` with the brace at END of line). If
        # geometry is absent the header didn't match — almost always a
        # single-line `{ … }` body or a multi-token id. Fail with the fix
        # rather than a bare KeyError deep in the expander.
        if "x" not in n.kw_args:
            raise SyntaxError(
                f"{n.source or '<dsl>'} line {n.line_no}: malformed '{n.kind}' "
                f"diagram block — no geometry parsed. Use the multi-line form "
                f"with the opening brace at END of line:\n"
                f"  {n.kind} <id> <x>,<y> <w>x<h> {{\n"
                f"    path p \"M 0,0 L 1,1 Z\" fill:accent\n"
                f"  }}\n"
                f"Single-line `{{ … }}` body and a missing/multi-token <id> are "
                f"not supported here."
            )
        x: int = n.kw_args["x"]  # type: ignore[assignment]
        y: int = n.kw_args["y"]  # type: ignore[assignment]
        w: int = n.kw_args["w"]  # type: ignore[assignment]
        h: int = n.kw_args["h"]  # type: ignore[assignment]
        dsl_id: str = n.kw_args["id"]  # type: ignore[assignment]

        # Virtual viewport: when the layout block declares `virtual:WxH`, the
        # body is authored in WxH coords and the renderer rasterizes at WxH.
        # PowerPoint downscales on insert. When absent, the slot IS the canvas
        # (legacy behavior, preserved bit-for-bit).
        _vw = n.kw_args.get("virtual_w")
        virtual_w: int = _vw if _vw is not None else w  # type: ignore[assignment]
        _vh = n.kw_args.get("virtual_h")
        virtual_h: int = _vh if _vh is not None else h  # type: ignore[assignment]

        # Resolve body: inline string or external file.
        body: str = n.kw_args.get("body") or ""  # type: ignore[assignment]
        from_path: str | None = n.kw_args.get("from")  # type: ignore[assignment]
        if from_path:
            base = layout_dir or out_dir.parent
            raw = Path(base / from_path).read_text()
            # Strip any canvas line — region/virtual size IS the canvas when
            # embedded. Files keep `canvas` for standalone-render workflows.
            body = "\n".join(
                line for line in raw.splitlines()
                if not line.strip().startswith("canvas ")
            )

        if n.kind == "svg":
            expanded_text = svg_expand.expand(
                body, brand_dir=brand_dir, canvas_override=(virtual_w, virtual_h)
            )
            ext = ".svg"
            prims = primitives_from_svg_dsl(body, brand_dir, canvas_w=virtual_w)
        else:
            expanded_text = excalidraw_expand.expand(
                body, brand_dir=brand_dir, canvas_override=(virtual_w, virtual_h)
            )
            ext = ".excalidraw"
            prims = primitives_from_excalidraw_dsl(body, brand_dir, canvas_w=virtual_w)

        # Cache key must include every input the renderer actually depends
        # on. Hashing only `body` collides whenever two slides share the same
        # diagram id + body but differ on brand, region size, or kind — the
        # later render then overwrites the earlier PNG (Review #0.1).
        # Virtual canvas dimensions also participate so identical bodies
        # rendered at different scales don't collide. `_tokens_hash` (merged
        # extends chain) and `_layout_dir_name` are computed once above.
        # from_path and layout_dir prevent collisions across layouts that
        # embed the same external DSL file.
        key_blob = "|".join((
            str(slide_index),
            n.kind,
            f"{w}x{h}",
            f"v{virtual_w}x{virtual_h}",
            brand_dir.name,
            _tokens_hash,
            from_path or "",
            _layout_dir_name,
            body,
        ))
        body_hash = hashlib.sha1(key_blob.encode()).hexdigest()[:10]
        artifact = out_dir / f"s{slide_index}-{dsl_id}-{body_hash}{ext}"
        artifact.write_text(expanded_text)

        png = artifact.with_suffix(".png")
        render(artifact, png)

        # Build a picture-kind DSLNode.  Geometry goes into kw_args (consistent
        # with how diagram nodes store their own geometry).  Diagram metadata is
        # stuffed into the sentinel key ``_diagram_meta`` — DSLNode has no
        # dedicated metadata field, so this is the cleanest non-breaking option.
        pic = DSLNode(
            kind="picture",
            kw_args={
                "id": dsl_id,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "src": str(png),
                "_diagram_meta": {
                    "kind": n.kind,
                    "source_dsl": body,
                    "internal_primitives": [p.__dict__ for p in prims],
                    "virtual_canvas_w": virtual_w,
                    "virtual_canvas_h": virtual_h,
                    "slot_w": w,
                    "slot_h": h,
                },
            },
            line_no=n.line_no,
            source=n.source,
        )
        out.append(pic)
    return out


def _bind_params(
    cd: CompoundDef,
    call: DSLNode,
    diagnostics: list[ExpansionDiagnostic] | None = None,
) -> dict:
    """Build the binding dict for a compound call.

    Every declared parameter is bound — defaulted to "" when the caller
    omits it — so `{{ name }}` placeholders inside the body never leak
    through as literal text. Positional args fill in declaration order;
    keyword args override positional; `label` carries the trailing
    quoted string when present.

    Undeclared kwargs are accepted (so layouts can pass overrides), but
    a warning is emitted via `warnings.warn` AND an `unknown_param`
    diagnostic is appended (if `diagnostics` is provided) so the typo
    `vlaue:"x"` doesn't silently leak.
    """
    declared = set(cd.params)
    bindings: dict[str, str] = dict.fromkeys(cd.params, "")
    for i, p in enumerate(cd.params):
        if i < len(call.pos_args):
            bindings[p] = call.pos_args[i]
    for k, v in call.kw_args.items():
        if k not in declared:
            msg = (
                f"compound '{cd.name}' (called at {call.source}:{call.line_no}): "
                f"unknown parameter '{k}' (declared params: {sorted(declared) or '[]'})"
            )
            warnings.warn(msg, UserWarning, stacklevel=2)
            if diagnostics is not None:
                diagnostics.append(ExpansionDiagnostic(
                    kind="unknown_param",
                    message=msg,
                    source=call.source,
                    line_no=call.line_no,
                ))
        bindings[k] = v
    if call.label is not None:
        bindings.setdefault("label", call.label)
    return bindings
