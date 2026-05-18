"""Tests for the ``picture query:`` provider-resolved branch (Task 7).

Covers the 6 cases enumerated in the image-provider-framework plan:

  1. ``query:`` + ``path:`` together → ``DSLError``.
  2. ``query:`` with no provider wired → loud error.
  3. Happy path: a fake provider returns one hit; the slide gets a
     picture shape and ``asset_lock.json`` is written.
  4. Lock re-use: the second build with the same slot id does NOT call
     ``provider.search`` again.
  5. Stale lock (``file://`` URL points at a deleted file): the
     provider is re-called and the lock is overwritten.
  6. Provider returns ``[]``: ``missing_assets`` gets a ``no-hit`` entry
     and a placeholder rect is emitted in place of the picture.

The test isolates the provider registry per-test so other tests' fakes
don't leak. The PNG fixture is generated via Pillow at the start of
each test.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

from lib import image_provider
from lib.dsl.parser import parse_lines
from lib.dsl.pptx_emit import DSLError, build_presentation
from lib.image_provider import ImageHit, ImageProvider
from tests.test_emitter_restraint import _minimal_tokens


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_registry(monkeypatch):
    """Per-test registry isolation — fakes registered here don't leak."""
    monkeypatch.setattr(image_provider, "_REGISTRY", {})
    monkeypatch.setattr(image_provider, "_DISCOVERED", False)
    yield


@pytest.fixture
def tiny_png(tmp_path) -> Path:
    """Generate a 10×10 red PNG and return its path."""
    p = tmp_path / "fixture.png"
    Image.new("RGB", (10, 10), color=(255, 0, 0)).save(p, "PNG")
    return p


def _build(dsl: str, *, deck_dir: Path, provider: ImageProvider | None = None):
    """Render one DSL slide through build_presentation with the new kwargs."""
    nodes, _ = parse_lines(dsl)
    return build_presentation(
        nodes,
        _minimal_tokens(),
        image_provider=provider,
        deck_dir=deck_dir,
    )


# ---------------------------------------------------------------------------
# Case 1 — mutex: query: and path: cannot coexist
# ---------------------------------------------------------------------------

def test_picture_query_and_path_together_raises_dsl_error(tmp_path):
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"kitchen" path:"/tmp/x.png"'
    )
    with pytest.raises(DSLError) as exc:
        _build(dsl, deck_dir=tmp_path)
    assert "mutually exclusive" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Case 2 — query: without ctx.image_provider raises loudly
# ---------------------------------------------------------------------------

def test_picture_query_without_provider_raises_dsl_error(tmp_path):
    """The plan is explicit: failing loud is correct when the brand author
    forgot to wire ``$image_provider`` but layouts still reference
    ``query:``. We do NOT silently fall through to a placeholder rect —
    that would mask a brand-pack misconfiguration."""
    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"kitchen"'
    )
    with pytest.raises(DSLError) as exc:
        _build(dsl, deck_dir=tmp_path, provider=None)
    msg = str(exc.value).lower()
    assert "provider" in msg
    assert "query" in msg


# ---------------------------------------------------------------------------
# Case 3 — happy path: provider returns a hit, picture emitted, lock written
# ---------------------------------------------------------------------------

def test_picture_query_happy_path_writes_picture_and_lock(tmp_path, tiny_png):
    import json

    hit = ImageHit(
        url=f"file://{tiny_png}",
        license="Test License",
        attribution="Jane Doe",
        width=10,
        height=10,
        mime="image/png",
    )
    provider = MagicMock(spec=ImageProvider)
    provider.name = "fakeprov"
    provider.search.return_value = [hit]

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"kitchen morning light"'
    )
    prs = _build(dsl, deck_dir=tmp_path, provider=provider)

    # Picture shape on the slide (not a placeholder rect).
    shapes = list(prs.slides[0].shapes)
    assert len(shapes) == 1
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    assert shapes[0].shape_type == MSO_SHAPE_TYPE.PICTURE, (
        f"expected a PICTURE shape, got {shapes[0].shape_type!r}"
    )

    # Lock file written with the hit data.
    lock_path = tmp_path / "asset_lock.json"
    assert lock_path.is_file(), "asset_lock.json should have been written"
    lock = json.loads(lock_path.read_text())
    assert lock["version"] == 1
    assert lock["provider"] == "fakeprov"
    assert "slots" in lock
    # Slot id derived from query (deterministic).
    assert len(lock["slots"]) == 1
    slot_id = next(iter(lock["slots"]))
    entry = lock["slots"][slot_id]
    assert entry["query"] == "kitchen morning light"
    assert entry["url"] == f"file://{tiny_png}"
    assert entry["license"] == "Test License"
    assert entry["attribution"] == "Jane Doe"
    assert entry["mime"] == "image/png"
    assert entry["pinned_at"].endswith("Z")  # UTC ISO with Z suffix

    # No missing_assets — we got a real picture.
    assert prs.missing_assets == []


