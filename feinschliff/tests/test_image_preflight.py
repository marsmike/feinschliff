"""Tests for image_preflight — palette + crop scorer.

All tests use Pillow-synthesised images (Image.new / Image.fromarray).
No fixture files needed.
"""
from __future__ import annotations

import pytest
from PIL import Image

from feinschliff.defects import DefectKind, Severity
from feinschliff.io.image_preflight import ImageScore, preflight_image, score_image


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def solid_rgb(r: int, g: int, b: int, w: int = 100, h: int = 100) -> Image.Image:
    """Return a solid-colour RGB image."""
    img = Image.new("RGB", (w, h), (r, g, b))
    return img


# ---------------------------------------------------------------------------
# score_image — palette_clash
# ---------------------------------------------------------------------------

class TestPaletteClash:
    def test_exact_match_gives_near_zero(self):
        """Solid red (#FF0000) vs brand palette ['#FF0000'] → ~0.0."""
        img = solid_rgb(255, 0, 0)
        score = score_image(img, ["#FF0000"], target_aspect=1.0)
        assert score.palette_clash < 0.1, f"expected near-zero, got {score.palette_clash}"

    def test_complementary_clash_exceeds_threshold(self):
        """Solid red (#FF0000) vs brand palette ['#00FFFF'] (cyan) → >0.6."""
        img = solid_rgb(255, 0, 0)
        score = score_image(img, ["#00FFFF"], target_aspect=1.0)
        assert score.palette_clash > 0.6, f"expected >0.6, got {score.palette_clash}"

    def test_close_but_not_identical_partial_clash(self):
        """A slightly-off blue vs brand blue — moderate clash (0.0..1.0)."""
        img = solid_rgb(0, 0, 200)  # slightly dim blue
        score = score_image(img, ["#0000FF"], target_aspect=1.0)
        assert 0.0 <= score.palette_clash <= 1.0

    def test_multiple_brand_colors_uses_best_match(self):
        """Brand palette with one matching and one clashing colour uses the best."""
        img = solid_rgb(255, 0, 0)
        # One exact match in the palette → clash should be near-zero
        score = score_image(img, ["#00FFFF", "#FF0000"], target_aspect=1.0)
        assert score.palette_clash < 0.1

    def test_palette_clash_clamped_to_unit(self):
        """palette_clash is always in [0.0, 1.0]."""
        img = solid_rgb(255, 0, 0)
        score = score_image(img, ["#FFFFFF"], target_aspect=1.0)
        assert 0.0 <= score.palette_clash <= 1.0

    def test_pure_white_image_skipped_black_white_dominance(self):
        """Near-pure-white image (watermark case) — scorer should not crash."""
        img = solid_rgb(255, 255, 255)
        score = score_image(img, ["#FFFFFF"], target_aspect=1.0)
        # Score is valid even for white images
        assert 0.0 <= score.palette_clash <= 1.0


# ---------------------------------------------------------------------------
# score_image — crop_risk
# ---------------------------------------------------------------------------

class TestCropRisk:
    def test_matching_aspect_gives_near_zero(self):
        """16:9 image vs 16:9 target → crop_risk ≈ 0.0."""
        img = solid_rgb(100, 100, 100, w=1600, h=900)
        score = score_image(img, ["#646464"], target_aspect=16 / 9)
        assert score.crop_risk < 0.15, f"expected near-zero, got {score.crop_risk}"

    def test_aspect_mismatch_square_vs_widescreen_high_risk(self):
        """16:9 image scored against 1:1 target → crop_risk > 0.5."""
        img = solid_rgb(100, 100, 100, w=1600, h=900)
        score = score_image(img, ["#646464"], target_aspect=1.0)
        assert score.crop_risk > 0.5, f"expected >0.5, got {score.crop_risk}"

    def test_portrait_vs_landscape_high_risk(self):
        """Tall portrait (2:3) vs landscape (3:2) → high crop risk."""
        img = solid_rgb(100, 100, 100, w=200, h=300)
        score = score_image(img, ["#646464"], target_aspect=3 / 2)
        assert score.crop_risk > 0.5

    def test_similar_aspect_low_risk(self):
        """Slightly wider than target (within 15%) → ~0.0 risk."""
        # Image is 16:10 (1.6), target is 16:9 (1.777) — ratio ≈ 10% diff
        img = solid_rgb(100, 100, 100, w=1600, h=1000)
        target = 16 / 9
        score = score_image(img, ["#646464"], target_aspect=target)
        assert score.crop_risk < 0.2

    def test_crop_risk_clamped_to_unit(self):
        """crop_risk is always in [0.0, 1.0]."""
        img = solid_rgb(100, 100, 100, w=100, h=1000)
        score = score_image(img, ["#FFFFFF"], target_aspect=16 / 9)
        assert 0.0 <= score.crop_risk <= 1.0


