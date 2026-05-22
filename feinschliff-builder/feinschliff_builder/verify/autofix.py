"""Mechanical fix suggestions and plan mutators for content-density defects.

This module does NOT call an LLM.  It operates in two modes:

1. **suggest_fix** (existing) — examines a single Defect record and returns a
   structured dict suggestion (which slot, what action, target character count)
   that an upstream caller can hand to an LLM in one shot.

2. **plan_fixes / apply_fixes** (new, B1) — translate a batch of Defect
   records into deterministic :class:`FixPatch` objects and apply them to a
   plan dict in place.  Only high-confidence mechanical classes are handled;
   anything ambiguous is left for LLM revise.

**Ordering contract for apply_fixes:**
- Patches against *different* slides are order-independent.
- Patches against *the same slot* are applied in arrival order; the second
  patch operates on the already-mutated content.  This is intentional: when
  two defects share a slot (e.g., two FILLER_WORD hits for different words),
  each patch should still read the current state.

**Idempotency:** ``apply_fixes(apply_fixes(plan, p), p) == apply_fixes(plan, p)``
for all patch lists ``p``.  Individual patch actions are idempotent (e.g.,
trimming already-trimmed text is a no-op; removing an absent word is a no-op).

**SLOT_OVERFLOW patch-selection contract:**
For a SLOT_OVERFLOW defect, ``plan_fixes`` emits at most ONE patch per defect:

- If the slot path is **scalar** (no ``[`` in the path) AND the original text
  exceeds ``budget * (1 + _SWAP_LARGER_THRESHOLD)`` AND a larger layout
  candidate is found, emit **only** ``swap_layout_larger``.  The larger layout
  was chosen precisely because the content cannot be shortened enough; emitting
  a ``shorten_slot`` on top would produce a shortened slot inside a layout that
  was selected to avoid shortening — semantically odd.
- If the slot path is **array-indexed** (contains ``[``, e.g. ``kpis[0].unit``),
  always emit ``shorten_slot`` regardless of overflow magnitude.  Swapping the
  layout would orphan the whole array into a layout that doesn't render it,
  causing silent data loss.  Shortening individual array-element strings always
  makes progress without structural loss.
- Otherwise (below the threshold, or no larger layout available), emit
  **only** ``shorten_slot`` as the fallback.

This ensures callers can inspect the patch list without worrying about
contradictory co-emissions for the same defect.
"""
from __future__ import annotations

import copy
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from feinschliff.defects import Defect, DefectKind


FixAction = Literal[
    "shorten_slot",         # SLOT_OVERFLOW, TEXT_OVERLAP — trim to budget
    "delete_word",          # FILLER_WORD — strip filler token
    "drop_bullet",          # BULLET_DUMP when >5 peers — drop weakest
    "swap_layout_smaller",  # EMPTY_PLACEHOLDER when slot_count > content keys
    "swap_layout_larger",   # SLOT_OVERFLOW when shorten_slot can't get under budget >20%
]

# Bullet-line prefixes that `drop_bullet` recognises.
_BULLET_PREFIXES = ("- ", "* ", "• ")

# When shorten can't get under budget by this fraction, also try swap_layout_larger.
_SWAP_LARGER_THRESHOLD = 0.20


@dataclass(frozen=True)
class FixPatch:
    slide_index: int            # 1-based (matches Defect.slide_index)
    action: FixAction
    slot: str | None            # None for layout-swap patches
    payload: dict[str, Any]     # action-specific data
    source_defect: DefectKind


# ─────────────────────────────────────────────────────────────────────────────
# suggest_fix — original dict API (kept for callers that want JSON form)
# ─────────────────────────────────────────────────────────────────────────────

