"""BrandPack — typed domain object for a feinschliff brand directory.

Replaces the legacy `Brand` dataclass from `feinschmiede.brand_discovery`. A BrandPack
loads and caches `tokens.json`, provides token resolution by dotted path, and
delegates layout/compound discovery to the toolkit's discovery layer.

Usage::

    pack = BrandPack.load(Path("brands/feinschliff"))
    hex_color = pack.resolve_token("color.accent")   # "#C9A24A"
    compound = pack.find_compound("footer")          # FoundCompound or None
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FoundCompound:
    name: str
    path: Path
    origin: str  # "brand-local" | "toolkit"


# ---------------------------------------------------------------------------
# BrandPack
# ---------------------------------------------------------------------------

class BrandPack:
    """Typed domain object representing a brand pack directory.

    Parameters are private; use `BrandPack.load(root)` to construct.
    """

    def __init__(
        self,
        root: Path,
        tokens: dict[str, Any],
        tokens_hash: str,
        *,
        image_provider_config: dict | None = None,
    ) -> None:
        self._root = root
        self._tokens = tokens
        self._tokens_hash = tokens_hash
        self._image_provider_config = image_provider_config

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, root: Path) -> "BrandPack":
        """Load a BrandPack from a brand directory.

        Parameters
        ----------
        root:
            Path to the brand directory (must contain `tokens.json`).

        Raises
        ------
        FileNotFoundError
            When `tokens.json` is absent.
        """
        tokens_path = root / "tokens.json"
        if not tokens_path.is_file():
            raise FileNotFoundError(
                f"BrandPack.load: {root!r} has no tokens.json"
            )
        raw_bytes = tokens_path.read_bytes()
        tokens = json.loads(raw_bytes)
        tokens_hash = hashlib.sha1(raw_bytes).hexdigest()[:12]
        return cls(root=root, tokens=tokens, tokens_hash=tokens_hash)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Brand directory name, e.g. ``'feinschliff'``."""
        return self._root.name

    # Alias kept for test parity with Brand.name
    @property
    def name(self) -> str:
        return self._root.name

    @property
    def root(self) -> Path:
        return self._root

    @property
    def tokens(self) -> dict[str, Any]:
        return self._tokens

    @property
    def tokens_hash(self) -> str:
        """12-char SHA-1 hex of tokens.json bytes."""
        return self._tokens_hash

    # ------------------------------------------------------------------
    # Sub-paths
    # ------------------------------------------------------------------

    @property
    def layouts_path(self) -> Path | None:
        """Brand-local layouts/ directory, or None when absent."""
        p = self._root / "layouts"
        return p if p.is_dir() else None

    @property
    def compounds_path(self) -> Path | None:
        """Brand-local compounds/ directory, or None when absent."""
        p = self._root / "compounds"
        return p if p.is_dir() else None

    # Convenience for callers that expect a direct Path (mirroring Brand)
    @property
    def tokens_path(self) -> Path | None:
        """Path to tokens.json if present."""
        p = self._root / "tokens.json"
        return p if p.is_file() else None

    @property
    def design_path(self) -> Path | None:
        """Path to DESIGN.md if present."""
        p = self._root / "DESIGN.md"
        return p if p.is_file() else None

    # ------------------------------------------------------------------
    # Token resolution
    # ------------------------------------------------------------------

    def resolve_token(self, dotted_path: str) -> Any | None:
        """Resolve a dotted key path against tokens.json.

        Example::

            pack.resolve_token("color.accent")   # "#C9A24A" or {"$value": "#C9A24A"}
            pack.resolve_token("missing.key")     # None

        Supports both bare strings and Design-Tokens ``{"$value": "..."}``
        objects at the leaf. Always returns the raw leaf value (not
        unwrapped) so callers can decide how to interpret $value wrappers.
        For plain hex extraction use ``brand_bridge.resolve()`` instead.
        """
        parts = dotted_path.split(".")
        node: Any = self._tokens
        for part in parts:
            if not isinstance(node, dict):
                return None
            if part not in node:
                return None
            node = node[part]
        return node

    # ------------------------------------------------------------------
    # Layout discovery
    #
    # NOTE: layout discovery (``find_layout`` / ``layout_table``) lived here
    # but pulled in ``feinschliff.layout_discovery`` — an engine→office
    # back-edge. The brand-local ``layouts_path`` (below) is the engine's
    # only layout responsibility; the toolkit-overlay precedence now lives
    # on the office side (``feinschliff.deck.picker``).
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Compound discovery
    # ------------------------------------------------------------------

    def find_compound(self, name: str) -> FoundCompound | None:
        """Locate a compound DSL file.

        Brand-local `compounds/` wins over toolkit bundled compounds.

        Parameters
        ----------
        name:
            Compound name, e.g. ``'footer'`` (without `.dsl`).

        Returns
        -------
        FoundCompound | None
        """
        # 1. Brand-local compounds/
        if self.compounds_path is not None:
            candidate = self.compounds_path / f"{name}.dsl"
            if candidate.is_file():
                return FoundCompound(name=name, path=candidate, origin="brand-local")
        # 2. Toolkit bundled compounds/
        toolkit_compounds = Path(__file__).resolve().parents[2] / "compounds"
        candidate = toolkit_compounds / f"{name}.dsl"
        if candidate.is_file():
            return FoundCompound(name=name, path=candidate, origin="toolkit")
        return None

    # ------------------------------------------------------------------
    # Image provider config (extends-resolved, set by discover_brands)
    # ------------------------------------------------------------------

    @property
    def image_provider_config(self) -> dict | None:
        """Extends-resolved ``$image_provider`` block from tokens.json.

        None when the brand (and none of its parents) declares a provider.
        Set externally by ``discover_brands`` so the extends-walk logic
        stays in one place.
        """
        return self._image_provider_config

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"BrandPack(id={self.id!r}, root={self._root!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BrandPack):
            return NotImplemented
        return self._root == other._root and self._tokens_hash == other._tokens_hash

    def __hash__(self) -> int:
        return hash((self._root, self._tokens_hash))