# ---------------------------------------------------------------------------
# score_image — dominant_hex and aspect_ratio
# ---------------------------------------------------------------------------

class TestDominantHexAndAspect:
    def test_dominant_hex_returns_three_items(self):
        """solid-colour image has ≤ 3 dominant hex values returned."""
        img = solid_rgb(200, 50, 50)
        score = score_image(img, ["#FF0000"], target_aspect=1.0)
        assert 1 <= len(score.dominant_hex) <= 3

    def test_dominant_hex_format(self):
        """Each dominant_hex entry is a lowercase '#rrggbb' string."""
        img = solid_rgb(200, 50, 50)
        score = score_image(img, ["#FF0000"], target_aspect=1.0)
        for h in score.dominant_hex:
            assert h.startswith("#"), f"expected #rrggbb, got {h}"
            assert len(h) == 7, f"expected 7-char hex, got {h}"

    def test_aspect_ratio_stored_correctly(self):
        """aspect_ratio = width / height."""
        img = solid_rgb(100, 100, 100, w=1600, h=900)
        score = score_image(img, ["#646464"], target_aspect=1.0)
        assert abs(score.aspect_ratio - 1600 / 900) < 0.01

    def test_square_image_aspect_is_one(self):
        img = solid_rgb(100, 100, 100, w=200, h=200)
        score = score_image(img, ["#646464"], target_aspect=1.0)
        assert abs(score.aspect_ratio - 1.0) < 0.001

    def test_white_dominant_skip_still_returns_list(self):
        """White-dominant image skips black/white, still returns list (possibly shorter)."""
        img = solid_rgb(255, 255, 255, w=200, h=200)
        score = score_image(img, ["#FFFFFF"], target_aspect=1.0)
        # Even if all quantized colors are "near-white", we should get a list
        assert isinstance(score.dominant_hex, list)

    def test_non_rgb_image_handled(self):
        """RGBA and grayscale images are converted to RGB without error."""
        rgba = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        score_rgba = score_image(rgba, ["#FF0000"], target_aspect=1.0)
        assert isinstance(score_rgba, ImageScore)

        gray = Image.new("L", (100, 100), 128)
        score_gray = score_image(gray, ["#808080"], target_aspect=1.0)
        assert isinstance(score_gray, ImageScore)


# ---------------------------------------------------------------------------
# preflight_image — defect emission
# ---------------------------------------------------------------------------

