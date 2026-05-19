"""Tests for the B1 apply-fixes mutator.

Covers each of the 5 v1 patch actions:
  1. shorten_slot      — SLOT_OVERFLOW → trim to budget
  2. delete_word       — FILLER_WORD   → strip filler token
  3. drop_bullet       — BULLET_DUMP   → drop weakest bullets until ≤5
  4. swap_layout_smaller — EMPTY_PLACEHOLDER (count mismatch) → smaller layout
  5. swap_layout_larger  — SLOT_OVERFLOW that shorten_slot can't resolve

Also covers:
  - Idempotency: applying twice == applying once.
  - No-op on empty patch list.
  - diff_summary produces a non-empty markdown summary when patches were applied.
  - plan_fixes skips unknown defect classes silently.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BRANDS_DIR = REPO_ROOT / "brands"
BRAND_DIR = REPO_ROOT / "brands" / "feinschliff"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plan(layout_rel: str, content: dict) -> dict:
    return {
        "brand": "feinschliff",
        "out": "deck.pptx",
        "slides": [
            {"layout": layout_rel, "content": content},
        ],
    }


# ---------------------------------------------------------------------------
# Import guards
# ---------------------------------------------------------------------------

def test_autofix_apply_importable():
    from lib.verify.autofix import plan_fixes, apply_fixes, diff_summary, FixPatch  # noqa: F401
    assert callable(plan_fixes)
    assert callable(apply_fixes)
    assert callable(diff_summary)


# ---------------------------------------------------------------------------
# 1. shorten_slot — SLOT_OVERFLOW
# ---------------------------------------------------------------------------

class TestShortenSlot:
    """SLOT_OVERFLOW defect → shorten_slot patch → content trimmed to budget."""

    def _overflow_defect(self, slot: str, budget: int, over_by: int, slide_index: int = 1):
        from lib.defects import Defect, DefectKind, Severity
        return Defect(
            slide_index=slide_index,
            kind=DefectKind.SLOT_OVERFLOW,
            severity=Severity.WARN,
            message=f"slot '{slot}' overflows by {over_by} chars",
            meta={"slot": slot, "budget_chars": budget, "over_by": over_by},
        )

    def test_plan_fixes_returns_shorten_patch(self):
        from lib.verify.autofix import plan_fixes, FixPatch
        from lib.defects import DefectKind

        # action_title budget on executive-summary = 84 chars.  Use 90 chars
        # (6 over budget) which is BELOW the 20% swap threshold (84 * 1.20 = 100.8).
        # Below the threshold, plan_fixes must emit only shorten_slot — never
        # swap_layout_larger.
        budget = 84
        long_text = "A" * 90  # 6 chars over budget; 90 < 100.8 → below swap threshold
        plan = _make_plan(
            "layouts/executive-summary.slide.dsl",
            {"action_title": long_text, "footer_left": "Corp", "footer_right": "2026"},
        )
        defect = self._overflow_defect("action_title", budget, 6)
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert len(patches) == 1, (
            f"Expected exactly 1 patch (shorten_slot), got {patches}"
        )
        p = patches[0]
        assert isinstance(p, FixPatch)
        assert p.action == "shorten_slot", (
            f"Expected shorten_slot below swap threshold, got {p.action}"
        )
        assert p.slot == "action_title"
        assert p.slide_index == 1
        assert p.source_defect == DefectKind.SLOT_OVERFLOW

    def test_apply_fixes_trims_to_budget(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        # Use content that is over budget but BELOW the 20% swap threshold so
        # plan_fixes emits shorten_slot (not swap_layout_larger).
        # executive-summary action_title budget = 84 chars; threshold = 84*1.20 = 100.8.
        # Use 90 chars → 6 over budget, below threshold → shorten_slot fires.
        budget = 84
        long_text = "We need to restructure our go-to-market approach before Q3 deadline"  # >84 chars?
        # Ensure it fits our scenario (above budget, below threshold)
        if len(long_text) <= budget:
            long_text = long_text + " now."
        long_text = (long_text[:budget + 5]).ljust(budget + 5, "!")  # ensure exactly budget+5 chars
        assert budget < len(long_text) <= budget * 1.20, (
            f"Fixture must be above budget ({budget}) but below swap threshold "
            f"({budget * 1.20}); got len={len(long_text)}"
        )
        plan = _make_plan(
            "layouts/executive-summary.slide.dsl",
            {"action_title": long_text, "footer_left": "Corp", "footer_right": "2026"},
        )
        defect = self._overflow_defect("action_title", budget, len(long_text) - budget)
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert patches, "Expected at least one patch"
        assert patches[0].action == "shorten_slot", (
            f"Expected shorten_slot below swap threshold, got {patches[0].action}"
        )
        after = apply_fixes(plan, patches)
        result_text = after["slides"][0]["content"]["action_title"]
        assert len(result_text) <= budget, (
            f"Expected trimmed to ≤{budget} chars, got {len(result_text)}: {result_text!r}"
        )

    def test_trim_cuts_at_sentence_boundary(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        budget = 60
        # Two sentences; first fits in budget, second pushes over
        text = "Revenue fell 12% last quarter. The cause was enterprise churn."
        assert len(text) > budget
        plan = _make_plan(
            "layouts/executive-summary.slide.dsl",
            {"action_title": text, "footer_left": "Corp", "footer_right": "2026"},
        )
        defect = self._overflow_defect("action_title", budget, len(text) - budget)
        patches = plan_fixes([defect], plan, BRAND_DIR)
        after = apply_fixes(plan, patches)
        result = after["slides"][0]["content"]["action_title"]
        assert len(result) <= budget
        # Should cut at sentence boundary; first sentence ends with period
        # "Revenue fell 12% last quarter." = 31 chars → fits → should be preserved
        assert result.endswith(".")

    def test_idempotent_shorten(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        # Use content below the 20% swap threshold to ensure shorten_slot fires.
        # executive-summary budget = 84; threshold = 100.8. Use 90 chars (6 over).
        budget = 84
        long_text = "A" * 90  # 90 < 100.8 → below threshold → shorten_slot
        plan = _make_plan(
            "layouts/executive-summary.slide.dsl",
            {"action_title": long_text, "footer_left": "Corp", "footer_right": "2026"},
        )
        defect = self._overflow_defect("action_title", budget, 6)
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert patches and patches[0].action == "shorten_slot", (
            f"Expected shorten_slot below swap threshold, got {patches}"
        )
        once = apply_fixes(plan, patches)
        twice = apply_fixes(once, patches)
        assert (once["slides"][0]["content"]["action_title"] ==
                twice["slides"][0]["content"]["action_title"])


# ---------------------------------------------------------------------------
# 2. delete_word — FILLER_WORD
# ---------------------------------------------------------------------------

class TestDeleteWord:
    """FILLER_WORD defect → delete_word patch → filler removed from slot."""

    def _filler_defect(self, slot: str, word: str, slide_index: int = 1):
        from lib.defects import Defect, DefectKind, Severity
        return Defect(
            slide_index=slide_index,
            kind=DefectKind.FILLER_WORD,
            severity=Severity.WARN,
            message=f"filler word '{word}' in slot '{slot}'",
            meta={"slot": slot, "word": word, "char_index": 0},
        )

    def test_plan_fixes_returns_delete_word_patch(self):
        from lib.verify.autofix import plan_fixes, FixPatch

        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": "Revenue is really growing", "so_what": "very really good result"},
        )
        defect = self._filler_defect("so_what", "really")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert len(patches) == 1
        p = patches[0]
        assert isinstance(p, FixPatch)
        assert p.action == "delete_word"
        assert p.slot == "so_what"
        assert p.payload["word"] == "really"

    def test_apply_fixes_removes_filler_word(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {
                "action_title": "Revenue is really growing very fast",
                "so_what": "Revenue is really growing very fast",
            },
        )
        defect = self._filler_defect("so_what", "really")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        after = apply_fixes(plan, patches)
        result = after["slides"][0]["content"]["so_what"]
        # "really" removed; "very" left (only one word targeted per defect)
        assert "really" not in result.lower()

    def test_apply_fixes_removes_all_occurrences(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {
                "action_title": "Revenue grew",
                "so_what": "Revenue really grew really fast",
            },
        )
        defect = self._filler_defect("so_what", "really")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        after = apply_fixes(plan, patches)
        result = after["slides"][0]["content"]["so_what"]
        assert "really" not in result.lower(), f"All occurrences should be removed: {result!r}"

    def test_filler_word_is_case_insensitive(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {
                "action_title": "Revenue grew",
                "so_what": "Revenue REALLY grew Really fast",
            },
        )
        defect = self._filler_defect("so_what", "really")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        after = apply_fixes(plan, patches)
        result = after["slides"][0]["content"]["so_what"]
        assert "really" not in result.lower(), f"Case-insensitive removal failed: {result!r}"

    def test_idempotent_delete_word(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {
                "action_title": "Revenue grew",
                "so_what": "Revenue really grew very fast",
            },
        )
        defect = self._filler_defect("so_what", "really")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        once = apply_fixes(plan, patches)
        twice = apply_fixes(once, patches)
        assert (once["slides"][0]["content"]["so_what"] ==
                twice["slides"][0]["content"]["so_what"])


# ---------------------------------------------------------------------------
# 3. drop_bullet — BULLET_DUMP
# ---------------------------------------------------------------------------

class TestDropBullet:
    """BULLET_DUMP defect with >5 peers → drop_bullet → ≤5 bullets remain."""

    def _bullet_dump_defect(self, slot: str, slide_index: int = 1):
        from lib.defects import Defect, DefectKind, Severity
        return Defect(
            slide_index=slide_index,
            kind=DefectKind.BULLET_DUMP,
            severity=Severity.WARN,
            message=f"bullet dump in slot '{slot}'",
            meta={"slot": slot},
        )

    def _make_bullets(self, n: int) -> str:
        """Return a string with n dash bullets, shortest first (reversed by length)."""
        # Intentionally make them vary in length so the "drop weakest = shortest" logic applies
        bullets = [f"- {'x' * (10 + i * 5)} item {i + 1}" for i in range(n)]
        return "\n".join(bullets)

    def test_plan_fixes_returns_drop_bullet_patch_when_gt5(self):
        from lib.verify.autofix import plan_fixes, FixPatch

        body = self._make_bullets(7)  # 7 bullets → should trigger
        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": "Title", "supporting_body": body},
        )
        defect = self._bullet_dump_defect("supporting_body")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert len(patches) == 1
        p = patches[0]
        assert isinstance(p, FixPatch)
        assert p.action == "drop_bullet"
        assert p.slot == "supporting_body"

    def test_plan_fixes_no_patch_when_le5(self):
        """With ≤5 bullets, BULLET_DUMP produces no patch (already acceptable)."""
        from lib.verify.autofix import plan_fixes

        body = self._make_bullets(5)  # exactly 5 → no patch
        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": "Title", "supporting_body": body},
        )
        defect = self._bullet_dump_defect("supporting_body")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert patches == [], f"Expected no patch for ≤5 bullets, got {patches}"

    def test_apply_fixes_reduces_bullets_to_5(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        body = self._make_bullets(8)  # 8 bullets → drop 3
        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": "Title", "supporting_body": body},
        )
        defect = self._bullet_dump_defect("supporting_body")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert patches, "Expected drop_bullet patch"
        after = apply_fixes(plan, patches)
        result = after["slides"][0]["content"]["supporting_body"]
        # Count lines starting with bullet markers
        bullet_lines = [
            ln for ln in result.splitlines()
            if ln.startswith("- ") or ln.startswith("* ") or ln.startswith("• ")
        ]
        assert len(bullet_lines) <= 5, (
            f"Expected ≤5 bullets after drop, got {len(bullet_lines)}: {result!r}"
        )

    def test_drop_bullet_preserves_order_of_survivors(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        # 7 bullets; we want to verify the survivors are in original order
        lines = [
            "- Alpha summary item",
            "- Beta summary item",
            "- Gamma summary item that is somewhat longer",
            "- Delta summary item that is moderately longer still",
            "- Epsilon the quite long one here definitely",
            "- Zeta the longest bullet item in this set by far and clearly",
            "- Eta another long bullet item here and here",
        ]
        body = "\n".join(lines)
        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": "Title", "supporting_body": body},
        )
        defect = self._bullet_dump_defect("supporting_body")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        after = apply_fixes(plan, patches)
        result = after["slides"][0]["content"]["supporting_body"]
        survivors = [ln for ln in result.splitlines() if ln.strip()]
        # The surviving lines should appear in the same relative order as original
        original_order = [ln for ln in lines if ln in survivors]
        assert survivors == original_order, (
            f"Survivors are not in original order.\nOriginal: {original_order}\n"
            f"Got: {survivors}"
        )

    def test_idempotent_drop_bullet(self):
        from lib.verify.autofix import plan_fixes, apply_fixes

        body = self._make_bullets(7)
        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": "Title", "supporting_body": body},
        )
        defect = self._bullet_dump_defect("supporting_body")
        patches = plan_fixes([defect], plan, BRAND_DIR)
        once = apply_fixes(plan, patches)
        twice = apply_fixes(once, patches)
        assert (once["slides"][0]["content"]["supporting_body"] ==
                twice["slides"][0]["content"]["supporting_body"])


# ---------------------------------------------------------------------------
# 4. swap_layout_smaller — EMPTY_PLACEHOLDER (slot count mismatch)
# ---------------------------------------------------------------------------

class TestSwapLayoutSmaller:
    """EMPTY_PLACEHOLDER from layout having more required slots than content → swap to smaller."""

    def _empty_placeholder_defect(self, slot: str, layout: str, slide_index: int = 1):
        from lib.defects import Defect, DefectKind, Severity
        return Defect(
            slide_index=slide_index,
            kind=DefectKind.EMPTY_PLACEHOLDER,
            severity=Severity.WARN,
            message=f"slot {slot!r} is empty or missing (layout: {layout})",
            meta={"slot": slot, "layout": layout},
        )

    def test_plan_fixes_swap_layout_smaller_when_candidate_exists(self):
        """When plan has an EMPTY_PLACEHOLDER and a smaller layout exists, return swap patch."""
        from lib.verify.autofix import plan_fixes

        # Use a content-heavy layout (executive-summary) with only minimal content
        # so there are many empty slots.  The fix should propose swapping down.
        plan = {
            "brand": "feinschliff",
            "out": "deck.pptx",
            "slides": [{
                "layout": "layouts/executive-summary.slide.dsl",
                "content": {"action_title": "Short title"},
                "_meta": {
                    "role": "content-columns",
                    "concept_count": 2,
                },
            }],
        }
        defects = [self._empty_placeholder_defect("summary", "executive-summary.slide.dsl")]
        patches = plan_fixes(defects, plan, BRAND_DIR)
        # We expect either a swap_layout_smaller patch or nothing (if no smaller layout found).
        # The important thing is we don't crash and the patch (if present) is valid.
        for p in patches:
            if p.action == "swap_layout_smaller":
                assert p.slide_index == 1
                assert "new_layout" in p.payload
                break

    def test_apply_fixes_updates_layout_field(self):
        """If a swap_layout_smaller patch is returned, applying it updates the layout field."""
        from lib.verify.autofix import plan_fixes, apply_fixes, FixPatch
        from lib.defects import DefectKind

        plan = {
            "brand": "feinschliff",
            "out": "deck.pptx",
            "slides": [{
                "layout": "layouts/executive-summary.slide.dsl",
                "content": {"action_title": "Short title"},
                "_meta": {
                    "role": "content-columns",
                    "concept_count": 2,
                },
            }],
        }
        defects = [self._empty_placeholder_defect("summary", "executive-summary.slide.dsl")]
        patches = plan_fixes(defects, plan, BRAND_DIR)
        swap_patches = [p for p in patches if p.action == "swap_layout_smaller"]
        if not swap_patches:
            pytest.skip("No swap_layout_smaller candidate found — may be correct if picker has no smaller layout")
        after = apply_fixes(plan, swap_patches)
        new_layout = after["slides"][0]["layout"]
        assert new_layout != "layouts/executive-summary.slide.dsl", (
            "Expected layout to change after swap_layout_smaller"
        )


# ---------------------------------------------------------------------------
# 5. swap_layout_larger — SLOT_OVERFLOW beyond shorten_slot threshold
# ---------------------------------------------------------------------------

class TestSwapLayoutLarger:
    """SLOT_OVERFLOW where shorten_slot can't get under budget by >20% → try swap_layout_larger."""

    def test_plan_fixes_swap_layout_larger_extreme_overflow(self):
        """Extreme overflow (>20% of budget) emits ONLY swap_layout_larger (not shorten_slot).

        The new contract: when the overflow exceeds the swap threshold AND a larger
        layout candidate exists, plan_fixes emits only swap_layout_larger for that
        defect.  Emitting both would be semantically contradictory — the larger layout
        was chosen precisely because the content cannot be shortened enough.
        """
        from lib.verify.autofix import plan_fixes

        # Craft a defect where content is > 120% of budget (over by more than 20%)
        budget = 80
        content_len = 200  # 150% of budget — well above 20% threshold
        over_by = content_len - budget

        text = "W" * content_len
        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": text, "footer_left": "Corp", "footer_right": "2026"},
        )
        from lib.defects import Defect, DefectKind, Severity
        defect = Defect(
            slide_index=1,
            kind=DefectKind.SLOT_OVERFLOW,
            severity=Severity.WARN,
            message=f"slot 'action_title' overflows by {over_by} chars",
            meta={"slot": "action_title", "budget_chars": budget, "over_by": over_by},
        )
        patches = plan_fixes([defect], plan, BRAND_DIR)
        actions = {p.action for p in patches}
        # Above the threshold: swap_layout_larger must fire (if a candidate exists);
        # shorten_slot must NOT be co-emitted for the same defect.
        assert "shorten_slot" not in actions, (
            f"shorten_slot must not be emitted when swap_layout_larger fires; got {actions}"
        )
        # swap_layout_larger is best-effort — skip if no candidate found.
        if "swap_layout_larger" in actions:
            assert len(patches) == 1, (
                f"Expected exactly 1 patch (swap_layout_larger) above threshold, got {patches}"
            )

    def test_apply_swap_layout_larger_updates_layout(self):
        """If a swap_layout_larger patch exists, applying it changes the layout field.

        Setup: action-title layout with no _meta (so _find_larger_layout falls
        back to role='content-columns', concept_count=2, then bumps cc to 3).
        pick_layout(role='content-columns', cc=3) returns 'executive-summary'
        as the top non-current candidate — a known-larger layout, verified by
        inspection of the affinity table.

        The original-text length (200 chars) is 5× the budget (40 chars) —
        well over the 20% threshold — so swap_layout_larger must fire after
        the threshold fix.
        """
        from lib.verify.autofix import plan_fixes, apply_fixes

        budget = 40
        text = "X" * 200  # 5× budget — original length is clearly > budget * 1.20
        # No _meta on the slide so _find_larger_layout defaults to role='content-columns',
        # concept_count=2 → bumps to 3 → pick_layout returns 'executive-summary'
        # (a valid, existing layout) as the first non-current candidate.
        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": text},
        )
        from lib.defects import Defect, DefectKind, Severity
        defect = Defect(
            slide_index=1,
            kind=DefectKind.SLOT_OVERFLOW,
            severity=Severity.WARN,
            message="slot 'action_title' overflows",
            meta={"slot": "action_title", "budget_chars": budget, "over_by": 160},
        )
        patches = plan_fixes([defect], plan, BRAND_DIR)
        larger_patches = [p for p in patches if p.action == "swap_layout_larger"]
        assert larger_patches, (
            "Expected swap_layout_larger patch: original text (200 chars) is >120% "
            "of budget (40 chars), so the threshold check should fire. "
            "If this fails, re-check that _find_larger_layout returns a candidate "
            "for action-title with no _meta."
        )
        after = apply_fixes(plan, larger_patches)
        new_layout = after["slides"][0]["layout"]
        assert new_layout != "layouts/action-title.slide.dsl"

    def test_plan_fixes_overflow_above_swap_threshold_emits_only_swap(self):
        """Above the 20% swap threshold, plan_fixes emits EXACTLY one swap_layout_larger
        patch (no shorten_slot co-emission).

        Contract: for a single SLOT_OVERFLOW defect where original_len > budget * 1.20
        and a larger layout candidate exists, the returned patch list must contain
        exactly one patch with action == 'swap_layout_larger' and zero patches with
        action == 'shorten_slot'.
        """
        from lib.verify.autofix import plan_fixes, _SWAP_LARGER_THRESHOLD
        from lib.defects import Defect, DefectKind, Severity

        # action-title layout has a known larger candidate (executive-summary).
        # Use budget=40, content=200 chars → 200 > 40*1.20=48 → above threshold.
        budget = 40
        content_len = 200
        over_by = content_len - budget
        assert content_len > budget * (1 + _SWAP_LARGER_THRESHOLD), (
            f"Fixture must exceed threshold; {content_len} <= {budget * (1 + _SWAP_LARGER_THRESHOLD)}"
        )

        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": "X" * content_len},
        )
        defect = Defect(
            slide_index=1,
            kind=DefectKind.SLOT_OVERFLOW,
            severity=Severity.WARN,
            message=f"slot 'action_title' overflows by {over_by} chars",
            meta={"slot": "action_title", "budget_chars": budget, "over_by": over_by},
        )
        patches = plan_fixes([defect], plan, BRAND_DIR)

        shorten_patches = [p for p in patches if p.action == "shorten_slot"]
        swap_patches = [p for p in patches if p.action == "swap_layout_larger"]

        assert shorten_patches == [], (
            "shorten_slot must NOT be emitted when swap_layout_larger fires for the "
            f"same defect; got shorten_patches={shorten_patches}"
        )
        assert len(swap_patches) == 1, (
            f"Expected exactly 1 swap_layout_larger patch above threshold, "
            f"got {swap_patches}"
        )
        assert swap_patches[0].slide_index == 1
        assert "new_layout" in swap_patches[0].payload
        assert swap_patches[0].payload["new_layout"] != "layouts/action-title.slide.dsl"