def suggest_fix(d: Defect) -> dict[str, Any] | None:
    if d.kind is DefectKind.SLOT_OVERFLOW:
        slot = d.meta.get("slot")
        budget = d.meta.get("budget_chars")
        over_by = d.meta.get("over_by")
        if slot is None or budget is None or over_by is None:
            return None
        return {
            "slide_index": d.slide_index,
            "slot": slot,
            "action": "shorten",
            "target_chars": budget,
            "instruction": (
                f"Shorten slot '{slot}' by drop ~{over_by} chars to fit "
                f"the {budget}-char budget. Preserve the claim; trim "
                f"qualifiers and filler before facts."
            ),
        }
    if d.kind is DefectKind.TEXT_OVERLAP:
        a, b = d.meta.get("a_id"), d.meta.get("b_id")
        slot = b or a
        return {
            "slide_index": d.slide_index,
            "slot": slot,
            "action": "shorten",
            "target_chars": None,
            "instruction": (
                f"Slot '{slot}' overlaps '{a if slot == b else b}'. "
                f"Shorten '{slot}' until the overlap clears."
            ),
        }
    if d.kind is DefectKind.FILLER_WORD:
        word = d.meta.get("word")
        slot = d.meta.get("slot")
        if word is None or slot is None:
            return None
        return {
            "slide_index": d.slide_index,
            "slot": slot,
            "action": "delete_word",
            "word": word,
            "instruction": f"Remove the filler word '{word}' from slot '{slot}'.",
        }
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Slot-path navigator helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_slot_path(path: str) -> list[str | int]:
    """Tokenise a slot path like 'kpis[0].unit' into ['kpis', 0, 'unit'].

    Grammar: key( '[' digit+ ']' | '.' key )*
    Plain keys become str tokens; bracketed integers become int tokens.
    """
    tokens: list[str | int] = []
    # Split on '.' or '[N]', keeping the matched separators as part of the split
    remaining = path
    while remaining:
        # Consume a plain key (everything up to the next '.' or '[')
        dot_pos = remaining.find(".")
        bracket_pos = remaining.find("[")

        # Find next separator
        if dot_pos == -1 and bracket_pos == -1:
            # Terminal plain key
            tokens.append(remaining)
            break
        elif dot_pos == -1:
            sep_pos = bracket_pos
        elif bracket_pos == -1:
            sep_pos = dot_pos
        else:
            sep_pos = min(dot_pos, bracket_pos)

        if sep_pos > 0:
            tokens.append(remaining[:sep_pos])
            remaining = remaining[sep_pos:]
        elif sep_pos == 0:
            # We're at a separator
            if remaining[0] == ".":
                remaining = remaining[1:]  # skip the dot
            elif remaining[0] == "[":
                close = remaining.find("]")
                if close == -1:
                    # Malformed — treat the rest as a plain key
                    tokens.append(remaining)
                    break
                idx_str = remaining[1:close]
                try:
                    tokens.append(int(idx_str))
                except ValueError:
                    tokens.append(idx_str)
                remaining = remaining[close + 1:]
                # Skip a following '.' if present
                if remaining.startswith("."):
                    remaining = remaining[1:]
        else:
            # sep_pos == 0 shouldn't happen since we check > 0 / == 0 above;
            # guard against infinite loop
            break

    return tokens


def _get_slot_value(content: dict | list, path: str) -> str | None:
    """Navigate a slot path like 'kpis[0].unit' or 'body' into content.

    Returns the value at that path, or None if any segment is missing.
    """
    tokens = _parse_slot_path(path)
    node: object = content
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(node, list):
                return None
            if token >= len(node) or token < 0:
                return None
            node = node[token]
        else:
            if not isinstance(node, dict):
                return None
            if token not in node:
                return None
            node = node[token]
    if isinstance(node, str):
        return node
    return None


