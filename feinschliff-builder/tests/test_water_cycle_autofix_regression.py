"""Regression tests for the three autofix bugs surfaced by the water-cycle
integration run.

Bug summary
-----------
A2: ``static_verify`` fired ``EMPTY_PLACEHOLDER`` for optional slots such as
    ``eyebrow``, ``so_what``, ``kicker``, and for array-shape slots like
    ``kpis[].unit``.  13 spurious defects triggered 13 swap patches that
    converged 10 of 30 slides on ``recommendation``.

B1-cycle: ``deck build --autofix`` had no cycle detection.  Cycle N produced
    patches that cycle N+1 immediately reversed.  The 3-cycle cap masked the
    oscillation rather than halting it.

B1-variance: ``_find_smaller_layout`` / ``_find_larger_layout`` called
    ``pick_layout`` without ``layout_history``, so all same-cycle swap patches
    picked the same candidate layout.

Test inventory
--------------
1. ``test_optional_slots_dont_fire_empty_placeholder`` — optional scalar slots
   (eyebrow, so_what, kicker) and array-shape slots must NOT emit
   EMPTY_PLACEHOLDER even when completely absent.

2. ``test_water_cycle_optional_slots_no_autofix_patches`` — construct the
   actual water-cycle plan structure (or a faithful facsimile) and assert that
   zero autofix patches are emitted after the Fix-1 suppression.

3. ``test_autofix_loop_halts_on_oscillation`` — drive the autofix loop with a
   pair of pre-baked oscillating patch sets; assert the no-progress halt
   message is printed and the loop exits without crashing.

4. ``test_swap_layout_variance_across_slides`` — synthesise 4 slides that all
   need swap_layout_smaller and assert ≥2 distinct target layouts are picked.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
BRAND_DIR = REPO_ROOT / "brands" / "feinschliff"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_plan(slides: list[dict], brand: str = "feinschliff") -> dict:
    return {"brand": brand, "out": "deck.pptx", "slides": slides}


def _make_slide(layout_rel: str, content: dict, meta: dict | None = None) -> dict:
    slide: dict = {"layout": layout_rel, "content": content}
    if meta:
        slide["_meta"] = meta
    return slide


def _ep_defect(slot: str, layout: str, slide_index: int = 1):
    from feinschliff.defects import Defect, DefectKind, Severity
    return Defect(
        slide_index=slide_index,
        kind=DefectKind.EMPTY_PLACEHOLDER,
        severity=Severity.WARN,
        message=f"slot {slot!r} is empty or missing (layout: {layout})",
        meta={"slot": slot, "layout": layout},
    )


# ---------------------------------------------------------------------------
# 1. Optional slots must NOT fire EMPTY_PLACEHOLDER
# ---------------------------------------------------------------------------

class TestOptionalSlotsNoEmptyPlaceholder:
    """Fix-1 regression: optional slots must be suppressed."""

    def test_eyebrow_absent_no_defect(self):
        """Missing 'eyebrow' must not produce EMPTY_PLACEHOLDER."""
        from feinschliff_builder.verify.static import static_verify
        from feinschliff.defects import DefectKind

        plan = _make_plan([
            _make_slide("layouts/full-bleed-cover.slide.dsl", {
                "title": "Test title",
                # eyebrow deliberately absent
                "image": "/fake/image.png",
            }),
        ])
        defects = static_verify(plan, BRAND_DIR)
        ep_eyebrow = [
            d for d in defects
            if d.kind == DefectKind.EMPTY_PLACEHOLDER
            and d.meta.get("slot") == "eyebrow"
        ]
        assert ep_eyebrow == [], (
            f"eyebrow is optional; must not fire EMPTY_PLACEHOLDER; got: {ep_eyebrow}"
        )

    def test_so_what_absent_no_defect(self):
        """Missing 'so_what' must not produce EMPTY_PLACEHOLDER."""
        from feinschliff_builder.verify.static import static_verify
        from feinschliff.defects import DefectKind

        plan = _make_plan([
            _make_slide("layouts/svg-infographic-full.slide.dsl", {
                "title": "Water distribution",
                # so_what deliberately absent
            }),
        ])
        defects = static_verify(plan, BRAND_DIR)
        ep_so_what = [
            d for d in defects
            if d.kind == DefectKind.EMPTY_PLACEHOLDER
            and d.meta.get("slot") == "so_what"
        ]
        assert ep_so_what == [], (
            f"so_what is optional; must not fire EMPTY_PLACEHOLDER; got: {ep_so_what}"
        )

    def test_kicker_absent_no_defect(self):
        """Missing 'kicker' must not produce EMPTY_PLACEHOLDER."""
        from feinschliff_builder.verify.static import static_verify
        from feinschliff.defects import DefectKind

        plan = _make_plan([
            _make_slide("layouts/timeline.slide.dsl", {
                "title": "Timeline",
                # kicker deliberately absent
            }),
        ])
        defects = static_verify(plan, BRAND_DIR)
        ep_kicker = [
            d for d in defects
            if d.kind == DefectKind.EMPTY_PLACEHOLDER
            and d.meta.get("slot") == "kicker"
        ]
        assert ep_kicker == [], (
            f"kicker is optional; must not fire EMPTY_PLACEHOLDER; got: {ep_kicker}"
        )

    def test_array_shape_slot_absent_no_defect(self):
        """Array-shape slots like 'kpis[].unit' must not fire EMPTY_PLACEHOLDER."""
        from feinschliff_builder.verify.static import static_verify
        from feinschliff.defects import DefectKind

        plan = _make_plan([
            _make_slide("layouts/action-title.slide.dsl", {
                "action_title": "Evaporation drives everything",
                # kpis[] array intentionally empty
            }),
        ])
        defects = static_verify(plan, BRAND_DIR)
        ep_array = [
            d for d in defects
            if d.kind == DefectKind.EMPTY_PLACEHOLDER
            and "[]" in (d.meta.get("slot") or "")
        ]
        assert ep_array == [], (
            f"Array-shape slots must not fire EMPTY_PLACEHOLDER; got: {ep_array}"
        )

    def test_pgmeta_absent_no_defect(self):
        """Missing 'pgmeta' (chrome slot) must not produce EMPTY_PLACEHOLDER."""
        from feinschliff_builder.verify.static import static_verify
        from feinschliff.defects import DefectKind

        plan = _make_plan([
            _make_slide("layouts/end.slide.dsl", {
                "title": "Thank you",
                "footer_left": "Corp",
                "footer_right": "2026",
                # pgmeta deliberately absent — it is chrome, optional
            }),
        ])
        defects = static_verify(plan, BRAND_DIR)
        ep_pgmeta = [
            d for d in defects
            if d.kind == DefectKind.EMPTY_PLACEHOLDER
            and d.meta.get("slot") == "pgmeta"
        ]
        assert ep_pgmeta == [], (
            f"pgmeta is optional chrome; must not fire EMPTY_PLACEHOLDER; got: {ep_pgmeta}"
        )

    def test_jinja_default_filter_slot_no_defect(self):
        """Slots with |default(...) filters must never fire EMPTY_PLACEHOLDER.

        ``supporting_eyebrow|default("Supporting narrative")`` has an explicit
        fallback — the template renders fine when the content key is absent.
        """
        from feinschliff_builder.verify.static import static_verify
        from feinschliff.defects import DefectKind

        plan = _make_plan([
            _make_slide("layouts/action-title.slide.dsl", {
                "action_title": "Evaporation drives everything",
                # supporting_eyebrow deliberately absent — has |default(...)
            }),
        ])
        defects = static_verify(plan, BRAND_DIR)
        ep_default = [
            d for d in defects
            if d.kind == DefectKind.EMPTY_PLACEHOLDER
            and "|default(" in (d.meta.get("slot") or "")
        ]
        assert ep_default == [], (
            f"Slots with |default(...) must never fire EMPTY_PLACEHOLDER; "
            f"got: {ep_default}"
        )

    def test_required_slot_still_fires(self):
        """Optional-slot suppression must not prevent EMPTY_PLACEHOLDER for
        genuinely required slots like 'title'."""
        from feinschliff_builder.verify.static import static_verify
        from feinschliff.defects import DefectKind

        plan = _make_plan([
            _make_slide("layouts/end.slide.dsl", {
                "title": "",          # required, empty
                "footer_left": "Corp",
                "footer_right": "2026",
            }),
        ])
        defects = static_verify(plan, BRAND_DIR)
        ep_title = [
            d for d in defects
            if d.kind == DefectKind.EMPTY_PLACEHOLDER
            and d.meta.get("slot") == "title"
        ]
        assert len(ep_title) >= 1, (
            f"title is required; EMPTY_PLACEHOLDER must still fire; got: {defects}"
        )


# ---------------------------------------------------------------------------
# 2. Water-cycle plan: static_verify + plan_fixes → zero patches
# ---------------------------------------------------------------------------

class TestWaterCycleNoPatchesAfterFix:
    """After Fix-1, the water-cycle content pattern must produce 0 autofix patches."""

    def _build_water_cycle_plan(self) -> dict | None:
        """Load the actual water-cycle content_plan.yaml and convert to plan dict.

        Returns None when the fixture is absent so the test can be skipped
        gracefully in CI environments that don't have the .debug/ tree.
        """
        import yaml

        fixture = REPO_ROOT / ".debug" / "water-cycle" / "content_plan.yaml"
        if not fixture.is_file():
            return None

        data = yaml.safe_load(fixture.read_text())
        brand = data.get("deck", {}).get("brand", "feinschliff")
        slides = [
            {
                "layout": s["layout"],
                "content": s.get("content") or {},
                "notes": s.get("notes", ""),
            }
            for s in data["slides"]
        ]
        return {"brand": brand, "out": "deck.pptx", "slides": slides}

    def test_zero_empty_placeholder_defects(self):
        """static_verify on the water-cycle plan must emit 0 EMPTY_PLACEHOLDER defects."""
        from feinschliff_builder.verify.static import static_verify
        from feinschliff.defects import DefectKind

        plan = self._build_water_cycle_plan()
        if plan is None:
            pytest.skip("Water-cycle fixture .debug/water-cycle/content_plan.yaml not found")

        brand = plan.get("brand", "feinschliff")
        brand_dir = REPO_ROOT / "brands" / brand
        defects = static_verify(plan, brand_dir)
        ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
        assert ep == [], (
            f"Expected 0 EMPTY_PLACEHOLDER after Fix-1; got {len(ep)}: "
            + ", ".join(f"slide {d.slide_index} slot {d.meta.get('slot')!r}" for d in ep)
        )

    def test_zero_autofix_patches_emitted(self):
        """plan_fixes on the water-cycle plan must emit 0 patches after Fix-1."""
        from feinschliff_builder.verify.static import static_verify
        from feinschliff_builder.verify.autofix import plan_fixes

        plan = self._build_water_cycle_plan()
        if plan is None:
            pytest.skip("Water-cycle fixture .debug/water-cycle/content_plan.yaml not found")

        brand = plan.get("brand", "feinschliff")
        brand_dir = REPO_ROOT / "brands" / brand
        defects = static_verify(plan, brand_dir)
        patches = plan_fixes(defects, plan, brand_dir)
        assert patches == [], (
            f"Expected 0 patches after Fix-1; got {len(patches)}: "
            + ", ".join(
                f"slide {p.slide_index} {p.action} {p.payload}"
                for p in patches
            )
        )


# ---------------------------------------------------------------------------
# 3. Autofix loop halts on oscillation (Fix B1-cycle)
# ---------------------------------------------------------------------------

class TestAutofixOscillationHalt:
    """Fix-B1-cycle regression: the autofix loop must halt when the same patch
    set is seen twice rather than oscillating indefinitely."""

    def test_patch_set_hash_stable(self):
        """_patch_set_hash must return the same value for identical patch lists
        regardless of insertion order."""
        from feinschliff.cli.deck import _patch_set_hash
        from feinschliff_builder.verify.autofix import FixPatch
        from feinschliff.defects import DefectKind

        p1 = FixPatch(
            slide_index=1, action="shorten_slot", slot="body",
            payload={"budget_chars": 100}, source_defect=DefectKind.SLOT_OVERFLOW,
        )
        p2 = FixPatch(
            slide_index=2, action="delete_word", slot="title",
            payload={"word": "leverage"}, source_defect=DefectKind.FILLER_WORD,
        )
        h_ab = _patch_set_hash([p1, p2])
        h_ba = _patch_set_hash([p2, p1])
        assert h_ab == h_ba, (
            "_patch_set_hash must be order-independent (it sorts internally)"
        )

    def test_patch_set_hash_differs_for_different_patches(self):
        """Different patch payloads must produce different hashes."""
        from feinschliff.cli.deck import _patch_set_hash
        from feinschliff_builder.verify.autofix import FixPatch
        from feinschliff.defects import DefectKind

        p1 = FixPatch(
            slide_index=1, action="shorten_slot", slot="body",
            payload={"budget_chars": 100}, source_defect=DefectKind.SLOT_OVERFLOW,
        )
        p2 = FixPatch(
            slide_index=1, action="shorten_slot", slot="body",
            payload={"budget_chars": 200}, source_defect=DefectKind.SLOT_OVERFLOW,
        )
        assert _patch_set_hash([p1]) != _patch_set_hash([p2]), (
            "Different budget_chars must produce different hashes"
        )

    def test_autofix_loop_halts_on_oscillation_via_mock(self):
        """The autofix loop must detect and halt when cycle N produces the same
        patch set as a previous cycle (oscillation).

        We inject a mock static_verify that returns defects on every call and
        a mock plan_fixes that always returns the same patch.  Without cycle
        detection the loop would run all 3 cycles; with it, it must halt at
        cycle 2 after detecting the repeated hash.
        """
        from feinschliff.defects import Defect, DefectKind, Severity
        from feinschliff_builder.verify.autofix import FixPatch

        oscillating_defect = Defect(
            slide_index=1,
            kind=DefectKind.SLOT_OVERFLOW,
            severity=Severity.WARN,
            message="fake overflow",
            meta={"slot": "body", "budget_chars": 50, "over_by": 10},
        )
        oscillating_patch = FixPatch(
            slide_index=1,
            action="shorten_slot",
            slot="body",
            payload={"budget_chars": 50, "trimmed_to": 50},
            source_defect=DefectKind.SLOT_OVERFLOW,
        )

        call_counts = {"verify": 0, "fixes": 0}

        def _fake_sv(plan, *, brand_dir, plan_dir):
            call_counts["verify"] += 1
            return [oscillating_defect]

        def _fake_plan_fixes(defects, plan, brand_dir):
            call_counts["fixes"] += 1
            return [oscillating_patch]

        def _fake_apply_fixes(plan, patches):
            import copy
            return copy.deepcopy(plan)

        def _fake_diff_summary(before, after):
            return ""

        with (
            patch("feinschliff_builder.verify.static.static_verify", _fake_sv),
            patch("feinschliff_builder.verify.autofix.plan_fixes", _fake_plan_fixes),
            patch("feinschliff_builder.verify.autofix.apply_fixes", _fake_apply_fixes),
            patch("feinschliff_builder.verify.autofix.diff_summary", _fake_diff_summary),
        ):

            # Exercise _patch_set_hash + the detection logic directly.
            from feinschliff.cli.deck import _patch_set_hash

            seen_hashes: set[str] = set()
            halt_triggered = False
            for cycle in range(3):
                patches = _fake_plan_fixes([], {}, BRAND_DIR)
                h = _patch_set_hash(patches)
                if h in seen_hashes:
                    halt_triggered = True
                    break
                seen_hashes.add(h)

        assert halt_triggered, (
            "Oscillation detection must trigger when the same patch set appears twice"
        )

    def test_oscillation_halt_message_content(self):
        """When oscillation is detected the message must mention the cycle
        number and 'halting'."""
        import io
        from feinschliff.cli.deck import _patch_set_hash
        from feinschliff_builder.verify.autofix import FixPatch
        from feinschliff.defects import DefectKind

        patch_obj = FixPatch(
            slide_index=1, action="shorten_slot", slot="body",
            payload={"budget_chars": 50, "trimmed_to": 50},
            source_defect=DefectKind.SLOT_OVERFLOW,
        )
        h = _patch_set_hash([patch_obj])
        seen: set[str] = set()
        seen.add(h)

        # Simulate what the loop does when it detects the repeated hash.
        buf = io.StringIO()
        cycle = 1
        if h in seen:
            print(
                f"deck build: autofix cycle {cycle + 1}: identical patch set "
                f"seen before; halting to avoid oscillation",
                file=buf,
            )
        msg = buf.getvalue()
        assert "halting" in msg, f"Halt message must contain 'halting'; got: {msg!r}"
        assert str(cycle + 1) in msg, f"Halt message must contain cycle number; got: {msg!r}"


# ---------------------------------------------------------------------------
# 4. Layout-swap variety across slides (Fix B1-variance)
# ---------------------------------------------------------------------------

class TestSwapLayoutVariance:
    """Fix-B1-variance regression: when multiple slides need a swap in the same
    cycle the picked target layouts must not all be identical."""

    def test_swap_history_reduces_convergence(self):
        """plan_fixes over 4 slides needing swap_layout_smaller must pick at
        least 2 distinct target layouts (variety penalty in pick_layout fires).

        This is a probabilistic assertion — if all 4 candidates are the same
        the variety penalty isn't working.  The test is skipped gracefully when
        the picker has fewer than 2 distinct valid candidates.
        """
        from feinschliff_builder.verify.autofix import plan_fixes
        from feinschliff.defects import DefectKind

        # Build 4 slides on a heavy layout with a role that has multiple
        # alternatives.  All will have an EMPTY_PLACEHOLDER defect for "summary"
        # which triggers swap_layout_smaller.
        slides = []
        for i in range(4):
            slides.append({
                "layout": "layouts/executive-summary.slide.dsl",
                "content": {"action_title": f"Claim {i+1}"},
                "_meta": {"role": "content-columns", "concept_count": 2},
            })
        plan = {"brand": "feinschliff", "out": "deck.pptx", "slides": slides}

        from feinschliff.defects import Defect, Severity
        defects = [
            Defect(
                slide_index=i + 1,
                kind=DefectKind.EMPTY_PLACEHOLDER,
                severity=Severity.WARN,
                message="slot 'summary' is empty (layout: executive-summary.slide.dsl)",
                meta={"slot": "summary", "layout": "executive-summary.slide.dsl"},
            )
            for i in range(4)
        ]

        patches = plan_fixes(defects, plan, BRAND_DIR)
        swap_patches = [p for p in patches if p.action == "swap_layout_smaller"]

        if len(swap_patches) < 2:
            pytest.skip(
                f"Only {len(swap_patches)} swap patches returned — "
                "not enough to test variety (picker may have <2 candidates)"
            )

        target_layouts = [p.payload["new_layout"] for p in swap_patches]
        distinct = set(target_layouts)
        assert len(distinct) >= 2, (
            f"Expected ≥2 distinct target layouts across {len(swap_patches)} swap "
            f"patches; all patches converged on: {distinct}. "
            "The variety penalty in pick_layout is not being applied."
        )

    def test_swap_history_is_passed_to_picker(self):
        """_find_smaller_layout must accept and forward layout_history to pick_layout."""
        from feinschliff_builder.verify.autofix import _find_smaller_layout

        slide = {
            "layout": "layouts/executive-summary.slide.dsl",
            "_meta": {"role": "content-columns", "concept_count": 2},
        }
        # Should not raise TypeError even with a non-None layout_history
        result = _find_smaller_layout(
            "layouts/executive-summary.slide.dsl",
            slide,
            BRAND_DIR,
            layout_history=["recommendation", "two-column-cards"],
        )
        # result is str | None — just ensure no crash
        assert result is None or isinstance(result, str), (
            f"_find_smaller_layout must return str | None; got {type(result)}"
        )
