"""Tests for clip_text_to_images and clip_to_images_enabled in slotify.py.

All fixtures use the same slide-22 / chapter-2 geometry classes described in
the TEXT_OVER_IMAGE incident spec, with neutral synthetic content only.
"""
import json

from feinschliff_builder.decompile.slotify import clip_text_to_images, clip_to_images_enabled

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_line(x, y, maxw, maxh, name="text_1", default="Body copy"):
    return (
        f'text {x},{y} size:16pt maxwidth:{maxw} maxheight:{maxh} '
        f'"{{{{ {name} | default(\\"{default}\\") }}}}"\n'
    )


def _pic_line(x, y, w, h, name="image2"):
    return (
        f'picture {x},{y} {w}x{h} '
        f'path:"{{{{ {name} | default(\\"placeholder.jpg\\") }}}}"\n'
    )


# ---------------------------------------------------------------------------
# slide-22 class: full-width text + right-half picture
# ---------------------------------------------------------------------------

def test_slide22_clips_maxwidth():
    """text 75,208 maxwidth:1835 + picture 1006,0 914x1080 → maxwidth 915."""
    dsl = (
        'canvas 1920x1080\n'
        + _pic_line(1006, 0, 914, 1080)
        + _text_line(75, 208, 1835, 787)
    )
    new_dsl, logs = clip_text_to_images(dsl)
    # new_maxw = 1006 - 75 - 16 = 915
    assert "maxwidth:915" in new_dsl, new_dsl
    # original maxheight untouched
    assert "maxheight:787" in new_dsl
    assert len(logs) == 1
    assert "text_1" in logs[0]
    assert "1835" in logs[0]
    assert "915" in logs[0]
    assert "image2" in logs[0]


def test_slide22_label_preserved():
    """The {{ text_N | default(...) }} token is preserved byte-for-byte."""
    dsl = (
        'canvas 1920x1080\n'
        + _pic_line(1006, 0, 914, 1080)
        + _text_line(75, 208, 1835, 787)
    )
    new_dsl, _ = clip_text_to_images(dsl)
    assert '"{{ text_1 | default(\\"Body copy\\") }}"' in new_dsl


# ---------------------------------------------------------------------------
# Fully-contained overlay → untouched
# ---------------------------------------------------------------------------

def test_fully_contained_overlay_untouched():
    """Title inside full-bleed photo: contained → no clip, no log."""
    dsl = (
        'canvas 1920x1080\n'
        + _pic_line(0, 0, 1920, 1080)
        + _text_line(75, 483, 1835, 81)
    )
    new_dsl, logs = clip_text_to_images(dsl)
    assert new_dsl == dsl
    assert logs == []


# ---------------------------------------------------------------------------
# Origin inside picture → warn-only (untouched)
# ---------------------------------------------------------------------------

def test_origin_inside_picture_untouched():
    """Text origin sits inside the picture box → clip is unsafe, leave alone."""
    # picture covers 500,0 to 1920x1080; text starts at x=600 (inside)
    dsl = (
        'canvas 1920x1080\n'
        + _pic_line(500, 0, 1420, 1080)
        + _text_line(600, 208, 1200, 600)
    )
    new_dsl, logs = clip_text_to_images(dsl)
    assert new_dsl == dsl
    assert logs == []


# ---------------------------------------------------------------------------
# Remainder too narrow → untouched
# ---------------------------------------------------------------------------

def test_too_narrow_remainder_untouched():
    """Picture at x=120 with text origin 75 → new_maxw = 120-75-16 = 29 < 200 → skip."""
    dsl = (
        'canvas 1920x1080\n'
        + _pic_line(120, 0, 1800, 1080)
        + _text_line(75, 208, 1835, 787)
    )
    new_dsl, logs = clip_text_to_images(dsl)
    assert new_dsl == dsl
    assert logs == []


# ---------------------------------------------------------------------------
# Picture below: clip maxheight
# ---------------------------------------------------------------------------

def test_picture_below_clips_maxheight():
    """text 75,208 maxheight:787 + picture 0,700 1920x380 → maxheight 476."""
    # new_maxh = 700 - 208 - 16 = 476
    dsl = (
        'canvas 1920x1080\n'
        + _pic_line(0, 700, 1920, 380)
        + _text_line(75, 208, 1835, 787)
    )
    new_dsl, logs = clip_text_to_images(dsl)
    assert "maxheight:476" in new_dsl, new_dsl
    # original maxwidth untouched
    assert "maxwidth:1835" in new_dsl
    assert len(logs) == 1
    assert "787" in logs[0]
    assert "476" in logs[0]


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def test_idempotent():
    """Running clip_text_to_images twice yields identical DSL and no logs."""
    dsl = (
        'canvas 1920x1080\n'
        + _pic_line(1006, 0, 914, 1080)
        + _text_line(75, 208, 1835, 787)
    )
    once, _ = clip_text_to_images(dsl)
    twice, logs2 = clip_text_to_images(once)
    assert twice == once
    assert logs2 == []


# ---------------------------------------------------------------------------
# Extra kwargs byte-preserved
# ---------------------------------------------------------------------------

def test_extra_kwargs_preserved():
    """autoshrink: and style: and other kwargs on the line are untouched."""
    dsl = (
        'canvas 1920x1080\n'
        + _pic_line(1006, 0, 914, 1080)
        # hand-craft a line with autoshrink + style kwargs
        + 'text 75,208 style:body size:16pt maxwidth:1835 maxheight:787 '
          'autoshrink:true "{{ text_1 | default(\\"Body copy\\") }}"\n'
    )
    new_dsl, logs = clip_text_to_images(dsl)
    assert "style:body" in new_dsl
    assert "autoshrink:true" in new_dsl
    assert "maxwidth:915" in new_dsl
    assert '"{{ text_1 | default(\\"Body copy\\") }}"' in new_dsl
    assert logs


# ---------------------------------------------------------------------------
# clip_to_images_enabled
# ---------------------------------------------------------------------------

def test_clip_to_images_enabled_default_true_when_tokens_missing(tmp_path):
    pack = tmp_path / "brand"
    pack.mkdir()
    assert clip_to_images_enabled(pack) is True


def test_clip_to_images_enabled_false_for_explicit_false(tmp_path):
    pack = tmp_path / "brand"
    pack.mkdir()
    (pack / "tokens.json").write_text(
        json.dumps({"text-fit": {"clip-to-images": False}}), encoding="utf-8"
    )
    assert clip_to_images_enabled(pack) is False


def test_clip_to_images_enabled_false_for_value_wrapped_false(tmp_path):
    pack = tmp_path / "brand"
    pack.mkdir()
    (pack / "tokens.json").write_text(
        json.dumps({"text-fit": {"clip-to-images": {"$value": False}}}),
        encoding="utf-8",
    )
    assert clip_to_images_enabled(pack) is False


def test_clip_to_images_enabled_true_for_malformed_json(tmp_path):
    pack = tmp_path / "brand"
    pack.mkdir()
    (pack / "tokens.json").write_text("{ not valid json }", encoding="utf-8")
    assert clip_to_images_enabled(pack) is True