# ---------------------------------------------------------------------------
# Case 4 — second build with same slot id reuses lock, does NOT re-search
# ---------------------------------------------------------------------------

def test_picture_query_lock_reuse_skips_provider_search(tmp_path, tiny_png):
    hit = ImageHit(
        url=f"file://{tiny_png}",
        license="Test License",
        attribution="Jane Doe",
        width=10,
        height=10,
        mime="image/png",
    )
    provider = MagicMock(spec=ImageProvider)
    provider.name = "fakeprov"
    provider.search.return_value = [hit]

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"reuse me"'
    )

    # First build: provider.search is called once, lock is written.
    _build(dsl, deck_dir=tmp_path, provider=provider)
    assert provider.search.call_count == 1

    # Second build: lock is hit, provider.search is NOT called again.
    provider.search.reset_mock()
    _build(dsl, deck_dir=tmp_path, provider=provider)
    provider.search.assert_not_called()


# ---------------------------------------------------------------------------
# Case 5 — stale lock (file:// URL no longer exists) → re-search, overwrite
# ---------------------------------------------------------------------------

def test_picture_query_stale_lock_triggers_research(tmp_path):
    import json

    # Pre-stage a lock file pointing at a non-existent fixture.
    stale_path = tmp_path / "stale.png"  # never created
    fresh_path = tmp_path / "fresh.png"
    Image.new("RGB", (10, 10), color=(0, 255, 0)).save(fresh_path, "PNG")

    # Derive the slot id manually — re-emit must overwrite this slot.
    # Slot id derivation: lowercase, non-alnum → '_', trim, truncate.
    # "stale check" → "stale_check".
    lock = {
        "version": 1,
        "provider": "fakeprov",
        "slots": {
            "stale_check": {
                "query": "stale check",
                "url": f"file://{stale_path}",
                "license": "Old License",
                "attribution": "Old Author",
                "mime": "image/png",
                "pinned_at": "2020-01-01T00:00:00Z",
            }
        },
    }
    (tmp_path / "asset_lock.json").write_text(json.dumps(lock))

    fresh_hit = ImageHit(
        url=f"file://{fresh_path}",
        license="Fresh License",
        attribution="Fresh Author",
        width=10,
        height=10,
        mime="image/png",
    )
    provider = MagicMock(spec=ImageProvider)
    provider.name = "fakeprov"
    provider.search.return_value = [fresh_hit]

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"stale check"'
    )
    prs = _build(dsl, deck_dir=tmp_path, provider=provider)

    # Provider must have been re-called because the pinned file is gone.
    assert provider.search.call_count == 1

    # Lock entry overwritten with the fresh URL.
    new_lock = json.loads((tmp_path / "asset_lock.json").read_text())
    entry = new_lock["slots"]["stale_check"]
    assert entry["url"] == f"file://{fresh_path}"
    assert entry["license"] == "Fresh License"
    assert entry["pinned_at"] != "2020-01-01T00:00:00Z"

    # Picture shape rendered from the fresh fixture.
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    assert list(prs.slides[0].shapes)[0].shape_type == MSO_SHAPE_TYPE.PICTURE


# ---------------------------------------------------------------------------
# Case 6 — provider returns [] → no-hit missing_assets entry + placeholder
# ---------------------------------------------------------------------------

