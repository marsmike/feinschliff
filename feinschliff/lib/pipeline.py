# feinschliff/lib/pipeline.py
"""Shared per-slide compile pipeline.

Every CLI entrypoint that emits a `.pptx` slide flows through
`compile_slide()`. Returns a `CompileResult` carrying the emitted
primitives, all collected defects, and the slide canvas size.

This is the only place `validate_diagrams*` should be called outside of
unit tests. The returned defects use the `lib.defects.Defect` dataclass —
caller decides which severities to honor and which to demote.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from lib.defects import Defect, DefectKind, Severity
from lib.diagrams.structural_validator import (
    validate_excalidraw_structure,
    validate_svg_structure,
)
from lib.dsl.expander import (
    expand_compounds,
    expand_diagram_blocks,
    interpolate_nodes,
    load_compounds_for_brand,
)
from lib.dsl.parser import parse_file
from lib.dsl.pptx_emit import _slide_canvas
from lib.dsl.tokens import load_tokens
from lib.layout_validator import (
    validate_diagrams,
    validate_diagrams_color,
    validate_diagrams_text_size,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
STD_COMPOUNDS = REPO_ROOT / "compounds"
BRANDS_DIR = REPO_ROOT / "brands"


@dataclasses.dataclass(frozen=True)
class CompileResult:
    primitives: list[Any]
    tokens: dict[str, Any]
    canvas: tuple[int, int]
    defects: list[Defect]


def compile_slide(
    *,
    layout_path: Path,
    ctx: dict[str, Any],
    brand_dir: Path,
    slide_index: int,
    diagrams_out_dir: Path,
) -> CompileResult:
    diagrams_out_dir.mkdir(parents=True, exist_ok=True)

    tokens = load_tokens(brand_dir, brands_dir=BRANDS_DIR)
    compounds = load_compounds_for_brand(
        brand_dir, std_dir=STD_COMPOUNDS, brands_dir=BRANDS_DIR,
    )

    layout_nodes, layout_compounds = parse_file(layout_path)
    for cd in layout_compounds:
        compounds[cd.name] = cd

    interp = interpolate_nodes(layout_nodes, ctx)
    interp = expand_diagram_blocks(
        interp,
        brand_dir=brand_dir,
        out_dir=diagrams_out_dir,
        layout_dir=layout_path.parent,
        slide_index=slide_index,
    )

    sw, sh = _slide_canvas(interp)

    defects: list[Defect] = []
    raw: list = []
    raw.extend(validate_diagrams(interp, slide_index=slide_index, slide_w=sw, slide_h=sh))
    raw.extend(validate_diagrams_color(interp, slide_index=slide_index, brand_dir=brand_dir))
    raw.extend(validate_diagrams_text_size(interp, slide_index=slide_index, slide_w=sw, slide_h=sh))
    for r in raw:
        defects.append(_legacy_to_defect(r, slide_index))

    # Structural lint over every diagram artifact this slide just wrote.
    # `expand_diagram_blocks` writes `s<idx>-<id>-<hash>.{excalidraw,svg}`
    # files into `diagrams_out_dir` (see lib/dsl/expander.py); scanning by
    # slide_index prefix is deterministic and won't double-count earlier
    # slides' files.
    for artifact in diagrams_out_dir.glob(f"s{slide_index}-*.excalidraw"):
        try:
            doc = json.loads(artifact.read_text())
        except json.JSONDecodeError:
            # File-level malformed JSON is caught by validate_excalidraw_file
            # in the CLI; here we just skip rather than crash the build.
            continue
        for d in validate_excalidraw_structure(doc):
            # validate_excalidraw_structure stamps slide_index=0 by default;
            # restamp with the real index so reports group correctly.
            defects.append(dataclasses.replace(d, slide_index=slide_index))
    for artifact in diagrams_out_dir.glob(f"s{slide_index}-*.svg"):
        try:
            svg_text = artifact.read_text()
        except OSError:
            continue
        for d in validate_svg_structure(svg_text):
            defects.append(dataclasses.replace(d, slide_index=slide_index))

    primitives, diagnostics = expand_compounds(interp, compounds)
    for d in diagnostics:
        if d.kind == "unknown_compound":
            defects.append(Defect(
                slide_index=slide_index,
                kind=DefectKind.UNKNOWN_COMPOUND,
                severity=Severity.FATAL,
                message=f"unknown compound: Check the compound name or load order. {d.format()}",
                meta={"diagnostic_kind": d.kind},
            ))

    return CompileResult(
        primitives=primitives,
        tokens=tokens,
        canvas=(sw, sh),
        defects=defects,
    )


_KIND_MAP = {
    "diagram-overflow": DefectKind.DIAGRAM_OVERFLOW,
    "diagram-text-too-small": DefectKind.DIAGRAM_TEXT_TOO_SMALL,
    "diagram-color-mismatch": DefectKind.DIAGRAM_COLOR_MISMATCH,
}


def _legacy_to_defect(legacy_obj: Any, slide_index: int) -> Defect:
    kind_str = getattr(legacy_obj, "kind", None) or "diagram-overflow"
    kind = _KIND_MAP.get(kind_str, DefectKind.DIAGRAM_OVERFLOW)
    return Defect(
        slide_index=slide_index,
        kind=kind,
        severity=Severity.FATAL if kind_str in {"diagram-overflow", "diagram-text-too-small"} else Severity.WARN,
        message=getattr(legacy_obj, "message", str(legacy_obj)),
        meta={k: v for k, v in getattr(legacy_obj, "__dict__", {}).items() if not k.startswith("_")},
    )