def _set_slot_value(content: dict | list, path: str, value: str) -> bool:
    """Set the value at the given path.

    Returns True on success, False if the path can't be navigated (any
    missing intermediate segment). Does NOT create intermediate keys/indices.
    """
    tokens = _parse_slot_path(path)
    if not tokens:
        return False
    node: object = content
    for token in tokens[:-1]:
        if isinstance(token, int):
            if not isinstance(node, list):
                return False
            if token >= len(node) or token < 0:
                return False
            node = node[token]
        else:
            if not isinstance(node, dict):
                return False
            if token not in node:
                return False
            node = node[token]
    # Apply final segment
    last = tokens[-1]
    if isinstance(last, int):
        if not isinstance(node, list):
            return False
        if last >= len(node) or last < 0:
            return False
        node[last] = value  # type: ignore[index]
        return True
    else:
        if not isinstance(node, dict):
            return False
        if last not in node:
            return False
        node[last] = value  # type: ignore[index]
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _shorten_to_budget(text: str, budget: int) -> str:
    """Trim *text* to at most *budget* chars.

    Strategy (in order):
    1. Cut at the last sentence boundary (``[.!?]`` followed by whitespace or
       end of candidate window) that lands at or before *budget*, preserving
       the terminal punctuation.
    2. Fall back to the last word boundary at or before *budget*.
    3. Hard-cut at *budget* (never mid-word when steps 1/2 found nothing).

    Idempotent: if ``len(text) <= budget`` the original string is returned.
    """
    if len(text) <= budget:
        return text

    candidate = text[:budget]

    # 1. Last sentence boundary within the candidate window.
    # Walk all [.!?] occurrences in the candidate and keep the last one that
    # is followed by a space or falls at the end of the candidate.
    last_sentence_end: int | None = None
    for m in re.finditer(r'[.!?]', candidate):
        end = m.end()
        if end >= len(candidate) or candidate[end] == " ":
            last_sentence_end = end
    if last_sentence_end is not None:
        trimmed = candidate[:last_sentence_end].rstrip()
        if trimmed:
            return trimmed

    # 2. Last word boundary.
    last_space = candidate.rfind(" ")
    if last_space > 0:
        return candidate[:last_space].rstrip()

    # 3. Hard cut.
    return candidate.rstrip()


def _count_bullets(text: str) -> list[str]:
    """Return lines in *text* that start with a recognised bullet prefix."""
    return [
        ln for ln in text.splitlines()
        if any(ln.startswith(pfx) for pfx in _BULLET_PREFIXES)
    ]


def _drop_weakest_bullets(text: str, keep: int = 5) -> str:
    """Drop the shortest (weakest) bullet lines until at most *keep* remain.

    Non-bullet lines (e.g. blank lines, section headers) are preserved as-is.
    Survivors retain their original relative order.
    """
    lines = text.splitlines()
    bullet_lines = [(i, ln) for i, ln in enumerate(lines)
                    if any(ln.startswith(pfx) for pfx in _BULLET_PREFIXES)]
    if len(bullet_lines) <= keep:
        return text

    # Sort by ascending length to find the weakest; drop the shortest ones.
    sorted_by_len = sorted(bullet_lines, key=lambda t: len(t[1]))
    to_drop = {idx for idx, _ in sorted_by_len[:len(bullet_lines) - keep]}

    surviving = [ln for i, ln in enumerate(lines) if i not in to_drop]
    # Strip trailing blank lines that were between dropped bullets.
    while surviving and not surviving[-1].strip():
        surviving.pop()
    return "\n".join(surviving)


def _get_slide_content(plan: dict, slide_index: int) -> dict:
    """Return the content dict for the 1-based *slide_index*."""
    return plan["slides"][slide_index - 1].get("content") or {}


def _set_slot(plan: dict, slide_index: int, slot: str, value: str) -> None:
    """Write *value* into plan slides[slide_index-1].content[slot]."""
    plan["slides"][slide_index - 1].setdefault("content", {})[slot] = value


def _get_slot(plan: dict, slide_index: int, slot: str) -> str | None:
    """Read plan slides[slide_index-1].content[slot]; return None if absent."""
    return _get_slide_content(plan, slide_index).get(slot)