def test_picture_query_no_hit_records_missing_and_emits_placeholder(tmp_path):
    provider = MagicMock(spec=ImageProvider)
    provider.name = "fakeprov"
    provider.search.return_value = []

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"nothing matches"'
    )
    prs = _build(dsl, deck_dir=tmp_path, provider=provider)

    # missing_assets gets a no-hit entry.
    assert prs.missing_assets, "expected a missing_assets entry"
    no_hit = [e for e in prs.missing_assets if e.get("kind") == "no-hit"]
    assert len(no_hit) == 1
    assert no_hit[0]["query"] == "nothing matches"

    # Placeholder rect was emitted (not a picture).
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shapes = list(prs.slides[0].shapes)
    assert len(shapes) == 1
    # AUTO_SHAPE for a rect; definitely not PICTURE.
    assert shapes[0].shape_type != MSO_SHAPE_TYPE.PICTURE

    # No lock entry should have been written for a failed search — that
    # would pin the failure permanently.
    lock_path = tmp_path / "asset_lock.json"
    if lock_path.is_file():
        import json
        lock = json.loads(lock_path.read_text())
        assert "nothing_matches" not in lock.get("slots", {}), (
            "failed search must not be pinned in asset_lock.json"
        )


# ---------------------------------------------------------------------------
# Extras — additional smoke coverage
# ---------------------------------------------------------------------------

def test_slot_id_from_query_is_deterministic(tmp_path, tiny_png):
    """Same query string → same slot id across builds, regardless of provider."""
    import json

    hit = ImageHit(
        url=f"file://{tiny_png}",
        license="L", attribution="A",
        width=10, height=10, mime="image/png",
    )

    def _new_provider():
        p = MagicMock(spec=ImageProvider)
        p.name = "fakeprov"
        p.search.return_value = [hit]
        return p

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"Kitchen morning light!"'
    )
    _build(dsl, deck_dir=tmp_path, provider=_new_provider())
    lock = json.loads((tmp_path / "asset_lock.json").read_text())
    slot_id_first = next(iter(lock["slots"]))

    # Wipe lock; build again — slot id must match.
    (tmp_path / "asset_lock.json").unlink()
    _build(dsl, deck_dir=tmp_path, provider=_new_provider())
    lock_again = json.loads((tmp_path / "asset_lock.json").read_text())
    slot_id_second = next(iter(lock_again["slots"]))

    assert slot_id_first == slot_id_second
    # Sanity: no leading/trailing underscore, lowercase, no punctuation.
    assert slot_id_first == "kitchen_morning_light"


def test_brand_switch_invalidates_lock(tmp_path, tiny_png):
    """A lock written under provider A is ignored when provider B is active.

    Different providers have different URL schemes / licensing — the
    pin must be re-acquired against the new provider.
    """
    import json

    hit_a = ImageHit(
        url=f"file://{tiny_png}", license="A", attribution="AA",
        width=10, height=10, mime="image/png",
    )
    prov_a = MagicMock(spec=ImageProvider)
    prov_a.name = "provider_a"
    prov_a.search.return_value = [hit_a]

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"shared query"'
    )
    _build(dsl, deck_dir=tmp_path, provider=prov_a)
    assert prov_a.search.call_count == 1

    # Now build with provider_b — search must be called because the lock
    # is scoped to provider_a.
    prov_b = MagicMock(spec=ImageProvider)
    prov_b.name = "provider_b"
    prov_b.search.return_value = [hit_a]
    _build(dsl, deck_dir=tmp_path, provider=prov_b)
    assert prov_b.search.call_count == 1, (
        "provider switch should invalidate the pin and trigger re-search"
    )

    # Lock now reflects provider_b.
    lock = json.loads((tmp_path / "asset_lock.json").read_text())
    assert lock["provider"] == "provider_b"


