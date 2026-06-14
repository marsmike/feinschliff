"""Tests for follows_not / follows_well frontmatter parsing in layout_profile.

Covers: accept valid lists, reject non-list and non-string items (ProfileError),
absent keys are absent from the profile dict, roundtrip through a real
tmp_path .slide.dsl via load_profile.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschliff.layout_profile import ProfileError, load_profile, parse_profile

# Minimal valid frontmatter shared by tests that only vary one field.
_BASE = {
    "role": "content-columns",
    "ideal_count": [2, 4],
    "data_band": "none",
    "comparison": False,
}


def _fm(**extra) -> str:
    """Build a minimal frontmatter YAML string, merging *extra* keys."""
    import yaml
    return yaml.dump({**_BASE, **extra}, default_flow_style=False)


# ── parse_profile: follows_not ────────────────────────────────────────────────


def test_follows_not_valid_list_is_accepted():
    profile = parse_profile(_fm(follows_not=["role=closer", "role=agenda"]), source="test")
    assert profile["follows_not"] == ["role=closer", "role=agenda"]


def test_follows_not_absent_key_not_in_profile():
    profile = parse_profile(_fm(), source="test")
    assert "follows_not" not in profile


def test_follows_not_non_list_raises():
    with pytest.raises(ProfileError, match="follows_not"):
        parse_profile(_fm(follows_not="role=closer"), source="test")


def test_follows_not_non_string_item_raises():
    with pytest.raises(ProfileError, match="follows_not"):
        parse_profile(_fm(follows_not=["role=closer", 42]), source="test")


def test_follows_not_empty_list_is_accepted():
    profile = parse_profile(_fm(follows_not=[]), source="test")
    assert profile["follows_not"] == []


# ── parse_profile: follows_well ───────────────────────────────────────────────


def test_follows_well_valid_list_is_accepted():
    profile = parse_profile(
        _fm(follows_well=["role=content-columns", "narrative_act=complication"]),
        source="test",
    )
    assert profile["follows_well"] == ["role=content-columns", "narrative_act=complication"]


def test_follows_well_absent_key_not_in_profile():
    profile = parse_profile(_fm(), source="test")
    assert "follows_well" not in profile


def test_follows_well_non_list_raises():
    with pytest.raises(ProfileError, match="follows_well"):
        parse_profile(_fm(follows_well={"role": "closer"}), source="test")


def test_follows_well_non_string_item_raises():
    with pytest.raises(ProfileError, match="follows_well"):
        parse_profile(_fm(follows_well=[True, "role=closer"]), source="test")


# ── load_profile roundtrip through a real .slide.dsl file ────────────────────

_SLIDE_DSL_TEMPLATE = """\
---
role: content-columns
ideal_count: [2, 4]
data_band: none
comparison: false
follows_not:
  - role=closer
  - role=agenda
follows_well:
  - narrative_act=complication
---
canvas 1920x1080
text 100,100 maxwidth:900 maxheight:80 "{{ title }}"
"""


def test_load_profile_roundtrip_follows_keys(tmp_path: Path):
    p = tmp_path / "content.slide.dsl"
    p.write_text(_SLIDE_DSL_TEMPLATE, encoding="utf-8")
    profile = load_profile(p)
    assert profile["follows_not"] == ["role=closer", "role=agenda"]
    assert profile["follows_well"] == ["narrative_act=complication"]


def test_load_profile_absent_follows_keys_absent(tmp_path: Path):
    text = """\
---
role: content-columns
ideal_count: [2, 4]
data_band: none
comparison: false
---
canvas 1920x1080
"""
    p = tmp_path / "bare.slide.dsl"
    p.write_text(text, encoding="utf-8")
    profile = load_profile(p)
    assert "follows_not" not in profile
    assert "follows_well" not in profile