def _find_smaller_layout(
    current_layout_rel: str,
    slide: dict,
    brand_dir: Path,
    layout_history: list[str] | None = None,
) -> str | None:
    """Use pick_layout to find a layout with fewer required slots than *current_layout_rel*.

    Returns a layout path string (same format as ``slide["layout"]``) or None.

    *layout_history* — optional list of recently-used layout IDs (most recent
    last). When provided it is passed to ``pick_layout`` so the variety penalty
    fires and multiple simultaneous swap patches don't all converge on the same
    candidate.
    """
    try:
        from feinschliff.layout_picker import pick_layout
    except ImportError:
        return None

    meta = slide.get("_meta") or {}
    role = meta.get("role") or "content-columns"
    concept_count = meta.get("concept_count")

    # Ask for top-5 candidates with the same role but potentially fewer slots.
    # We want a layout whose name suggests simplicity (e.g. action-title, end, etc.)
    candidates = pick_layout(
        role=role,
        concept_count=max(1, (concept_count or 2) - 1),
        top_k=5,
        layout_history=layout_history,
    )
    if not candidates:
        return None

    try:
        from feinschliff.layout_discovery import find_layout
    except ImportError:
        return None

    current_name = _layout_name(current_layout_rel)
    for c in candidates:
        layout_id = c["layout"]
        if layout_id == current_name:
            continue  # same as current
        if find_layout(layout_id) is not None:
            return f"layouts/{layout_id}.slide.dsl"
    return None


def _find_larger_layout(
    current_layout_rel: str,
    slide: dict,
    brand_dir: Path,
    layout_history: list[str] | None = None,
) -> str | None:
    """Use pick_layout to find a layout with more body/bullet room.

    Returns a layout path string or None.

    *layout_history* — optional list of recently-used layout IDs (most recent
    last). When provided it is passed to ``pick_layout`` so the variety penalty
    fires and multiple simultaneous swap patches don't all converge on the same
    candidate.
    """
    try:
        from feinschliff.layout_picker import pick_layout
    except ImportError:
        return None

    meta = slide.get("_meta") or {}
    role = meta.get("role") or "content-columns"
    concept_count = meta.get("concept_count")

    candidates = pick_layout(
        role=role,
        concept_count=min(8, (concept_count or 2) + 1),
        top_k=5,
        layout_history=layout_history,
    )
    if not candidates:
        return None

    try:
        from feinschliff.layout_discovery import find_layout
    except ImportError:
        return None

    current_name = _layout_name(current_layout_rel)
    for c in candidates:
        layout_id = c["layout"]
        if layout_id == current_name:
            continue
        if find_layout(layout_id) is not None:
            return f"layouts/{layout_id}.slide.dsl"
    return None


def _layout_name(layout_rel: str) -> str:
    """Extract the bare layout name from a relative path like 'layouts/foo.slide.dsl'."""
    name = Path(layout_rel).name
    if name.endswith(".slide.dsl"):
        name = name[: -len(".slide.dsl")]
    return name


# ─────────────────────────────────────────────────────────────────────────────
# plan_fixes — batch defect → patch translation
# ─────────────────────────────────────────────────────────────────────────────

def _defect_slide_index(d: object) -> int:
    """Extract slide_index from either a legacy or new-style Defect."""
    # Legacy feinschliff.defects.Defect has .slide_index directly.
    si = getattr(d, "slide_index", None)
    if si is not None:
        return int(si)
    # New feinschliff.diagnostics.Defect stores it in .extra["slide_index"].
    extra = getattr(d, "extra", None) or {}
    return int(extra.get("slide_index", 0))


def _defect_meta(d: object) -> dict:
    """Return the metadata dict from either a legacy or new-style Defect."""
    # Legacy: .meta; new: .extra
    meta = getattr(d, "meta", None)
    if meta is not None:
        return meta
    return getattr(d, "extra", None) or {}