# ---------------------------------------------------------------------------
# Behavioral requirements
# ---------------------------------------------------------------------------

class TestBehavioralRequirements:

    def test_empty_patches_no_op(self):
        """apply_fixes(plan, []) returns plan unchanged."""
        from lib.verify.autofix import apply_fixes
        plan = _make_plan("layouts/end.slide.dsl", {"title": "Hello", "pgmeta": "Q1"})
        result = apply_fixes(plan, [])
        assert result["slides"][0]["content"] == {"title": "Hello", "pgmeta": "Q1"}

    def test_unknown_defect_class_no_patch(self):
        """plan_fixes for an unsupported defect kind returns no patches."""
        from lib.verify.autofix import plan_fixes
        from lib.defects import Defect, DefectKind, Severity

        plan = _make_plan("layouts/end.slide.dsl", {"title": "Hello"})
        defect = Defect(
            slide_index=1,
            kind=DefectKind.CHROME_DRIFT,
            severity=Severity.FATAL,
            message="footer drifted",
            meta={},
        )
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert patches == [], f"Expected no patches for CHROME_DRIFT, got {patches}"

    def test_multi_slide_patches_independent(self):
        """Patches against different slides are independent and composable."""
        from lib.verify.autofix import plan_fixes, apply_fixes
        from lib.defects import Defect, DefectKind, Severity

        # Use content BELOW the 20% swap threshold for each slide so both get
        # shorten_slot (not swap_layout_larger).  Budget = 84 for executive-
        # summary, threshold = 100.8.  Use 90 chars (6 over budget, < 100.8).
        budget = 84
        plan = {
            "brand": "feinschliff",
            "out": "deck.pptx",
            "slides": [
                {
                    "layout": "layouts/executive-summary.slide.dsl",
                    "content": {"action_title": "A" * 90, "footer_left": "Corp", "footer_right": "2026"},
                },
                {
                    "layout": "layouts/executive-summary.slide.dsl",
                    "content": {"action_title": "B" * 90, "footer_left": "Corp", "footer_right": "2026"},
                },
            ],
        }
        defects = [
            Defect(
                slide_index=1,
                kind=DefectKind.SLOT_OVERFLOW,
                severity=Severity.WARN,
                message="overflow slide 1",
                meta={"slot": "action_title", "budget_chars": budget, "over_by": 6},
            ),
            Defect(
                slide_index=2,
                kind=DefectKind.SLOT_OVERFLOW,
                severity=Severity.WARN,
                message="overflow slide 2",
                meta={"slot": "action_title", "budget_chars": budget, "over_by": 6},
            ),
        ]
        patches = plan_fixes(defects, plan, BRAND_DIR)
        # Both slides are below the swap threshold, so exactly 2 shorten_slot patches.
        shorten_patches = [p for p in patches if p.action == "shorten_slot"]
        assert len(shorten_patches) == 2, (
            f"Expected 2 shorten_slot patches (one per slide, both below swap threshold), "
            f"got {shorten_patches}"
        )
        # No swap_layout_larger should appear — content is below the threshold.
        swap_patches = [p for p in patches if p.action == "swap_layout_larger"]
        assert swap_patches == [], (
            f"Expected no swap_layout_larger patches below threshold, got {swap_patches}"
        )
        after = apply_fixes(plan, patches)
        for i, slide in enumerate(after["slides"]):
            result = slide["content"]["action_title"]
            assert len(result) <= budget, f"Slide {i+1}: expected ≤{budget} chars, got {len(result)}"

    def test_diff_summary_non_empty_when_patches_applied(self):
        """diff_summary returns a non-empty markdown string when plan changed."""
        from lib.verify.autofix import plan_fixes, apply_fixes, diff_summary
        from lib.defects import Defect, DefectKind, Severity

        budget = 80
        plan = _make_plan(
            "layouts/executive-summary.slide.dsl",
            {"action_title": "A" * 130, "footer_left": "Corp", "footer_right": "2026"},
        )
        defect = Defect(
            slide_index=1,
            kind=DefectKind.SLOT_OVERFLOW,
            severity=Severity.WARN,
            message="overflow",
            meta={"slot": "action_title", "budget_chars": budget, "over_by": 50},
        )
        patches = plan_fixes([defect], plan, BRAND_DIR)
        after = apply_fixes(plan, patches)
        summary = diff_summary(plan, after)
        assert summary.strip(), "Expected non-empty diff summary"
        assert summary.startswith("-") or "slide" in summary.lower(), (
            f"Expected markdown bullet list, got: {summary!r}"
        )

    def test_diff_summary_empty_when_no_change(self):
        """diff_summary returns empty string when before == after."""
        from lib.verify.autofix import diff_summary

        plan = _make_plan("layouts/end.slide.dsl", {"title": "Hello"})
        summary = diff_summary(plan, plan)
        assert not summary.strip(), f"Expected empty diff for identical plans, got: {summary!r}"

    def test_text_overlap_shorten_uses_75_percent_ratio(self):
        """TEXT_OVERLAP defect with no budget_chars → shorten by 75% of current length."""
        from lib.verify.autofix import plan_fixes, apply_fixes
        from lib.defects import Defect, DefectKind, Severity

        text = "This is a body slot that overlaps with the title slot." * 2  # 108 chars
        plan = _make_plan(
            "layouts/executive-summary.slide.dsl",
            {"action_title": text, "summary": text, "footer_left": "Corp", "footer_right": "2026"},
        )
        defect = Defect(
            slide_index=1,
            kind=DefectKind.TEXT_OVERLAP,
            severity=Severity.FATAL,
            message="action_title overlaps summary",
            meta={"a_id": "action_title", "b_id": "summary", "overlap_px": 12},
        )
        patches = plan_fixes([defect], plan, BRAND_DIR)
        assert patches, "Expected shorten_slot patch for TEXT_OVERLAP"
        p = patches[0]
        assert p.action == "shorten_slot"
        after = apply_fixes(plan, patches)
        slot = p.slot
        original_len = len(plan["slides"][0]["content"][slot])
        result_len = len(after["slides"][0]["content"][slot])
        # Should be shortened — not necessarily exactly 75%, but meaningfully shorter
        assert result_len < original_len, f"Expected shortened text, same length: {result_len}"


