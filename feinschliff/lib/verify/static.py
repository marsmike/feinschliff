"""Pre-render static geometry verify.

Inspects a plan.yaml dict (post-merge, content filled) for geometry defects
that do NOT require rendering. Returns one :class:`~lib.defects.Defect` per
problem; empty list = clean.

Two defect classes are detected:

- **SLOT_OVERFLOW** — text in ``slide.content[slot]`` exceeds the pixel
  budget computed from the layout's ``maxwidth``/``maxheight`` nodes.
  Delegates to :func:`lib.content_validator._check_slot_overflow` via the
  same ``textfit.fits()`` helper the autoshrink emitter uses.

- **EMPTY_PLACEHOLDER** — a slot that the layout interpolates via
  ``{{ slot_name }}`` is either absent from the content dict or is an empty
  / whitespace-only string. Severity is WARN (not fatal); the orchestrator
  decides whether to abort.

Usage::

    from pathlib import Path
    from lib.verify.static import static_verify

    defects = static_verify(plan, brand_dir=Path("brands/feinschliff"))
    for d in defects:
        print(d)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from lib.defects import Defect, DefectKind, Severity

# Slot interpolation RE — matches {{ slot_name }}, {{ cells[0].heading }}, etc.
_SLOT_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
# Normalise array indices: cells[0].heading → cells[].heading
_IDX_RE = re.compile(r"\[\d+\]")


REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDS_DIR = REPO_ROOT / "brands"
STD_COMPOUNDS = REPO_ROOT / "compounds"


def _resolve_layout_path(plan_dir: Path, layout_rel: str) -> Path | None:
    """Resolve a layout path from the plan directory or repo root."""
    candidate = (plan_dir / layout_rel).resolve()
    if candidate.is_file():
        return candidate
    candidate2 = (REPO_ROOT / layout_rel).resolve()
    if candidate2.is_file():
        return candidate2
    return None


def _collect_interpolated_slots(nodes: list) -> set[str]:
    """Walk DSL nodes and collect the normalised slot names that appear in
    ``{{ slot }}`` interpolations inside text labels.

    Only returns slots where the entire label is a single interpolation
    (or the label contains the interpolation as a substring). Array indices
    are normalised to ``[]`` so they match the content validator's convention.

    This is deliberately broad — any ``{{ slot }}`` that appears in any text
    node is treated as required (WARN if missing, not fatal).
    """
    from lib.dsl.parser import DSLNode

    required: set[str] = set()

    def _visit(node: DSLNode) -> None:
        # text nodes carry a `label` attribute
        label = getattr(node, "label", None) or ""
        for m in _SLOT_RE.finditer(label):
            raw = m.group(1).strip()
            normalised = _IDX_RE.sub("[]", raw)
            # Only track top-level simple slot names, not compound ones like
            # `kpis[].value` — the content validator handles those via budget
            # lookup. We track them all: WARN severity means false positives
            # (optional slots flagged) are tolerable.
            required.add(normalised)
        # recurse into children (e.g. compound body)
        for child in getattr(node, "children", None) or []:
            _visit(child)

    for node in nodes:
        _visit(node)
    return required


def _flatten_content_keys(ctx: dict, prefix: str = "") -> dict[str, str]:
    """Flatten a nested content dict to normalised-path → value.

    Mirrors the normalisation in ``lib.content_validator._iter_slot_values``:
    array indices collapse to ``[]``.
    """
    out: dict[str, str] = {}
    if isinstance(ctx, dict):
        for k, v in ctx.items():
            child = f"{prefix}.{k}" if prefix else k
            out.update(_flatten_content_keys(v, child))
    elif isinstance(ctx, list):
        for item in ctx:
            out.update(_flatten_content_keys(item, f"{prefix}[]"))
    elif isinstance(ctx, str):
        out[prefix] = ctx
    return out


def static_verify(
    plan: dict,
    brand_dir: Path,
    *,
    plan_dir: Path | None = None,
) -> list[Defect]:
    """Inspect a plan dict for geometry defects without rendering.

    Parameters
    ----------
    plan:
        The loaded plan.yaml dict (post-merge, content filled in). The dict
        must contain a ``slides`` list with entries that each carry at least
        a ``layout`` field.
    brand_dir:
        Path to the active brand directory (used by ``load_tokens`` and
        ``load_compounds_for_brand``).
    plan_dir:
        Directory that ``layout:`` paths in the plan are resolved relative to.
        When *None* (the default), falls back to ``REPO_ROOT`` — matching the
        historical behaviour for toolkit layouts.  CLI callers that load a plan
        from a file should pass ``plan_path.parent`` so brand-relative layout
        overrides (e.g. ``brands/acme/layouts/cover.slide.dsl``) resolve
        correctly.

    Returns
    -------
    list[Defect]
        One :class:`~lib.defects.Defect` per detected problem.  Empty list
        means clean.  All defects are :attr:`~lib.defects.Severity.WARN`.
    """
    from lib.dsl.parser import parse_file
    from lib.dsl.tokens import load_tokens
    from lib.dsl.expander import load_compounds_for_brand
    from lib.slot_budget import compute_slot_budgets
    from lib.content_validator import (
        _check_slot_overflow,
        _iter_slot_values,
        ContentDefect,
    )

    defects: list[Defect] = []
    slides_spec = plan.get("slides") or []

    # Resolve layout paths against plan_dir when supplied; fall back to
    # REPO_ROOT so existing callers that don't pass plan_dir are unaffected.
    effective_plan_dir = plan_dir if plan_dir is not None else REPO_ROOT

    tokens = load_tokens(brand_dir, brands_dir=BRANDS_DIR)
    compounds = load_compounds_for_brand(
        brand_dir, std_dir=STD_COMPOUNDS, brands_dir=BRANDS_DIR
    )

    for i, spec in enumerate(slides_spec):
        slide_index = i + 1
        layout_rel = spec.get("layout", "")

        layout_path = _resolve_layout_path(effective_plan_dir, layout_rel)
        if layout_path is None:
            # Can't resolve layout → skip, don't crash
            print(
                f"verify-static: slide {slide_index}: layout not found: "
                f"{layout_rel!r} — skipped",
                file=sys.stderr,
            )
            continue

        try:
            layout_nodes, layout_compounds = parse_file(layout_path)
        except Exception as exc:  # noqa: BLE001
            print(
                f"verify-static: slide {slide_index}: parse error in "
                f"{layout_path.name}: {exc} — skipped",
                file=sys.stderr,
            )
            continue

        # Merge layout-local compounds into the brand compounds dict.
        local_compounds = dict(compounds)
        for cd in layout_compounds:
            local_compounds[cd.name] = cd

        ctx = spec.get("content") or {}

        # ── 1. EMPTY_PLACEHOLDER ──────────────────────────────────────────
        # Collect all {{ slot }} interpolations in the layout and check
        # whether each is supplied and non-empty in the content dict.
        interpolated = _collect_interpolated_slots(layout_nodes)
        flat_content = _flatten_content_keys(ctx)

        for slot_path in sorted(interpolated):
            value = flat_content.get(slot_path)
            if value is None or (isinstance(value, str) and not value.strip()):
                defects.append(Defect(
                    slide_index=slide_index,
                    kind=DefectKind.EMPTY_PLACEHOLDER,
                    severity=Severity.WARN,
                    message=(
                        f"slot {slot_path!r} is empty or missing "
                        f"(layout: {layout_path.name})"
                    ),
                    meta={"slot": slot_path, "layout": layout_path.name},
                ))

        # ── 2. SLOT_OVERFLOW ─────────────────────────────────────────────
        # Compute per-slot pixel budgets from the DSL and check whether
        # the supplied content will fit without wrapping beyond max_lines.
        try:
            slot_budgets = compute_slot_budgets(
                layout_nodes, tokens, compounds=local_compounds
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"verify-static: slide {slide_index}: could not compute "
                f"slot budgets for {layout_path.name}: {exc} — overflow "
                "checks skipped",
                file=sys.stderr,
            )
            slot_budgets = {}

        if slot_budgets:
            for norm_path, raw_path, value in _iter_slot_values(ctx):
                budget = slot_budgets.get(norm_path)
                if budget is None:
                    continue
                content_defects: list[ContentDefect] = _check_slot_overflow(
                    value, slot=raw_path, budget=budget, slide_index=slide_index,
                )
                for cd in content_defects:
                    budget_chars = budget.max_chars
                    over_by = max(0, len(value) - budget_chars)
                    defects.append(Defect(
                        slide_index=slide_index,
                        kind=DefectKind.SLOT_OVERFLOW,
                        severity=Severity.WARN,
                        message=cd.message,
                        meta={
                            "slot": cd.slot,
                            "budget_chars": budget_chars,
                            "over_by": over_by,
                        },
                    ))

    return defects