def test_picture_query_search_exception_treated_as_no_hit(tmp_path):
    """``provider.search()`` raising must be caught at the
    ``_emit_picture`` boundary and treated like an empty result — same
    as ``return []``. Per spec §"Failure modes": placeholder rect +
    ``missing_assets`` entry, no crash. Without this test a future
    refactor could silently drop the ``except Exception: return None``
    in ``_lookup_lock_then_search``.
    """
    provider = MagicMock(spec=ImageProvider)
    provider.name = "fakeprov"
    provider.search.side_effect = RuntimeError("upstream API exploded")

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"explodes"'
    )
    # No exception should bubble out of the build.
    prs = _build(dsl, deck_dir=tmp_path, provider=provider)

    # missing_assets gets a no-hit entry (impl maps exceptions to the same
    # path as a `[]` return — see `_lookup_lock_then_search`).
    assert prs.missing_assets, "expected a missing_assets entry"
    no_hit = [e for e in prs.missing_assets if e.get("kind") == "no-hit"]
    assert len(no_hit) == 1
    assert no_hit[0]["query"] == "explodes"
    assert no_hit[0]["provider"] == "fakeprov"

    # Placeholder rect emitted (not a picture).
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shapes = list(prs.slides[0].shapes)
    assert len(shapes) == 1
    assert shapes[0].shape_type != MSO_SHAPE_TYPE.PICTURE

    # Failed search must NOT be pinned in asset_lock.json — a stale
    # "no results" entry would block the slot forever.
    lock_path = tmp_path / "asset_lock.json"
    if lock_path.is_file():
        import json
        lock = json.loads(lock_path.read_text())
        assert "explodes" not in lock.get("slots", {}), (
            "exception-raising search must not be pinned in asset_lock.json"
        )


def test_picture_query_warns_when_deck_dir_unset_for_http_hit(tmp_path):
    """When ``ctx.deck_dir`` is ``None`` and the resolved hit needs HTTP
    materialise, a ``RuntimeWarning`` must fire so library callers who
    forgot to wire ``deck_dir`` notice (no rebuild cache reuse). The
    fallback itself still completes the build via a throwaway tempdir.

    We mock ``urllib.request.urlopen`` so no real network call happens.
    """
    import urllib.request as _urlreq

    # Minimal valid PNG payload — pptx Picture insertion calls Pillow to
    # introspect dimensions, so the bytes need to actually be parseable.
    from io import BytesIO
    buf = BytesIO()
    Image.new("RGB", (10, 10), color=(0, 0, 255)).save(buf, "PNG")
    png_bytes = buf.getvalue()

    class _FakeResp:
        def __init__(self, data):
            self._data = data

        def read(self):
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    def _fake_urlopen(url, timeout=None):  # noqa: ARG001
        return _FakeResp(png_bytes)

    hit = ImageHit(
        url="https://example.invalid/test.png",
        license="L", attribution="A",
        width=10, height=10, mime="image/png",
    )
    provider = MagicMock(spec=ImageProvider)
    provider.name = "fakeprov"
    provider.search.return_value = [hit]

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"needs http"'
    )

    # deck_dir=None forces the tempdir fallback path. We still need a
    # tmp_path for any other I/O the build might do, but pass None to
    # the EmitContext via the helper signature.
    nodes, _ = parse_lines(dsl)
    from lib.dsl.pptx_emit import build_presentation as _bp

    import unittest.mock as _um
    with _um.patch.object(_urlreq, "urlopen", _fake_urlopen):
        with pytest.warns(RuntimeWarning, match="deck_dir is unset"):
            prs = _bp(
                nodes,
                _minimal_tokens(),
                image_provider=provider,
                deck_dir=None,
            )

    # Build still produces a picture shape (tempdir fallback works).
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shapes = list(prs.slides[0].shapes)
    assert shapes and shapes[0].shape_type == MSO_SHAPE_TYPE.PICTURE


def test_picture_query_label_used_as_slot_id(tmp_path, tiny_png):
    """When the picture node carries a quoted label, that label becomes the
    slot id (overriding the query-derived slug)."""
    import json

    hit = ImageHit(
        url=f"file://{tiny_png}", license="L", attribution="A",
        width=10, height=10, mime="image/png",
    )
    provider = MagicMock(spec=ImageProvider)
    provider.name = "fakeprov"
    provider.search.return_value = [hit]

    dsl = (
        'canvas 1920x1080\n'
        'theme test\n'
        'picture 100,100 200x200 query:"any" "hero_image"'
    )
    _build(dsl, deck_dir=tmp_path, provider=provider)
    lock = json.loads((tmp_path / "asset_lock.json").read_text())
    assert "hero_image" in lock["slots"]