def plan_fixes(
    defects,
    plan: dict,
    brand_dir: Path,
) -> list[FixPatch]:
    """Translate *defects* into deterministic patches.

    Accepts either a list of legacy ``feinschliff.defects.Defect`` objects or a
    ``DiagnosticBag`` (``feinschliff.diagnostics``).  Both are supported via duck-
    typing so callers can migrate to ``validate()`` without also updating
    the downstream ``plan_fixes`` call.

    Returns only patches we are confident in — anything ambiguous (e.g.
    CLAIM_TITLE, TITLE_BODY_COHERENCE) is skipped and left for LLM revise.

    The order of the returned list mirrors the order of *defects* for
    same-slide same-slot patches; patches for different slides are
    interleaved in defect-arrival order.
    """
    patches: list[FixPatch] = []
    slides = plan.get("slides") or []

    # Accumulate layout IDs picked for swap patches within this batch so that
    # pick_layout's variety penalty fires for each successive swap, preventing
    # all patches in the same cycle from converging on the same candidate.
    swap_history: list[str] = []

    for d in defects:
        _sidx = _defect_slide_index(d)
        _meta = _defect_meta(d)
        slide_0 = _sidx - 1  # 0-based index into slides[]
        if not (0 <= slide_0 < len(slides)):
            continue
        slide = slides[slide_0]

        # ── SLOT_OVERFLOW ────────────────────────────────────────────────────
        if d.kind == DefectKind.SLOT_OVERFLOW:
            slot = _meta.get("slot")
            budget = _meta.get("budget_chars")
            if slot is None or budget is None:
                continue  # not enough info

            current_text = _get_slot_value(slide.get("content") or {}, slot) or ""

            # Array-indexed slots (e.g. 'kpis[0].unit') must never trigger a
            # layout swap: the new layout won't have the same array structure,
            # so the array data would be silently orphaned and never rendered.
            # Shortening always makes progress on individual array-element
            # strings; the layout-swap path cannot preserve them.
            is_array_slot = "[" in slot

            # Decision: try swap_layout_larger first when the overflow is
            # extreme (>20% of budget) AND the slot is scalar (not
            # array-indexed). If a candidate layout exists, emit ONLY the
            # swap patch — the larger layout was chosen precisely because
            # shortening alone is insufficient. If no candidate is found, or
            # the slot is array-indexed, fall back to shorten_slot. Below the
            # threshold, always use shorten_slot. Never emit both for the same
            # defect.
            swap_emitted = False
            if not is_array_slot and len(current_text) > budget * (1 + _SWAP_LARGER_THRESHOLD):
                current_layout = slide.get("layout", "")
                larger_rel = _find_larger_layout(
                    current_layout, slide, brand_dir, layout_history=swap_history
                )
                if larger_rel:
                    swap_history.append(_layout_name(larger_rel))
                    patches.append(FixPatch(
                        slide_index=_sidx,
                        action="swap_layout_larger",
                        slot=None,
                        payload={"new_layout": larger_rel},
                        source_defect=DefectKind.SLOT_OVERFLOW,
                    ))
                    swap_emitted = True

            if not swap_emitted:
                trimmed = _shorten_to_budget(current_text, budget)
                patches.append(FixPatch(
                    slide_index=_sidx,
                    action="shorten_slot",
                    slot=slot,
                    payload={"budget_chars": budget, "trimmed_to": len(trimmed)},
                    source_defect=DefectKind.SLOT_OVERFLOW,
                ))

        # ── TEXT_OVERLAP ─────────────────────────────────────────────────────
        elif d.kind == DefectKind.TEXT_OVERLAP:
            a_id = _meta.get("a_id")
            b_id = _meta.get("b_id")
            slot = b_id or a_id  # prefer b (the one that moves / is shorter)
            if not slot:
                continue

            current_text = _get_slot_value(slide.get("content") or {}, slot) or ""
            if not current_text:
                continue

            # When no budget_chars is present, shorten by 75% of current length.
            budget = _meta.get("budget_chars")
            if budget is None:
                budget = max(1, int(len(current_text) * 0.75))

            patches.append(FixPatch(
                slide_index=_sidx,
                action="shorten_slot",
                slot=slot,
                payload={"budget_chars": budget},
                source_defect=DefectKind.TEXT_OVERLAP,
            ))

        # ── FILLER_WORD ───────────────────────────────────────────────────────
        elif d.kind == DefectKind.FILLER_WORD:
            word = _meta.get("word")
            slot = _meta.get("slot")
            if not word or not slot:
                continue

            patches.append(FixPatch(
                slide_index=_sidx,
                action="delete_word",
                slot=slot,
                payload={"word": word},
                source_defect=DefectKind.FILLER_WORD,
            ))

        # ── BULLET_DUMP ───────────────────────────────────────────────────────
        elif d.kind == DefectKind.BULLET_DUMP:
            slot = _meta.get("slot")
            if not slot:
                # Try common body slot names
                content = slide.get("content") or {}
                for candidate_slot in ("body", "supporting_body", "bullets", "content"):
                    if candidate_slot in content:
                        slot = candidate_slot
                        break
            if not slot:
                continue

            current_text = _get_slot_value(slide.get("content") or {}, slot) or ""
            bullet_count = len(_count_bullets(current_text))
            if bullet_count <= 5:
                # Not enough bullets to warrant dropping — skip
                continue

            patches.append(FixPatch(
                slide_index=_sidx,
                action="drop_bullet",
                slot=slot,
                payload={"keep": 5},
                source_defect=DefectKind.BULLET_DUMP,
            ))

        # ── EMPTY_PLACEHOLDER ─────────────────────────────────────────────────
        elif d.kind == DefectKind.EMPTY_PLACEHOLDER:
            current_layout = slide.get("layout", "")
            smaller_rel = _find_smaller_layout(
                current_layout, slide, brand_dir, layout_history=swap_history
            )
            if smaller_rel:
                swap_history.append(_layout_name(smaller_rel))
                patches.append(FixPatch(
                    slide_index=_sidx,
                    action="swap_layout_smaller",
                    slot=None,
                    payload={"new_layout": smaller_rel},
                    source_defect=DefectKind.EMPTY_PLACEHOLDER,
                ))
            # If no smaller layout found, return no patch — the orchestrator
            # will see EMPTY_PLACEHOLDER unresolved.

        # ── All other defect classes: no patch in v1 ─────────────────────────
        # (CLAIM_TITLE, TITLE_BODY_COHERENCE, LAYOUT_CONCEPT_MISMATCH,
        #  OUT_OF_BOUNDS, chrome defects, etc.)

    return patches


