"""Renderer Protocol + concrete backends for Excalidraw / SVG diagrams.

The :class:`Renderer` Protocol defines the interface that any rendering
backend must satisfy.  Two implementations ship out of the box:

- :class:`RoughRenderer` — pure-Python ``rough`` + ``cairosvg``, ~150 ms
  per diagram, no browser.  Supports the full Feinschliff Excalidraw
  vocabulary (rectangle / ellipse / diamond / line / arrow / text / dot /
  group) but rejects ``freedraw``, ``image``, and ``frame`` elements.

- :class:`PlaywrightRenderer` — headless Chromium via Playwright running
  the real ``@excalidraw/excalidraw`` ESM bundle.  Supports every element
  type and is the authoritative fallback.

The module-level registry plus :func:`choose_renderer` replaces the raw
try/except dispatch that lived inline in ``render.py``; ``render.py`` is
now a thin facade that delegates here.  Third-party back-ends can be
injected via :func:`register_renderer`.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass

# ── unsupported element types for the rough path ────────────────────────────

_ROUGH_UNSUPPORTED_TYPES = frozenset({"freedraw", "image", "frame", "embeddable"})


# ──────────────────────────────────────────────────────────────────────────────
# Protocol
# ──────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class Renderer(Protocol):
    """Protocol satisfied by every diagram rendering backend.

    The ``name`` attribute is used for debugging / registry introspection.
    ``supports`` guards ``choose_renderer`` — return ``False`` when the
    backend cannot handle the given source document.
    """

    name: str

    def supports(self, src: Path) -> bool:
        """Return True if this backend can render the document at *src*."""
        ...

    def render_png(self, src: Path, out: Path) -> Path:
        """Render *src* to a PNG at *out* and return *out*."""
        ...


# ──────────────────────────────────────────────────────────────────────────────
# RoughRenderer
# ──────────────────────────────────────────────────────────────────────────────

class RoughRenderer:
    """Pure-Python Excalidraw → PNG via ``rough`` + ``cairosvg``.

    Supports the canonical Feinschliff diagram vocabulary.  Rejects
    documents that contain ``freedraw``, ``image``, ``frame``, or
    ``embeddable`` elements — those require the real Excalidraw web app
    (see :class:`PlaywrightRenderer`).
    """

    name = "rough"

    # ── availability ──────────────────────────────────────────────────────

    @staticmethod
    def _available() -> bool:
        try:
            import rough  # noqa: F401
            import cairosvg  # noqa: F401
            return True
        except (ImportError, OSError):
            return False

    # ── supports ──────────────────────────────────────────────────────────

    def supports(self, src: Path) -> bool:
        """Return True iff the rough path can handle this document.

        Conditions (all must hold):
        1. ``rough`` and ``cairosvg`` are importable.
        2. The source is a ``.excalidraw`` file (not ``.svg`` — the rough
           renderer only speaks the Excalidraw JSON vocabulary).
        3. No element in the document has a type in
           ``_ROUGH_UNSUPPORTED_TYPES``.
        """
        if src.suffix.lower() != ".excalidraw":
            return False
        if not self._available():
            return False
        try:
            import json
            data = json.loads(src.read_text(encoding="utf-8"))
            elements = [e for e in data.get("elements", []) if not e.get("isDeleted")]
            return not any(
                e.get("type") in _ROUGH_UNSUPPORTED_TYPES for e in elements
            )
        except (OSError, ValueError, KeyError):
            # If we can't read/parse, don't claim support — let Playwright try.
            return False

    # ── render ────────────────────────────────────────────────────────────

    def render_png(self, src: Path, out: Path) -> Path:
        from feinschmiede.diagrams.render_rough import render_excalidraw
        return render_excalidraw(src, out, style="clean")


# ──────────────────────────────────────────────────────────────────────────────
# PlaywrightRenderer
# ──────────────────────────────────────────────────────────────────────────────

class PlaywrightRenderer:
    """Playwright + real Excalidraw web app fallback renderer.

    Supports every element type the Excalidraw web app supports.  Heavier
    (~1.5 s cold, ~200 MB Chromium) but authoritative.  Also handles
    plain ``.svg`` sources via a minimal page render.
    """

    name = "playwright"

    def supports(self, src: Path) -> bool:
        """Playwright handles both ``.excalidraw`` and ``.svg`` sources."""
        return src.suffix.lower() in (".excalidraw", ".svg")

    def render_png(self, src: Path, out: Path) -> Path:
        ext = src.suffix.lower()
        if ext == ".excalidraw":
            from feinschmiede.diagrams.render_playwright import render_excalidraw
            return render_excalidraw(src, out)
        # .svg path: inline SVG → Playwright screenshot
        from feinschmiede.diagrams.render import _render_svg_playwright
        return _render_svg_playwright(src, out)


# ──────────────────────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────────────────────

_REGISTRY: list[Renderer] = [RoughRenderer(), PlaywrightRenderer()]


def choose_renderer(src: Path) -> Renderer:
    """Return the first registered :class:`Renderer` that supports *src*.

    Raises :exc:`RuntimeError` when no renderer claims support —
    callers should ensure the registry always includes
    :class:`PlaywrightRenderer` as a catchall unless intentionally stripped.
    """
    for r in _REGISTRY:
        if r.supports(src):
            return r
    raise RuntimeError(
        f"choose_renderer: no registered backend supports {src!r}. "
        "Install rough+cairosvg (preferred) or playwright+chromium (fallback)."
    )


def register_renderer(r: Renderer, priority: int = 0) -> None:
    """Insert *r* into the global registry at *priority* (0 = highest)."""
    _REGISTRY.insert(priority, r)
