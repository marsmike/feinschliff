"""Integration test for Task 8 — cli/build wires the image_provider.

Stages a fake brand + fake provider in tmp_path, runs `feinschliff build`
via subprocess (mirrors the existing CLI-test convention in
`test_cli_build_content_lint.py`), and asserts:

  - the .pptx is produced (exit 0),
  - `asset_lock.json` is written next to the deck,
  - the lock entry carries the slot id + provider + url the fake provider
    returned for the layout's `query:`.

The fake provider is loaded via `FEINSCHLIFF_PROVIDER_PATH`; the fake
brand via `FEINSCHLIFF_BRAND_PATH`. Both env knobs already exist on the
discovery loops — the test does not touch the user's real
`~/.feinschliff/` or the bundled repo brands.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
FEINSCHLIFF = REPO / "feinschliff"


# Minimal but schema-valid tokens.json body. Matches the scaffold used in
# `tests/test_brand_image_provider_config.py`. The test brand's
# `$image_provider` is added on top.
_VALID_TOKENS_BASE: dict[str, object] = {
    "color": {
        "ink": "#111111",
        "accent": "#FF5722",
        "paper": "#FFFFFF",
        "fog": "#CCCCCC",
        "graphite": "#444444",
        "steel": "#666666",
        "paper-2": "#F5F5F5",
        "accent-hover": "#FF8A65",
    },
    "font-family": {
        "display": ["Inter"],
        "body": ["Inter"],
        "mono": ["Consolas"],
    },
    "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
    "font-weight": {"regular": 400, "semibold": 600, "bold": 700},
}


@pytest.fixture
def staged_env(tmp_path):
    """Stage a fake brand pack + fake provider in tmp_path.

    Returns a dict ready to merge into the subprocess env:
      - FEINSCHLIFF_BRAND_PATH points at the brands root
      - FEINSCHLIFF_PROVIDER_PATH points at the providers root

    The brand declares `$image_provider: {kind: "test-provider"}`. The
    provider returns one `ImageHit` pointing at a local PNG fixture.
    """
    # ── PNG fixture the fake provider returns ─────────────────────────────
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    fixture_png = fixture_dir / "fixture.png"
    Image.new("RGB", (10, 10), color=(0, 128, 255)).save(fixture_png, "PNG")

    # ── Fake provider ────────────────────────────────────────────────────
    providers_root = tmp_path / "feinschliff_providers"
    providers_root.mkdir()
    provider_py = providers_root / "test_provider.py"
    # macOS/Linux only; the integration suite isn't run on Windows (see
    # pyproject.toml). The fixture path is interpolated directly into the
    # module body as a string literal — keeps the provider trivial.
    provider_py.write_text(textwrap.dedent(f"""\
        from feinschliff.io.image_provider import (
            ImageHit, ImageProvider, register_provider,
        )

        _FIXTURE_URL = "file://{fixture_png}"

        @register_provider
        class TestProvider(ImageProvider):
            name = "test-provider"

            def search(self, query, *, count=1, hints=None):
                return [ImageHit(
                    url=_FIXTURE_URL,
                    license="Test License",
                    attribution="Test Provider",
                    width=10,
                    height=10,
                    mime="image/png",
                )]
    """))

    # ── Fake brand pack ──────────────────────────────────────────────────
    brands_root = tmp_path / "brands"
    brand_dir = brands_root / "test-brand"
    brand_dir.mkdir(parents=True)
    tokens_body: dict = dict(_VALID_TOKENS_BASE)
    tokens_body["$image_provider"] = {"kind": "test-provider"}
    (brand_dir / "tokens.json").write_text(json.dumps(tokens_body))

    # ── Layout DSL using `query:` ────────────────────────────────────────
    layout_path = tmp_path / "one-picture.slide.dsl"
    layout_path.write_text(
        "canvas 1920x1080\n"
        "theme test-brand\n"
        'picture 100,100 200x200 query:"kitchen morning light"\n'
    )

    env = os.environ.copy()
    env["FEINSCHLIFF_BRAND_PATH"] = str(brands_root)
    # Discovery looks for `*.py` directly inside each entry of
    # FEINSCHLIFF_PROVIDER_PATH (mirrors how brand_discovery enumerates).
    # Point at the providers root, not its parent.
    env["FEINSCHLIFF_PROVIDER_PATH"] = str(providers_root)
    # PYTHONPATH so the fake provider can `from feinschliff.io.image_provider import ...`.
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{FEINSCHLIFF}{os.pathsep}{existing_pp}" if existing_pp else str(FEINSCHLIFF)
    )

    return {
        "env": env,
        "layout_path": layout_path,
        "fixture_png": fixture_png,
        "brand_name": "test-brand",
        "deck_dir": tmp_path / "out",
    }


def test_build_resolves_provider_and_writes_lock(staged_env, tmp_path):
    """End-to-end: `feinschliff build` discovers the test provider,
    instantiates it via the brand's `$image_provider`, threads it into
    EmitContext, resolves the `query:`, writes the picture into the
    pptx, and pins the hit into `asset_lock.json` next to the deck."""
    out_dir = staged_env["deck_dir"]
    out_dir.mkdir()
    out_pptx = out_dir / "deck.pptx"

    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "build",
            str(staged_env["layout_path"]),
            "--brand", staged_env["brand_name"],
            "-o", str(out_pptx),
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
        env=staged_env["env"],
    )

    # Surface stderr on failure so the diagnostic is visible in pytest.
    assert result.returncode == 0, (
        f"feinschliff build exited {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    # .pptx materialised at the expected path.
    assert out_pptx.is_file(), f"expected pptx at {out_pptx}"

    # asset_lock.json next to the deck.
    lock_path = out_dir / "asset_lock.json"
    assert lock_path.is_file(), (
        f"expected asset_lock.json at {lock_path}; "
        f"deck_dir contents: {sorted(p.name for p in out_dir.iterdir())}"
    )

    lock = json.loads(lock_path.read_text())
    assert lock["version"] == 1
    assert lock["provider"] == "test-provider", lock
    assert lock["slots"], "lock has no pinned slots"

    # Slot id is derived from the query string ("kitchen morning light"
    # → "kitchen_morning_light"). Pin both the URL and the metadata so a
    # future refactor of `_slot_id_from_query` or `_entry_from_hit` can't
    # silently regress the lock-file shape.
    slot_id, entry = next(iter(lock["slots"].items()))
    assert slot_id == "kitchen_morning_light", slot_id
    assert entry["query"] == "kitchen morning light"
    assert entry["url"] == f"file://{staged_env['fixture_png']}"
    assert entry["license"] == "Test License"
    assert entry["attribution"] == "Test Provider"
    assert entry["mime"] == "image/png"
    assert entry["pinned_at"].endswith("Z")