# ─────────────────────────────────────────────────────────────────────────────
# apply_fixes — mutate plan dict according to patches
# ─────────────────────────────────────────────────────────────────────────────

def apply_fixes(plan: dict, patches: list[FixPatch]) -> dict:
    """Apply *patches* in order to a deep-copy of *plan*.  Returns the mutated plan.

    Idempotent: applying the same patch list twice returns the same result as
    applying it once.  Failure mode: if a patch can't be applied (e.g. slot
    missing), log to stderr and skip that patch, don't crash.
    """
    mutated = copy.deepcopy(plan)
    slides = mutated.get("slides") or []

    for patch in patches:
        slide_0 = patch.slide_index - 1
        if not (0 <= slide_0 < len(slides)):
            print(
                f"apply_fixes: patch slide_index={patch.slide_index} out of range "
                f"(plan has {len(slides)} slide(s)) — skipped",
                file=sys.stderr,
            )
            continue

        slide = slides[slide_0]

        try:
            if patch.action == "shorten_slot":
                _apply_shorten_slot(slide, patch)

            elif patch.action == "delete_word":
                _apply_delete_word(slide, patch)

            elif patch.action == "drop_bullet":
                _apply_drop_bullet(slide, patch)

            elif patch.action in ("swap_layout_smaller", "swap_layout_larger"):
                _apply_swap_layout(slide, patch)

            else:
                print(
                    f"apply_fixes: unknown action {patch.action!r} — skipped",
                    file=sys.stderr,
                )
        except Exception as exc:  # noqa: BLE001
            print(
                f"apply_fixes: slide {patch.slide_index}, action={patch.action!r}, "
                f"slot={patch.slot!r}: {exc} — skipped",
                file=sys.stderr,
            )

    return mutated


