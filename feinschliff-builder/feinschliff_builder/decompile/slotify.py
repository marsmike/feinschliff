"""Slotify pass over decompiled `.slide.dsl` layouts.

The hybrid decompiler emits slide-faithful layouts whose text is LITERAL —
right for measuring decompile fidelity, useless as a fillable template. This
pass rewrites every literal text label into

    text … "{{ text_N | default(\"<original literal>\") }}"

so the layout becomes a real template: a bare build (empty ctx) renders the
original showcase copy via the `default(…)` filter, and a deck build binds
`text_1..text_N` in ctx to replace it. Picture placeholders are already
slotified at decompile time (`path:"{{ image | default(\"…\") }}"`); native
chrome (logos, custGeom decoration) intentionally stays fixed.

Grammar constraints honoured (see feinschliff/dsl/expander.py):
  * `_DEFAULT_FILTER_RE` allows no ASCII `"` inside default("…") — escaped
    quotes in the source literal are typographically curlified (“…”).
  * `_SLOT_RE` bodies cannot contain `{`/`}` — labels with braces stay
    literal rather than emitting a slot that cannot parse.

Slot numbering is per-file, in line order: text_1, text_2, …
"""
from __future__ import annotations

import re
from pathlib import Path

# A top-level text primitive whose trailing bare-quoted token is the label.
# Group 1 = everything up to the opening quote, group 2 = raw escaped label.
_TEXT_LINE_RE = re.compile(r'^(text\b[^"]*)"((?:[^"\\]|\\.)*)"\s*$')


def _curlify(raw: str) -> str:
    r"""Replace escaped ASCII quotes (`\"`) in a raw DSL literal with curly
    quotes so the literal can ride inside the expander's default("…") filter.
    Literal backslashes (`\\`) are protected first, mirroring the parser's
    `_unquote` ordering. Opening/closing forms alternate per run of text."""
    protected = raw.replace("\\\\", "\x00")
    out: list[str] = []
    open_next = True
    for chunk in protected.split('\\"'):
        out.append(chunk)
        out.append("“" if open_next else "”")
        open_next = not open_next
    s = "".join(out[:-1])  # drop the trailing quote added after the last chunk
    return s.replace("\x00", "\\\\")


def slotify_dsl(dsl_text: str) -> tuple[str, list[str]]:
    """Rewrite literal text labels in one layout's DSL into `text_N` slots.

    Returns `(new_dsl_text, slot_names)`. Lines left untouched: non-text
    primitives, empty labels, labels already containing a slot (`{{`), and
    labels with `{`/`}` (cannot ride in the slot grammar).
    """
    out_lines: list[str] = []
    slots: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        m = _TEXT_LINE_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue
        prefix, raw = m.group(1), m.group(2)
        if not raw or "{" in raw or "}" in raw:
            out_lines.append(line)
            continue
        name = f"text_{len(slots) + 1}"
        slots.append(name)
        default = _curlify(raw)
        new_body = f'{prefix}"{{{{ {name} | default(\\"{default}\\") }}}}"'
        out_lines.append(new_body + ("\n" if line.endswith("\n") else ""))
    return "".join(out_lines), slots


def slotify_layout_file(path: Path) -> list[str]:
    """Slotify one `.slide.dsl` in place; returns the created slot names."""
    text = path.read_text(encoding="utf-8")
    new_text, slots = slotify_dsl(text)
    if slots:
        path.write_text(new_text, encoding="utf-8")
    return slots


_SLOT_NAME_RE = re.compile(r"\{\{\s*(text_\d+)\b")
_TEXT_PREFIX_RE = re.compile(r'^(text\s+[^"]*?)\s*("(?:\{\{.*)$)')

# Roles whose boxes were sized for showcase copy but receive arbitrary real
# content — graceful shrink to the 10pt emit floor beats silent overflow.
_AUTOSHRINK_ROLES = frozenset({"title", "body"})


def add_autoshrink(dsl_text: str, slot_roles: dict[str, str]) -> str:
    """Add `autoshrink:true` to slot-bearing text lines whose slot role is
    title/body. Idempotent; never touches the quoted label."""
    out_lines: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        slot = _SLOT_NAME_RE.search(body)
        if (not body.startswith("text ") or slot is None
                or "autoshrink:" in body
                or slot_roles.get(slot.group(1)) not in _AUTOSHRINK_ROLES):
            out_lines.append(line)
            continue
        m = _TEXT_PREFIX_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue
        new_body = f"{m.group(1)} autoshrink:true {m.group(2)}"
        out_lines.append(new_body + ("\n" if line.endswith("\n") else ""))
    return "".join(out_lines)