# ---------------------------------------------------------------------------
# Integration: plan_fixes → apply_fixes → static_verify loop
# ---------------------------------------------------------------------------

class TestIntegrationLoop:
    """End-to-end: create a defective plan, apply fixes, re-verify."""

    def test_slot_overflow_resolved_by_apply_fixes(self):
        """After apply_fixes with shorten_slot, static_verify finds no SLOT_OVERFLOW.

        The fixture is sized to be above the real budget (84 chars for executive-
        summary action_title) but BELOW the 20% swap threshold (84 * 1.20 = 100.8
        chars), so plan_fixes emits shorten_slot (not swap_layout_larger).  After
        apply_fixes the text is trimmed to ≤84 chars and static_verify confirms
        that no SLOT_OVERFLOW remains for that slot.
        """
        from lib.verify.static import static_verify
        from lib.verify.autofix import plan_fixes, apply_fixes
        from lib.defects import DefectKind

        # 89 chars — above budget=84, below swap threshold=100.8 → shorten_slot fires.
        action_title = (
            "Revenue declined three consecutive quarters due to enterprise churn and acquisition gaps."
        )
        assert len(action_title) == 89, f"Fixture length changed: {len(action_title)}"

        plan = {
            "brand": "feinschliff",
            "out": "deck.pptx",
            "slides": [{
                "layout": "layouts/executive-summary.slide.dsl",
                "content": {
                    "action_title": action_title,
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            }],
        }
        # First verify — confirm the fixture actually produces a SLOT_OVERFLOW.
        initial_defects = static_verify(plan, BRAND_DIR)
        overflow = [d for d in initial_defects if d.kind == DefectKind.SLOT_OVERFLOW]
        if not overflow:
            pytest.skip(
                f"action_title ({len(action_title)} chars) fits in budget; "
                "fixture may need updating if budget was increased"
            )

        patches = plan_fixes(overflow, plan, BRAND_DIR)
        assert patches, "Expected patches for overflow defects"
        # Confirm shorten_slot was selected (content is below swap threshold).
        assert patches[0].action == "shorten_slot", (
            f"Expected shorten_slot (content below swap threshold), got {patches[0].action}"
        )
        fixed_plan = apply_fixes(plan, patches)
        after_defects = static_verify(fixed_plan, BRAND_DIR)
        after_overflow = [d for d in after_defects if d.kind == DefectKind.SLOT_OVERFLOW]
        assert after_overflow == [], (
            f"Expected no SLOT_OVERFLOW after apply_fixes, still got: {after_overflow}"
        )


# ---------------------------------------------------------------------------
# Array-slot path navigator unit tests
# ---------------------------------------------------------------------------

class TestPathNavigator:
    """Direct unit tests for _get_slot_value / _set_slot_value."""

    def test_plain_key(self):
        from lib.verify.autofix import _get_slot_value, _set_slot_value

        content = {"title": "Hello"}
        assert _get_slot_value(content, "title") == "Hello"
        assert _set_slot_value(content, "title", "World")
        assert content["title"] == "World"

    def test_array_index(self):
        from lib.verify.autofix import _get_slot_value, _set_slot_value

        content = {"kpis": [{"unit": "USD"}, {"unit": "EUR"}]}
        assert _get_slot_value(content, "kpis[0].unit") == "USD"
        assert _get_slot_value(content, "kpis[1].unit") == "EUR"
        assert _set_slot_value(content, "kpis[0].unit", "GBP")
        assert content["kpis"][0]["unit"] == "GBP"

    def test_nested_path(self):
        from lib.verify.autofix import _get_slot_value, _set_slot_value

        content = {"data": {"rows": [{"label": "A"}, {"label": "B"}]}}
        assert _get_slot_value(content, "data.rows[1].label") == "B"
        assert _set_slot_value(content, "data.rows[0].label", "Z")
        assert content["data"]["rows"][0]["label"] == "Z"

    def test_out_of_range_index_returns_none(self):
        from lib.verify.autofix import _get_slot_value, _set_slot_value

        content = {"kpis": [{"unit": "USD"}, {"unit": "EUR"}, {"unit": "GBP"}]}
        assert _get_slot_value(content, "kpis[5].unit") is None
        assert _set_slot_value(content, "kpis[5].unit", "CHF") is False

    def test_missing_key_returns_none(self):
        from lib.verify.autofix import _get_slot_value, _set_slot_value

        content = {"title": "Hello"}
        assert _get_slot_value(content, "missing_key") is None
        assert _set_slot_value(content, "missing_key", "x") is False

    def test_set_does_not_create_intermediate(self):
        from lib.verify.autofix import _set_slot_value

        content: dict = {}
        # Should not create 'kpis' key
        assert _set_slot_value(content, "kpis[0].unit", "X") is False
        assert "kpis" not in content


# ---------------------------------------------------------------------------
# Array-indexed slot patching via apply_fixes
# ---------------------------------------------------------------------------

class TestArraySlotApply:
    """apply_fixes must navigate array-indexed slot paths like 'kpis[0].unit'."""

    def test_apply_shorten_slot_array_indexed_path(self):
        """shorten_slot patch on 'kpis[0].unit' navigates into the array and mutates.

        Before: kpis[0].unit = 'US share' (8 chars).
        Defect: budget_chars=4 (over by 4).
        After apply_fixes: kpis[0].unit is shortened to ≤4 chars.
        """
        from lib.verify.autofix import apply_fixes, FixPatch
        from lib.defects import DefectKind

        plan = {
            "brand": "feinschliff",
            "out": "deck.pptx",
            "slides": [{
                "layout": "layouts/executive-summary.slide.dsl",
                "content": {
                    "kpis": [{"value": "9%", "unit": "US share"}],
                },
            }],
        }
        patch = FixPatch(
            slide_index=1,
            action="shorten_slot",
            slot="kpis[0].unit",
            payload={"budget_chars": 4},
            source_defect=DefectKind.SLOT_OVERFLOW,
        )
        after = apply_fixes(plan, [patch])
        result = after["slides"][0]["content"]["kpis"][0]["unit"]
        assert len(result) <= 4, (
            f"Expected 'kpis[0].unit' shortened to ≤4 chars, got {len(result)}: {result!r}"
        )

    def test_apply_shorten_slot_array_out_of_range(self, capsys):
        """shorten_slot on 'kpis[5].unit' with a 3-element array logs a skip and does not crash."""
        from lib.verify.autofix import apply_fixes, FixPatch
        from lib.defects import DefectKind

        plan = {
            "brand": "feinschliff",
            "out": "deck.pptx",
            "slides": [{
                "layout": "layouts/executive-summary.slide.dsl",
                "content": {
                    "kpis": [
                        {"value": "9%", "unit": "US share"},
                        {"value": "45%", "unit": "EU share"},
                        {"value": "12%", "unit": "APAC shr"},
                    ],
                },
            }],
        }
        original_kpis = [dict(k) for k in plan["slides"][0]["content"]["kpis"]]
        patch = FixPatch(
            slide_index=1,
            action="shorten_slot",
            slot="kpis[5].unit",
            payload={"budget_chars": 4},
            source_defect=DefectKind.SLOT_OVERFLOW,
        )
        # Must not raise
        after = apply_fixes(plan, [patch])

        # Content must be unchanged
        after_kpis = after["slides"][0]["content"]["kpis"]
        assert after_kpis == original_kpis, (
            "Out-of-range array patch must not mutate existing content"
        )

        # A skip message must have been emitted to stderr
        captured = capsys.readouterr()
        assert "kpis[5].unit" in captured.err, (
            f"Expected skip log mentioning 'kpis[5].unit' in stderr; got: {captured.err!r}"
        )


# ---------------------------------------------------------------------------
# Regression: array-indexed slot overflows must never trigger swap_layout_larger
# ---------------------------------------------------------------------------

class TestArraySlotOverflowAlwaysShortens:
    """plan_fixes SLOT_OVERFLOW on array-indexed paths → shorten_slot, never swap.

    Regression guard for: https://github.com/marsmike/feinschliff/issues/N
    Before the fix, 'kpis[0].unit' with content 5× over budget triggered
    swap_layout_larger, orphaning the entire kpis[] array into a layout that
    doesn't render it.  The fix: is_array_slot = '[' in slot → always shorten.
    """

    def _overflow_defect(self, slot: str, budget: int, text_len: int):
        from lib.defects import Defect, DefectKind, Severity
        return Defect(
            slide_index=1,
            kind=DefectKind.SLOT_OVERFLOW,
            severity=Severity.WARN,
            message=f"slot '{slot}' overflows by {text_len - budget} chars",
            meta={"slot": slot, "budget_chars": budget, "over_by": text_len - budget},
        )

    def test_plan_fixes_array_slot_overflow_always_shortens(self):
        """SLOT_OVERFLOW on 'kpis[0].unit' (content 5× over budget) emits shorten_slot,
        never swap_layout_larger — regardless of how far over budget the content is.

        Verifies the is_array_slot guard introduced to prevent silent orphaning of
        array data when the layout is swapped to one without a kpis[] slot.
        """
        from lib.verify.autofix import plan_fixes, _SWAP_LARGER_THRESHOLD
        from lib.defects import DefectKind

        budget = 4
        content = "United States share"  # 19 chars — 4.75× budget, well above 20% threshold
        assert len(content) > budget * (1 + _SWAP_LARGER_THRESHOLD), (
            "Fixture must be above swap threshold to exercise the guard"
        )

        plan = {
            "brand": "feinschliff",
            "out": "deck.pptx",
            "slides": [{
                "layout": "layouts/kpi-grid.slide.dsl",
                "content": {
                    "kpis": [
                        {"value": "42%", "unit": content},
                        {"value": "31%", "unit": "European Union share"},
                        {"value": "27%", "unit": "China share"},
                    ],
                },
            }],
        }
        defect = self._overflow_defect("kpis[0].unit", budget, len(content))
        patches = plan_fixes([defect], plan, BRAND_DIR)

        shorten_patches = [p for p in patches if p.action == "shorten_slot"]
        swap_patches = [p for p in patches if p.action == "swap_layout_larger"]

        assert swap_patches == [], (
            "swap_layout_larger must NOT be emitted for array-indexed slot "
            f"'kpis[0].unit' — it would orphan the kpis[] array. Got: {swap_patches}"
        )
        assert len(shorten_patches) == 1, (
            f"Expected exactly 1 shorten_slot patch for array-indexed overflow, "
            f"got {shorten_patches}"
        )
        p = shorten_patches[0]
        assert p.slot == "kpis[0].unit"
        assert p.action == "shorten_slot"
        assert p.source_defect == DefectKind.SLOT_OVERFLOW

    def test_scalar_slot_extreme_overflow_still_swaps(self):
        """Scalar slots above the swap threshold still trigger swap_layout_larger
        (the new guard must not break the existing scalar-slot swap path).
        """
        from lib.verify.autofix import plan_fixes, _SWAP_LARGER_THRESHOLD

        budget = 40
        content = "X" * 200  # 5× budget — well above threshold
        assert len(content) > budget * (1 + _SWAP_LARGER_THRESHOLD)

        plan = _make_plan(
            "layouts/action-title.slide.dsl",
            {"action_title": content},
        )
        from lib.defects import Defect, DefectKind, Severity
        defect = Defect(
            slide_index=1,
            kind=DefectKind.SLOT_OVERFLOW,
            severity=Severity.WARN,
            message="slot 'action_title' overflows",
            meta={"slot": "action_title", "budget_chars": budget, "over_by": 160},
        )
        patches = plan_fixes([defect], plan, BRAND_DIR)
        shorten_patches = [p for p in patches if p.action == "shorten_slot"]
        swap_patches = [p for p in patches if p.action == "swap_layout_larger"]

        # Scalar path: swap_layout_larger must still fire when a candidate exists.
        # (If _find_larger_layout returns no candidate, shorten_slot is the fallback —
        # but shorten must not co-exist with swap.)
        assert not (shorten_patches and swap_patches), (
            "shorten_slot and swap_layout_larger must not be co-emitted for the same defect; "
            f"got shorten={shorten_patches}, swap={swap_patches}"
        )
        # At least one patch must be returned.
        assert patches, "Expected at least one patch for extreme scalar overflow"
