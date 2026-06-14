from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .extract import extract_text_from_pptx

_FALLBACK_LAYOUTS: dict[str, str] = {
    "cover": "title-cover",
    "closer": "closer",
    "content": "content-columns",
}


@dataclass
class CosmeticReport:
    slides_preserved: int
    slides_dropped: int
    warnings: list[str]
    plan_path: Path


def _role_for(index: int, total: int) -> str:
    if index == 1:
        return "cover"
    if total >= 2 and index == total:
        return "closer"
    return "content"


def _coerce_layout_name(value: object) -> str:
    """Accept a string or list[str]; return a single name."""
    if isinstance(value, list):
        return value[0]
    return str(value)


def cosmetic_polish(
    src_pptx: Path,
    brand: str,
    out_pptx: Path,
) -> CosmeticReport:
    """Build a cosmetic-polish plan YAML for *src_pptx* using *brand*.

    Extracts text from every slide, assigns a layout from the brand's
    deck-map.yaml (or falls back to toolkit defaults), and writes a plan YAML
    next to *out_pptx*.  The caller is responsible for running
    ``feinschliff deck build`` on the plan.

    Returns a :class:`CosmeticReport` describing what was found.
    """
    from feinschmiede.brand_discovery import find_brand
    from feinschliff.deck.content_metadata import load_deck_map
    from feinschliff.deck.orchestrate import resolve_layout_path

    brand_pack = find_brand(brand)
    brand_root: Path = Path(brand_pack.root)

    deck_map = load_deck_map(brand_pack)

    warn_msgs: list[str] = []

    def _layout_for_role(role: str) -> str:
        if deck_map:
            dm_section = deck_map.get("layouts", deck_map)
            raw = dm_section.get(role)
            if raw:
                return _coerce_layout_name(raw)
        # Missing in deck-map — warn and fall back
        fallback = _FALLBACK_LAYOUTS.get(role, "content-columns")
        warn_msgs.append(
            f"deck-map.yaml missing '{role}'; falling back to toolkit default '{fallback}'."
        )
        return fallback

    slide_texts = extract_text_from_pptx(src_pptx)
    total = len(slide_texts)

    slides_out: list[dict] = []
    for st in slide_texts:
        role = _role_for(st.index, total)
        layout_name = _layout_for_role(role)
        layout_path = resolve_layout_path(brand_root, layout_name)

        if layout_path is None:
            # Fall through to a raw name string so the builder can diagnose
            layout_str = layout_name
        else:
            layout_str = str(layout_path)

        if st.has_chart:
            warn_msgs.append(
                f"Slide {st.index} has a chart; cosmetic mode does not preserve charts."
                " Use --mode redesign to rebuild."
            )
        if st.has_table:
            warn_msgs.append(
                f"Slide {st.index} has a table; cosmetic mode does not preserve tables."
                " Use --mode redesign to rebuild."
            )
        if st.has_image:
            warn_msgs.append(
                f"Slide {st.index} has an embedded image; cosmetic mode strips images."
                " Use --mode redesign to preserve them."
            )

        slides_out.append(
            {
                "layout": layout_str,
                "content_inline": {
                    "title": st.title,
                    "body": st.body,
                    "notes": st.notes,
                },
            }
        )

    plan: dict = {
        "brand": brand,
        "out": str(out_pptx),
        "slides": slides_out,
    }

    plan_path = out_pptx.parent / "cosmetic.plan.yaml"
    plan_path.write_text(yaml.safe_dump(plan, allow_unicode=True, sort_keys=False), encoding="utf-8")

    return CosmeticReport(
        slides_preserved=total,
        slides_dropped=0,
        warnings=warn_msgs,
        plan_path=plan_path,
    )
