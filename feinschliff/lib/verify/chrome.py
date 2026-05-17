"""Deterministic chrome scanners for Layer 1 verify.

Two scanners:
  - `scan_pp_chrome(prs)` — walk every <p:spTree> shape; flag drop-shadow
    effects, gradient fills, and outlines wider than 1pt. Mirrors what
    `pptx_emit.sanitize_chrome` is supposed to remove; this is the
    post-build assertion that sanitation actually ran.
  - `scan_chrome_drift(prs, tolerance_emu=...)` — for shapes whose name
    starts with a chrome-role prefix (logo/footer/header/pgmeta/...),
    compare positions across slides and flag drift > tolerance.
"""
from __future__ import annotations

from dataclasses import dataclass


_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

# Outline >1pt is "fat" by the restraint contract.
_OUTLINE_FAT_THRESHOLD_EMU = 12700

# Marker the emitter writes on a <p:sp> that opted in via `effect:allow`.
_EFFECT_ALLOW_ATTR = "effect-allow"


@dataclass
class ChromeDefect:
    kind: str             # "drop-shadow" | "gradient-fill" | "fat-outline" | "chrome-drift"
    slide_index: int      # 1-based
    shape_name: str
    detail: str

    def __str__(self) -> str:
        return f"slide {self.slide_index} [{self.kind}] {self.detail}"


def _shape_label(shape) -> str:
    if shape.has_text_frame and shape.text_frame.text.strip():
        return shape.text_frame.text.split("\n")[0][:40]
    return shape.name or "(unnamed)"


def _has_allow_marker(sp_element) -> bool:
    """True if any <p:sp> ancestor (inclusive) of sp_element carries
    effect-allow="1"."""
    cur = sp_element
    while cur is not None:
        if cur.tag.endswith("}sp") and cur.get(_EFFECT_ALLOW_ATTR) == "1":
            return True
        cur = cur.getparent()
    return False


def scan_pp_chrome(prs) -> list[ChromeDefect]:
    """Walk every slide's <p:spTree> and flag PowerPoint chrome that
    escaped sanitation."""
    out: list[ChromeDefect] = []
    for i, slide in enumerate(prs.slides, start=1):
        sptree = slide._element.find(f".//{{{_NS_P}}}spTree")
        if sptree is None:
            continue
        for shape in slide.shapes:
            sp_el = shape._element
            # Drop shadow / glow / soft-edge — unless this shape opted in.
            for eff in sp_el.iter(f"{{{_NS_A}}}effectLst"):
                if _has_allow_marker(eff.getparent()):
                    continue
                out.append(ChromeDefect(
                    kind="drop-shadow",
                    slide_index=i,
                    shape_name=_shape_label(shape),
                    detail="effectLst present (drop-shadow / glow / soft-edge)",
                ))
                break
            # Gradient fill.
            if sp_el.find(f".//{{{_NS_A}}}gradFill") is not None:
                out.append(ChromeDefect(
                    kind="gradient-fill",
                    slide_index=i,
                    shape_name=_shape_label(shape),
                    detail="gradFill present",
                ))
            # Outline wider than 1pt.
            for ln in sp_el.iter(f"{{{_NS_A}}}ln"):
                w_str = ln.get("w")
                if w_str is None:
                    continue
                try:
                    w = int(w_str)
                except ValueError:
                    continue
                if w > _OUTLINE_FAT_THRESHOLD_EMU:
                    out.append(ChromeDefect(
                        kind="fat-outline",
                        slide_index=i,
                        shape_name=_shape_label(shape),
                        detail=f"outline width {w} EMU > {_OUTLINE_FAT_THRESHOLD_EMU} (1pt)",
                    ))
                    break
    return out


# Shapes whose name starts with one of these prefixes are considered "chrome"
# (logo / header / footer / page-meta / wordmark). Their positions should be
# consistent across slides.
_CHROME_NAME_PREFIXES = ("logo", "footer", "header", "pgmeta", "wordmark", "chrome")

# Default tolerance — 4 design-px in EMU (4 × 6350).
_CHROME_DRIFT_TOLERANCE_EMU = 25400


def _is_chrome_shape(shape) -> bool:
    name = (shape.name or "").lower()
    return any(name.startswith(p) for p in _CHROME_NAME_PREFIXES)


def scan_chrome_drift(prs, *, tolerance_emu: int = _CHROME_DRIFT_TOLERANCE_EMU) -> list[ChromeDefect]:
    """Compare chrome-shape positions across slides. Flag any chrome-named
    shape whose left/top drifts more than `tolerance_emu` from the median
    position the shape holds across all slides where it appears."""
    grouped: dict[str, list[tuple[int, int, int]]] = {}
    for i, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if not _is_chrome_shape(shape):
                continue
            grouped.setdefault(shape.name, []).append((i, shape.left, shape.top))

    out: list[ChromeDefect] = []
    for name, positions in grouped.items():
        if len(positions) < 2:
            continue
        lefts = sorted(p[1] for p in positions)
        tops = sorted(p[2] for p in positions)
        median_left = lefts[len(lefts) // 2]
        median_top = tops[len(tops) // 2]
        for slide_idx, left, top in positions:
            dl = abs(left - median_left)
            dt = abs(top - median_top)
            if dl > tolerance_emu or dt > tolerance_emu:
                out.append(ChromeDefect(
                    kind="chrome-drift",
                    slide_index=slide_idx,
                    shape_name=name,
                    detail=(
                        f"position drift: Δleft={dl} EMU, Δtop={dt} EMU "
                        f"(tolerance {tolerance_emu} EMU)"
                    ),
                ))
    return out
