"""Deck composer — typed DSL Document → PPTX.

Provides :class:`Deck`, a thin orchestrator that takes a typed
:class:`~feinschmiede.dsl.ast.Document` and a :class:`~feinschmiede.brand.pack.BrandPack`
and produces a ``.pptx`` file via the typed pipeline:

.. code-block:: text

    Document  →  expand_document(doc, pack)  →  emit_pptx_from_document(...)

The CLI layer (``cli/deck.py::cmd_build``) still runs the legacy
``compile_slide`` + ``build_multi_slide`` pipeline for the plan-YAML
path. :class:`Deck` targets the newer typed-AST path introduced in
Phase 1 (``parse_document`` → ``expand_document`` →
``emit_pptx_from_document``).

Usage::

    from pathlib import Path
    from feinschmiede.brand.pack import BrandPack
    from feinschliff.deck.compose import Deck
    from feinschmiede.dsl.ast import Document

    pack = BrandPack.load(Path("brands/feinschliff"))
    doc  = Document(...)   # or parse_document(text)
    deck = Deck(brand=pack, document=doc)
    out  = deck.build(Path("/tmp/out.pptx"))
    print(out)             # /tmp/out.pptx
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from feinschmiede.brand.pack import BrandPack
    from feinschmiede.dsl.ast import Document
    from feinschmiede.diagnostics import DiagnosticBag


class Deck:
    """Typed deck builder wrapping expand_document + emit_pptx_from_document.

    Parameters
    ----------
    brand:
        The brand pack used for token resolution and compound loading.
    document:
        The typed Document AST to render.  Obtain via
        :func:`feinschliff.dsl.parser.parse_document` or construct manually.
    """

    def __init__(self, brand: "BrandPack", document: "Document") -> None:
        self.brand = brand
        self.document = document
        self._diagnostics: "DiagnosticBag | None" = None

    # ── factory ───────────────────────────────────────────────────────────

    @classmethod
    def from_dsl_text(cls, text: str, brand: "BrandPack") -> "Deck":
        """Parse *text* as slide DSL and return a :class:`Deck`.

        Parameters
        ----------
        text:
            Raw DSL source (slide layout text or multi-slide document).
        brand:
            Brand pack applied during expansion and emit.
        """
        from feinschliff.dsl.parser import parse_document
        doc = parse_document(text)
        return cls(brand=brand, document=doc)

    @classmethod
    def from_dsl_path(cls, path: Path, brand: "BrandPack") -> "Deck":
        """Read *path* as slide DSL and return a :class:`Deck`."""
        return cls.from_dsl_text(path.read_text(encoding="utf-8"), brand=brand)

    @classmethod
    def from_brief(cls, brief_path: Path, brand: "BrandPack") -> "Deck":
        """Build a :class:`Deck` from a deck plan YAML (the "brief").

        Reads a plan YAML in the standard ``feinschliff deck build`` format
        (``brand:``, ``slides: [{layout:, content:}, …]``) and constructs a
        typed :class:`~feinschmiede.dsl.ast.Document` via
        :func:`feinschliff.deck.orchestrate.compose_from_brief`.

        Unlike the full ``deck build`` pipeline, slot interpolation
        (``{{ slot_name }}`` → content values) is **not** applied — layout
        placeholders are preserved as-is.  Use :meth:`build` to emit the PPTX.

        Parameters
        ----------
        brief_path:
            Path to a deck plan YAML.
        brand:
            Brand pack applied during expansion and emit.

        Returns
        -------
        Deck
            A :class:`Deck` whose ``document`` contains one
            :class:`~feinschmiede.dsl.ast.Slide` per slide in the brief.

        Raises
        ------
        FileNotFoundError
            When *brief_path* or a referenced layout DSL file cannot be found.
        ValueError
            When the plan YAML is missing the ``slides`` key.
        """
        from feinschliff.deck.orchestrate import compose_from_brief
        doc = compose_from_brief(brief_path, brand)
        return cls(brand=brand, document=doc)

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def diagnostics(self) -> "DiagnosticBag":
        """The :class:`~feinschmiede.diagnostics.DiagnosticBag` from the last build.

        Empty (no errors) before :meth:`build` has been called.
        """
        if self._diagnostics is None:
            from feinschmiede.diagnostics import DiagnosticBag
            return DiagnosticBag()
        return self._diagnostics

    # ── build ─────────────────────────────────────────────────────────────

    def build(self, out_path: Path) -> Path:
        """Expand the document and emit a PPTX at *out_path*.

        Steps:
        1. :func:`~feinschliff.dsl.expander.expand_document` — expand compound
           calls into primitive elements using the brand's compounds.
        2. :func:`~feinschliff.dsl.pptx_emit.emit_pptx_from_document` — render
           the expanded Document to a ``.pptx`` file.

        Parameters
        ----------
        out_path:
            Destination ``.pptx`` path (parent directories are created
            if they don't exist).

        Returns
        -------
        Path
            The written *out_path*.
        """
        from feinschliff.dsl.expander import expand_document
        from feinschliff.dsl.pptx_emit import emit_pptx_from_document

        out_path.parent.mkdir(parents=True, exist_ok=True)
        expanded = expand_document(self.document, self.brand)
        return emit_pptx_from_document(expanded, self.brand, out_path)