def _apply_shorten_slot(slide: dict, patch: FixPatch) -> None:
    slot = patch.slot
    if slot is None:
        return
    content = slide.setdefault("content", {})
    current = _get_slot_value(content, slot)
    if current is None:
        print(
            f"apply_fixes: shorten_slot: slot path {slot!r} not found in content — skipped",
            file=sys.stderr,
        )
        return
    if not isinstance(current, str):
        return
    budget = patch.payload.get("budget_chars")
    if budget is None:
        return
    shortened = _shorten_to_budget(current, budget)
    _set_slot_value(content, slot, shortened)


def _apply_delete_word(slide: dict, patch: FixPatch) -> None:
    slot = patch.slot
    word = patch.payload.get("word")
    if not slot or not word:
        return
    content = slide.setdefault("content", {})
    current = _get_slot_value(content, slot)
    if current is None or not isinstance(current, str):
        return
    # Case-insensitive word-boundary removal.
    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
    result = pattern.sub("", current)
    # Collapse multiple spaces that removal may leave behind.
    result = re.sub(r'  +', ' ', result).strip()
    _set_slot_value(content, slot, result)


def _apply_drop_bullet(slide: dict, patch: FixPatch) -> None:
    slot = patch.slot
    if slot is None:
        return
    content = slide.setdefault("content", {})
    current = _get_slot_value(content, slot)
    if current is None or not isinstance(current, str):
        return
    keep = patch.payload.get("keep", 5)
    _set_slot_value(content, slot, _drop_weakest_bullets(current, keep=keep))


def _apply_swap_layout(slide: dict, patch: FixPatch) -> None:
    new_layout = patch.payload.get("new_layout")
    if not new_layout:
        return
    slide["layout"] = new_layout


# ─────────────────────────────────────────────────────────────────────────────
# diff_summary — human-readable changelog
# ─────────────────────────────────────────────────────────────────────────────

def diff_summary(before: dict, after: dict) -> str:
    """Return a markdown bullet list of what changed between *before* and *after*.

    Compares only the slides' content and layout fields.  Returns an empty
    string when the two dicts are identical.
    """
    before_slides = before.get("slides") or []
    after_slides = after.get("slides") or []
    lines: list[str] = []

    for i, (b_slide, a_slide) in enumerate(zip(before_slides, after_slides), start=1):
        b_content = b_slide.get("content") or {}
        a_content = a_slide.get("content") or {}
        b_layout = b_slide.get("layout", "")
        a_layout = a_slide.get("layout", "")

        if b_layout != a_layout:
            lines.append(
                f"- slide {i}: layout changed from `{b_layout}` → `{a_layout}`"
            )

        all_keys = set(b_content) | set(a_content)
        for slot in sorted(all_keys):
            bv = b_content.get(slot, "")
            av = a_content.get(slot, "")
            if bv != av:
                blen = len(bv) if isinstance(bv, str) else "?"
                alen = len(av) if isinstance(av, str) else "?"
                lines.append(
                    f"- slide {i}, slot `{slot}`: {blen} → {alen} chars"
                )

    return "\n".join(lines)
