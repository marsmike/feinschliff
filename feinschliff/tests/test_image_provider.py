"""Tests for the pluggable image-provider framework.

Mirrors the discovery pattern used in :mod:`tests.test_brand_discovery`:
the discovery helpers are monkeypatched so each test pins exactly which
search paths are visible, and ``FEINSCHLIFF_PROVIDER_PATH`` stages fake
plugin directories under ``tmp_path``.
"""
from __future__ import annotations

import dataclasses
import textwrap

import pytest

from lib import image_provider
from lib.image_provider import (
    ImageHit,
    ImageProvider,
    discover_providers,
    get_provider,
    register_provider,
)


@pytest.fixture(autouse=True)
def _isolate_registry(monkeypatch):
    """Each test sees a fresh, empty registry so registrations don't leak."""
    monkeypatch.setattr(image_provider, "_REGISTRY", {})
    # Reset discovery memoisation so each test re-scans its own staged tree.
    monkeypatch.setattr(image_provider, "_DISCOVERED", False)
    yield


@pytest.fixture(autouse=True)
def _silence_default_paths(monkeypatch, tmp_path):
    """Block real plugin / user / cwd-dev paths from leaking into tests."""
    monkeypatch.setattr(image_provider, "_bundled_providers_root", lambda: tmp_path / "no-bundled")
    monkeypatch.setattr(image_provider, "_user_providers_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr(image_provider, "_plugin_providers_roots", lambda: [])
    monkeypatch.setattr(image_provider, "_cwd_dev_providers_roots", lambda: [])
    monkeypatch.delenv("FEINSCHLIFF_PROVIDER_PATH", raising=False)
    yield


class _DummyProvider(ImageProvider):
    """Trivial provider used by the registry tests."""
    name = "dummy"

    def search(self, query, *, count=1, hints=None):
        return []


def test_register_provider_decorator_round_trip():
    register_provider(_DummyProvider)
    assert image_provider._REGISTRY["dummy"] is _DummyProvider

    instance = get_provider("dummy")
    assert isinstance(instance, _DummyProvider)


def test_register_provider_duplicate_raises_value_error():
    register_provider(_DummyProvider)

    class _Other(ImageProvider):
        name = "dummy"  # collides with above

        def search(self, query, *, count=1, hints=None):
            return []

    with pytest.raises(ValueError) as exc:
        register_provider(_Other)
    assert "dummy" in str(exc.value)


def test_get_provider_unknown_lists_all_registered_names():
    class _A(ImageProvider):
        name = "alpha"

        def search(self, query, *, count=1, hints=None):
            return []

    class _B(ImageProvider):
        name = "bravo"

        def search(self, query, *, count=1, hints=None):
            return []

    register_provider(_A)
    register_provider(_B)

    with pytest.raises(KeyError) as exc:
        get_provider("nope", {})
    msg = str(exc.value)
    assert "nope" in msg
    assert "alpha" in msg
    assert "bravo" in msg


def test_image_hit_is_frozen():
    hit = ImageHit(
        url="https://example.com/x.jpg",
        license="Test License",
        attribution="Test Author",
        width=100,
        height=200,
        mime="image/jpeg",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        hit.url = "https://example.com/y.jpg"  # type: ignore[misc]


def test_discover_providers_is_idempotent(tmp_path, monkeypatch):
    plugin_root = tmp_path / "providers_a"
    plugin_root.mkdir()
    (plugin_root / "good.py").write_text(
        textwrap.dedent(
            """
            from lib.image_provider import ImageProvider, register_provider

            @register_provider
            class GoodProvider(ImageProvider):
                name = "good"
                def search(self, query, *, count=1, hints=None):
                    return []
            """
        )
    )
    monkeypatch.setenv("FEINSCHLIFF_PROVIDER_PATH", str(plugin_root))

    discover_providers()
    size_after_first = len(image_provider._REGISTRY)
    assert "good" in image_provider._REGISTRY

    discover_providers()
    size_after_second = len(image_provider._REGISTRY)

    assert size_after_first == size_after_second == 1


def test_discover_providers_skips_broken_plugins_and_logs(tmp_path, monkeypatch, caplog):
    plugin_root = tmp_path / "providers_b"
    plugin_root.mkdir()
    # A broken module — raises ImportError at import time.
    (plugin_root / "broken.py").write_text(
        "raise ImportError('synthetic failure for test')\n"
    )
    # A good module alongside it — must still load.
    (plugin_root / "fine.py").write_text(
        textwrap.dedent(
            """
            from lib.image_provider import ImageProvider, register_provider

            @register_provider
            class FineProvider(ImageProvider):
                name = "fine"
                def search(self, query, *, count=1, hints=None):
                    return []
            """
        )
    )
    monkeypatch.setenv("FEINSCHLIFF_PROVIDER_PATH", str(plugin_root))

    # Capture warnings emitted by pipeline_log.log_event so the test
    # can assert a record landed somewhere observable. log_event writes
    # to a JSONL file under deck_dir, so we patch it to capture calls.
    captured: list[dict] = []
    import lib.pipeline_log as pl

    def _fake_log_event(deck_dir, phase, status, *, elapsed_ms=None, **extra):
        captured.append({"phase": phase, "status": status, **extra})
        return {"phase": phase, "status": status, **extra}

    monkeypatch.setattr(pl, "log_event", _fake_log_event)
    # Also patch the import-time-bound symbol inside image_provider, in
    # case the implementation imported the function name directly.
    monkeypatch.setattr(image_provider, "log_event", _fake_log_event, raising=False)

    # Must not raise.
    discover_providers()

    assert "fine" in image_provider._REGISTRY
    assert "broken" not in image_provider._REGISTRY
    # At least one log record references the broken plugin.
    assert any(
        "broken" in str(rec.get("path", "")) or "broken" in str(rec.get("module", ""))
        for rec in captured
    ), f"expected a log record about broken.py, got: {captured}"
