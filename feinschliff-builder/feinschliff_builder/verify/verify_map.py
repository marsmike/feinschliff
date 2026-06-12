"""Loader for ``<brand-pack>/verify-map.yaml``.

Schema
------
The file is a YAML mapping with one required key and one optional key:

.. code-block:: yaml

    layouts:                         # required
      cover-dark: 1                  # layout-name → 1-based source slide number
      quote: 11
      …
    chart_bboxes:                    # optional
      quote: [75, 195, 1770, 410]    # layout-name → [x, y, w, h] in design px
      timeline: [55, 165, 1810, 660]

``layouts`` maps every layout name to the 1-based slide index in the source
PPTX that the layout was derived from.  All scripts that run visual diffs,
decompile runs, or source-region extractions are driven by this mapping.

``chart_bboxes`` is used only by ``brand_source_extract.py``: it gives an
explicit design-coordinate bounding box for a layout whose "chart" area
should be pixel-compared against the source rather than being masked.

Public API
----------
:func:`load_verify_map` — parse + validate; raises on missing or malformed.
:attr:`VerifyMap.layouts` — ``dict[str, int]``
:attr:`VerifyMap.chart_bboxes` — ``dict[str, list[int]]`` (may be empty)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class VerifyMap:
    """Parsed and validated contents of a ``verify-map.yaml`` file.

    Attributes
    ----------
    layouts:
        Mapping from layout name to 1-based source-slide number.
    chart_bboxes:
        Optional per-layout bounding boxes ``[x, y, w, h]`` in design pixels
        (1920 × 1080 space) for chart-region pixel comparison.  Empty dict
        when the key is absent from the file.
    """

    layouts: dict[str, int]
    chart_bboxes: dict[str, list[int]] = field(default_factory=dict)


def load_verify_map(brand_dir: Path) -> VerifyMap:
    """Parse and validate ``<brand_dir>/verify-map.yaml``.

    Parameters
    ----------
    brand_dir:
        The brand-pack root directory.  The file ``verify-map.yaml`` is
        expected directly inside it.

    Returns
    -------
    VerifyMap
        Parsed and lightly validated map.  ``layouts`` values are coerced to
        ``int`` so callers get a clean ``dict[str, int]`` regardless of
        whether the YAML was written as bare integers or strings.

    Raises
    ------
    FileNotFoundError
        If ``<brand_dir>/verify-map.yaml`` does not exist.
    ValueError
        If the file cannot be parsed as YAML, if ``layouts`` is missing, or
        if any layout value cannot be coerced to a positive integer.
    """
    map_path = brand_dir / "verify-map.yaml"
    if not map_path.is_file():
        raise FileNotFoundError(f"missing verify-map.yaml in {brand_dir}")

    try:
        raw: Any = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed YAML in {map_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(
            f"{map_path}: expected a YAML mapping at the top level, "
            f"got {type(raw).__name__}"
        )

    raw_layouts = raw.get("layouts")
    if raw_layouts is None:
        raise ValueError(f"{map_path}: missing required key 'layouts'")
    if not isinstance(raw_layouts, dict):
        raise ValueError(
            f"{map_path}: 'layouts' must be a mapping, "
            f"got {type(raw_layouts).__name__}"
        )

    layouts: dict[str, int] = {}
    for name, value in raw_layouts.items():
        try:
            slide_no = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{map_path}: layout '{name}' has non-integer slide number "
                f"{value!r}"
            ) from exc
        if slide_no < 1:
            raise ValueError(
                f"{map_path}: layout '{name}' slide number must be ≥ 1, "
                f"got {slide_no}"
            )
        layouts[str(name)] = slide_no

    raw_bboxes = raw.get("chart_bboxes") or {}
    if not isinstance(raw_bboxes, dict):
        raise ValueError(
            f"{map_path}: 'chart_bboxes' must be a mapping, "
            f"got {type(raw_bboxes).__name__}"
        )
    chart_bboxes: dict[str, list[int]] = {}
    for name, bbox in raw_bboxes.items():
        if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
            raise ValueError(
                f"{map_path}: chart_bboxes['{name}'] must be a list of 4 "
                f"integers [x, y, w, h], got {bbox!r}"
            )
        try:
            chart_bboxes[str(name)] = [int(v) for v in bbox]
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{map_path}: chart_bboxes['{name}'] contains non-integer "
                f"value: {bbox!r}"
            ) from exc

    return VerifyMap(layouts=layouts, chart_bboxes=chart_bboxes)
