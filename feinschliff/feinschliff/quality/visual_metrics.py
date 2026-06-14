from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class VisualMetricsIssue:
    slide: int          # 1-based
    metric: str         # "whitespace" | "collision" | "balance"
    severity: str       # "warn" | "fail"
    message: str
    value: float        # the measured value
    threshold: tuple[float, float] | float  # expected range or threshold


@dataclass(frozen=True)
class VisualMetricsResult:
    per_slide: dict[int, dict[str, float]]
    # {1: {"whitespace": 0.45, "balance": 0.08, "collision_pairs": 0}, ...}
    issues: list[VisualMetricsIssue]
    verdict: str  # "clean" | "warn" | "fail"


def _measure_whitespace(img: Image.Image) -> float:
    """Fraction of near-white pixels (all channels >= 245)."""
    rgb = img.convert("RGB")
    width, height = rgb.size
    total = width * height
    white = 0
    pixels = rgb.load()
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if r >= 245 and g >= 245 and b >= 245:
                white += 1
    return white / total if total > 0 else 1.0


def _measure_collision_pairs(img: Image.Image) -> int:
    """Count cells with >=3 occupied rook-adjacent neighbours in a 12x8 grid.

    Each cell is 'occupied' when >=10% of its pixels are non-white.
    Returns the number of such dense cells as a proxy for layout crowding.
    """
    rgb = img.convert("RGB")
    width, height = rgb.size
    cols, rows = 12, 8
    cell_w = max(width // cols, 1)
    cell_h = max(height // rows, 1)
    pixels = rgb.load()

    occupied: list[list[bool]] = []
    for row in range(rows):
        occupied_row: list[bool] = []
        for col in range(cols):
            x0 = col * cell_w
            y0 = row * cell_h
            x1 = min(x0 + cell_w, width)
            y1 = min(y0 + cell_h, height)
            cell_total = (x1 - x0) * (y1 - y0)
            if cell_total == 0:
                occupied_row.append(False)
                continue
            non_white = 0
            for cy in range(y0, y1):
                for cx in range(x0, x1):
                    r, g, b = pixels[cx, cy]
                    if not (r >= 245 and g >= 245 and b >= 245):
                        non_white += 1
            occupied_row.append(non_white / cell_total >= 0.10)
        occupied.append(occupied_row)

    dense = 0
    for row in range(rows):
        for col in range(cols):
            if not occupied[row][col]:
                continue
            neighbours = 0
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = row + dr, col + dc
                if 0 <= nr < rows and 0 <= nc < cols and occupied[nr][nc]:
                    neighbours += 1
            if neighbours >= 3:
                dense += 1
    return dense


def _measure_balance(img: Image.Image) -> float:
    """Centre-of-mass deviation: distance(CoM, centre) / diagonal."""
    gray = img.convert("L")
    width, height = gray.size
    pixels = gray.load()

    sum_w = 0.0
    sum_wx = 0.0
    sum_wy = 0.0
    for y in range(height):
        for x in range(width):
            v = pixels[x, y]
            if v < 245:  # non-white
                weight = 245 - v
                sum_w += weight
                sum_wx += weight * x
                sum_wy += weight * y

    if sum_w == 0:
        return 0.0  # blank image — perfectly balanced

    com_x = sum_wx / sum_w
    com_y = sum_wy / sum_w
    cx = width / 2.0
    cy = height / 2.0
    dist = ((com_x - cx) ** 2 + (com_y - cy) ** 2) ** 0.5
    diagonal = (width ** 2 + height ** 2) ** 0.5
    return dist / diagonal if diagonal > 0 else 0.0


def compute_visual_metrics(
    png_paths: list[Path] | dict[int, Path],
    *,
    whitespace_range: tuple[float, float] = (0.25, 0.65),
    balance_threshold: float = 0.15,
    collision_max_pairs: int = 0,
) -> VisualMetricsResult:
    """Compute AeSlides visual metrics on rendered slide PNGs.

    Args:
        png_paths: 1-based dict {slide_index: path} or a list of paths
            (list index 0 → slide 1).
        whitespace_range: acceptable [low, high] fraction of near-white
            pixels. Outside this range → warn.
        balance_threshold: max allowed CoM-to-centre deviation as a
            fraction of the image diagonal. Exceeding → warn.
        collision_max_pairs: max allowed dense cells (>=3 occupied
            neighbours). Exceeding → warn.

    Returns:
        VisualMetricsResult with per_slide metrics, issues list, and
        overall verdict ("clean" | "warn" | "fail").
    """
    if isinstance(png_paths, list):
        indexed: dict[int, Path] = {i + 1: p for i, p in enumerate(png_paths)}
    else:
        indexed = dict(png_paths)

    per_slide: dict[int, dict[str, float]] = {}
    issues: list[VisualMetricsIssue] = []

    for slide_idx in sorted(indexed):
        path = indexed[slide_idx]
        img = Image.open(path)

        ws = _measure_whitespace(img)
        bal = _measure_balance(img)
        col = _measure_collision_pairs(img)

        per_slide[slide_idx] = {
            "whitespace": ws,
            "balance": bal,
            "collision_pairs": float(col),
        }

        lo, hi = whitespace_range
        if not (lo <= ws <= hi):
            direction = "overcrowded" if ws < lo else "sparse"
            issues.append(VisualMetricsIssue(
                slide=slide_idx,
                metric="whitespace",
                severity="warn",
                message=(
                    f"{ws:.2f} outside range ({lo}-{hi}). "
                    f"Slide may be {direction}."
                ),
                value=ws,
                threshold=whitespace_range,
            ))

        if bal > balance_threshold:
            issues.append(VisualMetricsIssue(
                slide=slide_idx,
                metric="balance",
                severity="warn",
                message=(
                    f"Centre-of-mass deviation {bal:.3f} exceeds "
                    f"threshold {balance_threshold}. Content may be "
                    f"visually off-centre."
                ),
                value=bal,
                threshold=balance_threshold,
            ))

        if col > collision_max_pairs:
            issues.append(VisualMetricsIssue(
                slide=slide_idx,
                metric="collision",
                severity="warn",
                message=(
                    f"{col} dense region(s) detected "
                    f"(max allowed: {collision_max_pairs})."
                ),
                value=float(col),
                threshold=float(collision_max_pairs),
            ))

    if not issues:
        verdict = "clean"
    else:
        severities = {i.severity for i in issues}
        verdict = "fail" if "fail" in severities else "warn"

    return VisualMetricsResult(
        per_slide=per_slide,
        issues=issues,
        verdict=verdict,
    )
