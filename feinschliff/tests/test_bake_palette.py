"""Tests for scripts/bake_palette.py — retrofit + (eventually) from-design-md."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "bake_palette.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_retrofit_dry_run_for_feinschliff_emits_parseable_design_md():
    """Dry-run retrofit produces a DESIGN.md that the parser accepts."""
    sys.path.insert(0, str(REPO_ROOT))
    from lib.design_md import parse_text

    proc = _run("retrofit", "--brand", "feinschliff", "--dry-run")
    assert proc.returncode == 0, proc.stderr
    # Strip the "=== <path> ===" header line.
    body = proc.stdout.split("\n", 1)[1]
    dm = parse_text(body)
    assert dm.name == "Feinschliff"
    # Every color slot in tokens.json should be in DESIGN.md.
    tokens = json.loads((REPO_ROOT / "brands/feinschliff/tokens.json").read_text())
    expected = {slot for slot, v in tokens["color"].items() if isinstance(v, dict) and "$value" in v}
    assert set(dm.colors.keys()) == expected
    # Hex values should match (case-insensitive).
    for slot, v in tokens["color"].items():
        if isinstance(v, dict) and "$value" in v:
            assert dm.colors[slot] == v["$value"].lower()


def test_retrofit_round_trip_color_section_matches_tokens_json():
    """For every brand, retrofit's frontmatter colors equal tokens.json's color $value map."""
    sys.path.insert(0, str(REPO_ROOT))
    from lib.brand_discovery import discover_brands
    from lib.design_md import parse_text

    for brand in discover_brands():
        proc = _run("retrofit", "--brand", brand.name, "--dry-run")
        assert proc.returncode == 0, f"{brand.name}: {proc.stderr}"
        body = proc.stdout.split("\n", 1)[1]
        dm = parse_text(body)
        tokens = json.loads((brand.root / "tokens.json").read_text())
        for slot, v in tokens["color"].items():
            if isinstance(v, dict) and "$value" in v:
                assert dm.colors[slot] == v["$value"].lower(), (
                    f"{brand.name}/{slot}: tokens={v['$value'].lower()} vs DESIGN.md={dm.colors[slot]}"
                )


def test_retrofit_unknown_brand_fails():
    proc = _run("retrofit", "--brand", "does-not-exist", "--dry-run")
    assert proc.returncode != 0
    assert "unknown brand" in proc.stderr


def test_retrofit_writes_file(tmp_path, monkeypatch):
    """When not --dry-run, retrofit writes brands/<name>/DESIGN.md."""
    # Use real feinschliff brand — write target is gitignored on test failure cleanup.
    out = REPO_ROOT / "brands" / "feinschliff" / "DESIGN.md"
    proc = _run("retrofit", "--brand", "feinschliff")
    assert proc.returncode == 0, proc.stderr
    assert out.is_file()
    text = out.read_text()
    assert text.startswith("---\n")
    assert "name: Feinschliff" in text
    # Don't delete — let the dedicated retrofit-all step land it for real.


def test_from_design_md_unknown_brand_fails():
    """Bake fails cleanly when target brand has no DESIGN.md."""
    proc = _run("from-design-md", "--brand", "nonexistent-brand", "--base", "feinschliff")
    assert proc.returncode == 2
    assert "DESIGN.md not found" in proc.stderr


def test_build_replacement_map_validates_slot_membership():
    sys.path.insert(0, str(REPO_ROOT))
    from lib.design_md import parse_text
    from scripts.bake_palette import _build_replacement_map

    base_tokens = {
        "color": {
            "accent": {"$value": "#AABBCC"},
            "ink": {"$value": "#112233"},
        }
    }
    dm = parse_text(
        "---\nname: T\ncolors:\n  accent: \"#ddeeff\"\n  ink: \"#445566\"\n---\n"
    )
    rep = _build_replacement_map(dm, base_tokens, "test", "base")
    assert rep == {"AABBCC": "DDEEFF", "112233": "445566"}


def test_build_replacement_map_unknown_slot_raises():
    sys.path.insert(0, str(REPO_ROOT))
    from lib.design_md import parse_text
    from scripts.bake_palette import _build_replacement_map

    base_tokens = {"color": {"accent": {"$value": "#AABBCC"}}}
    dm = parse_text("---\nname: T\ncolors:\n  unknown: \"#ddeeff\"\n---\n")
    with pytest.raises(SystemExit, match="not in base brand"):
        _build_replacement_map(dm, base_tokens, "test", "base")


def test_build_replacement_map_collision_partial_override_raises():
    """If two base slots share a hex and only one is overridden, the rewrite is ambiguous."""
    sys.path.insert(0, str(REPO_ROOT))
    from lib.design_md import parse_text
    from scripts.bake_palette import _build_replacement_map

    base_tokens = {
        "color": {
            "ink": {"$value": "#0B1A33"},
            "black": {"$value": "#0B1A33"},  # collision: same hex as ink
        }
    }
    dm = parse_text("---\nname: T\ncolors:\n  ink: \"#ffffff\"\n---\n")
    with pytest.raises(SystemExit, match="hex collisions"):
        _build_replacement_map(dm, base_tokens, "test", "base")


def test_build_replacement_map_collision_aligned_override_ok():
    """If both colliding slots map to the SAME new hex, the rewrite is unambiguous."""
    sys.path.insert(0, str(REPO_ROOT))
    from lib.design_md import parse_text
    from scripts.bake_palette import _build_replacement_map

    base_tokens = {
        "color": {
            "ink": {"$value": "#0B1A33"},
            "black": {"$value": "#0B1A33"},  # collision; both overridden to same target
        }
    }
    dm = parse_text(
        "---\nname: T\ncolors:\n  ink: \"#ffffff\"\n  black: \"#ffffff\"\n---\n"
    )
    rep = _build_replacement_map(dm, base_tokens, "test", "base")
    assert rep == {"0B1A33": "FFFFFF"}


def test_build_replacement_map_collision_divergent_override_raises():
    """If colliding slots map to DIFFERENT new hexes, bake refuses (XML can't differentiate)."""
    sys.path.insert(0, str(REPO_ROOT))
    from lib.design_md import parse_text
    from scripts.bake_palette import _build_replacement_map

    base_tokens = {
        "color": {
            "ink": {"$value": "#0B1A33"},
            "black": {"$value": "#0B1A33"},
        }
    }
    dm = parse_text(
        "---\nname: T\ncolors:\n  ink: \"#ffffff\"\n  black: \"#000000\"\n---\n"
    )
    with pytest.raises(SystemExit, match="divergent overrides"):
        _build_replacement_map(dm, base_tokens, "test", "base")