class TestPreflightImage:
    def test_no_defects_when_scores_below_thresholds(self):
        """Matching palette and aspect → no defects."""
        img = solid_rgb(255, 0, 0, w=1600, h=900)
        score, defects = preflight_image(
            img,
            brand_palette_hex=["#FF0000"],
            slot_aspect=16 / 9,
            slide_index=0,
        )
        assert defects == []
        assert isinstance(score, ImageScore)

    def test_palette_clash_defect_fired(self):
        """Clashing image → IMAGE_PALETTE_CLASH defect emitted."""
        img = solid_rgb(255, 0, 0)  # red
        score, defects = preflight_image(
            img,
            brand_palette_hex=["#00FFFF"],  # cyan — complementary
            slot_aspect=1.0,
            slide_index=2,
        )
        kinds = [d.kind for d in defects]
        assert DefectKind.IMAGE_PALETTE_CLASH in kinds

    def test_palette_clash_defect_slide_index(self):
        """IMAGE_PALETTE_CLASH defect carries the correct slide_index."""
        img = solid_rgb(255, 0, 0)
        _, defects = preflight_image(
            img, brand_palette_hex=["#00FFFF"], slot_aspect=1.0, slide_index=7
        )
        clash_defects = [d for d in defects if d.kind == DefectKind.IMAGE_PALETTE_CLASH]
        assert clash_defects, "expected at least one IMAGE_PALETTE_CLASH defect"
        assert clash_defects[0].slide_index == 7

    def test_palette_clash_defect_is_warn(self):
        """IMAGE_PALETTE_CLASH is WARN severity."""
        img = solid_rgb(255, 0, 0)
        _, defects = preflight_image(
            img, brand_palette_hex=["#00FFFF"], slot_aspect=1.0, slide_index=0
        )
        for d in defects:
            if d.kind == DefectKind.IMAGE_PALETTE_CLASH:
                assert d.severity == Severity.WARN
                break

    def test_crop_risk_defect_fired(self):
        """Mismatched aspect → IMAGE_CROP_RISK defect emitted."""
        img = solid_rgb(255, 0, 0, w=1600, h=900)  # 16:9
        score, defects = preflight_image(
            img,
            brand_palette_hex=["#FF0000"],
            slot_aspect=1.0,  # 1:1 target — big mismatch
            slide_index=3,
        )
        kinds = [d.kind for d in defects]
        assert DefectKind.IMAGE_CROP_RISK in kinds

    def test_crop_risk_defect_is_warn(self):
        """IMAGE_CROP_RISK is WARN severity."""
        img = solid_rgb(255, 0, 0, w=1600, h=900)
        _, defects = preflight_image(
            img, brand_palette_hex=["#FF0000"], slot_aspect=1.0, slide_index=0
        )
        for d in defects:
            if d.kind == DefectKind.IMAGE_CROP_RISK:
                assert d.severity == Severity.WARN
                break

    def test_both_defects_can_fire_simultaneously(self):
        """Clashing palette + bad aspect → both defects fired."""
        img = solid_rgb(255, 0, 0, w=1600, h=900)
        _, defects = preflight_image(
            img,
            brand_palette_hex=["#00FFFF"],  # clash
            slot_aspect=1.0,  # crop risk
            slide_index=1,
        )
        kinds = {d.kind for d in defects}
        assert DefectKind.IMAGE_PALETTE_CLASH in kinds
        assert DefectKind.IMAGE_CROP_RISK in kinds

    def test_custom_thresholds_respected(self):
        """Custom thresholds: very tight palette threshold fires defect."""
        img = solid_rgb(200, 0, 0)  # slightly dim red
        # Set palette_clash threshold to 0.0 so almost any deviation fires
        _, defects_tight = preflight_image(
            img,
            brand_palette_hex=["#FF0000"],
            slot_aspect=1.0,
            slide_index=0,
            thresholds={"palette_clash": 0.0, "crop_risk": 1.0},
        )
        kinds = {d.kind for d in defects_tight}
        assert DefectKind.IMAGE_PALETTE_CLASH in kinds

    def test_custom_thresholds_suppress_defects(self):
        """Custom thresholds: very lenient threshold suppresses defect."""
        img = solid_rgb(255, 0, 0, w=1600, h=900)  # 16:9
        # crop_risk threshold at 1.0 — nothing fires
        _, defects = preflight_image(
            img,
            brand_palette_hex=["#FF0000"],
            slot_aspect=1.0,  # would normally fire crop risk
            slide_index=0,
            thresholds={"palette_clash": 1.0, "crop_risk": 1.0},
        )
        assert defects == []

    def test_defect_meta_includes_score_values(self):
        """Defect meta dict contains the computed score for diagnostics."""
        img = solid_rgb(255, 0, 0)
        _, defects = preflight_image(
            img, brand_palette_hex=["#00FFFF"], slot_aspect=1.0, slide_index=0
        )
        clash = next(d for d in defects if d.kind == DefectKind.IMAGE_PALETTE_CLASH)
        assert "palette_clash" in clash.meta


# ---------------------------------------------------------------------------
# DefectKind taxonomy — image kinds present and WARN-only
# ---------------------------------------------------------------------------

class TestDefectKindTaxonomy:
    def test_image_palette_clash_in_enum(self):
        assert DefectKind.IMAGE_PALETTE_CLASH.value == "image-palette-clash"

    def test_image_crop_risk_in_enum(self):
        assert DefectKind.IMAGE_CROP_RISK.value == "image-crop-risk"

    def test_image_defects_not_fatal(self):
        from feinschliff.defects import fatal_kinds
        fatal = fatal_kinds()
        assert DefectKind.IMAGE_PALETTE_CLASH.value not in fatal
        assert DefectKind.IMAGE_CROP_RISK.value not in fatal


# ---------------------------------------------------------------------------
# ImageScore frozen dataclass
# ---------------------------------------------------------------------------

class TestImageScoreDataclass:
    def test_is_frozen(self):
        img = solid_rgb(100, 100, 100)
        score = score_image(img, ["#646464"], target_aspect=1.0)
        with pytest.raises((AttributeError, TypeError)):
            score.palette_clash = 0.5  # type: ignore[misc]

    def test_fields_present(self):
        img = solid_rgb(100, 100, 100)
        score = score_image(img, ["#646464"], target_aspect=1.0)
        assert hasattr(score, "palette_clash")
        assert hasattr(score, "crop_risk")
        assert hasattr(score, "dominant_hex")
        assert hasattr(score, "aspect_ratio")
