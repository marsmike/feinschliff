"""Tests for the built-in :mod:`lib.providers.unsplash` reference impl.

Mirrors :mod:`tests.test_image_provider` for registry isolation. Mocks
``urllib.request.urlopen`` (the implementation deliberately avoids
``requests`` to keep the OSS dep list lean — see plan §Task 3).
"""
from __future__ import annotations

import io
import json
import socket
import urllib.error
import warnings
from unittest.mock import MagicMock, patch

import pytest

from lib import image_provider
from lib.image_provider import ImageHit


@pytest.fixture(autouse=True)
def _isolate_registry(monkeypatch):
    """Each test sees a fresh, empty registry so registrations don't leak."""
    monkeypatch.setattr(image_provider, "_REGISTRY", {})
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


@pytest.fixture(autouse=True)
def _no_unsplash_env(monkeypatch):
    """Strip ``UNSPLASH_ACCESS_KEY`` from the env so tests are deterministic."""
    monkeypatch.delenv("UNSPLASH_ACCESS_KEY", raising=False)
    yield


@pytest.fixture(autouse=True)
def _reset_stub_warning(monkeypatch):
    """Reset the module-level "warned once" flag so each test starts fresh."""
    # Import here so the module exists for the patch — the test of the
    # module's mere import side-effects must still see a virgin registry.
    from lib.providers import unsplash as unsplash_mod

    monkeypatch.setattr(unsplash_mod, "_STUB_WARNED", False)
    yield


# Sample Unsplash search response (trimmed to what we parse).
_FIXTURE_RESPONSE = {
    "total": 1,
    "total_pages": 1,
    "results": [
        {
            "id": "abc123",
            "width": 4000,
            "height": 3000,
            "urls": {
                "raw": "https://images.unsplash.com/photo-1?raw",
                "full": "https://images.unsplash.com/photo-1?full",
                "regular": "https://images.unsplash.com/photo-1?w=1080",
                "small": "https://images.unsplash.com/photo-1?w=400",
                "thumb": "https://images.unsplash.com/photo-1?w=200",
            },
            "user": {"name": "Jane Doe", "username": "jdoe"},
            "alt_description": "a sunny kitchen",
        }
    ],
}


def _fake_response(payload: dict, status: int = 200):
    """Build a fake ``urlopen`` context-manager return."""
    body = json.dumps(payload).encode("utf-8")
    fake = MagicMock()
    fake.read.return_value = body
    fake.status = status
    fake.getcode.return_value = status
    # urlopen returns a context manager.
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm


# ---------------------------------------------------------------------------
# Stub-mode behaviour (no access key).
# ---------------------------------------------------------------------------


def test_instantiation_without_key_is_stub():
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({})
    assert p._stub is True
    assert p.access_key is None


def test_instantiation_with_env_key_is_not_stub(monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "env-key-xyz")
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({})
    assert p._stub is False
    assert p.access_key == "env-key-xyz"


def test_instantiation_with_config_key_is_not_stub():
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "config-key-abc"})
    assert p._stub is False
    assert p.access_key == "config-key-abc"


def test_config_key_takes_precedence_over_env(monkeypatch):
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "env-key-xyz")
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "config-wins"})
    assert p.access_key == "config-wins"


def test_stub_search_returns_empty_and_warns_once():
    from lib.providers.unsplash import UnsplashProvider

    p1 = UnsplashProvider({})
    p2 = UnsplashProvider({})

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result1 = p1.search("kitchen")
        result2 = p2.search("garden")
        result3 = p1.search("again")

    assert result1 == []
    assert result2 == []
    assert result3 == []

    # Exactly one warning across the process, regardless of how many
    # instances / search calls happen.
    unsplash_warnings = [
        w for w in captured
        if "UNSPLASH_ACCESS_KEY" in str(w.message) or "stub" in str(w.message).lower()
    ]
    assert len(unsplash_warnings) == 1, (
        f"expected exactly 1 stub warning, got {len(unsplash_warnings)}: "
        f"{[str(w.message) for w in captured]}"
    )


# ---------------------------------------------------------------------------
# Live mode — successful HTTP request.
# ---------------------------------------------------------------------------


def test_search_with_key_returns_parsed_image_hit():
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "test-key"})

    with patch("lib.providers.unsplash.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _fake_response(_FIXTURE_RESPONSE)
        hits = p.search("sunny kitchen", count=1)

    assert len(hits) == 1
    hit = hits[0]
    assert isinstance(hit, ImageHit)
    assert hit.url == "https://images.unsplash.com/photo-1?w=1080"
    assert hit.license == "Unsplash License"
    assert hit.attribution == "Jane Doe on Unsplash"
    assert hit.width == 4000
    assert hit.height == 3000
    assert hit.mime == "image/jpeg"

    # The request was made to the right URL with the auth header.
    assert mock_urlopen.call_count == 1
    req = mock_urlopen.call_args[0][0]
    # urlopen was called with a Request object.
    assert "api.unsplash.com/search/photos" in req.full_url
    assert "query=sunny+kitchen" in req.full_url or "query=sunny%20kitchen" in req.full_url
    assert "per_page=1" in req.full_url
    assert req.get_header("Authorization") == "Client-ID test-key"


def test_search_handles_empty_results():
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "test-key"})

    with patch("lib.providers.unsplash.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _fake_response({"results": [], "total": 0})
        hits = p.search("nothing-matches")

    assert hits == []


# ---------------------------------------------------------------------------
# Transient failure paths — 429 / 5xx, timeout, URLError.
# ---------------------------------------------------------------------------


def test_search_retries_then_gives_up_on_429():
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "test-key"})

    # 429 raises HTTPError in urllib.
    err = urllib.error.HTTPError(
        url="https://api.unsplash.com/search/photos",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=io.BytesIO(b""),
    )

    with patch("lib.providers.unsplash.urlopen", side_effect=err) as mock_urlopen, \
            patch("lib.providers.unsplash.time.sleep") as mock_sleep:
        hits = p.search("kitchen")

    assert hits == []
    # Single retry → 2 total calls.
    assert mock_urlopen.call_count == 2
    # Backoff sleep was hit at least once between attempts.
    assert mock_sleep.call_count >= 1


def test_search_retries_then_gives_up_on_500():
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "test-key"})
    err = urllib.error.HTTPError(
        url="https://api.unsplash.com/search/photos",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=io.BytesIO(b""),
    )

    with patch("lib.providers.unsplash.urlopen", side_effect=err) as mock_urlopen, \
            patch("lib.providers.unsplash.time.sleep"):
        hits = p.search("kitchen")

    assert hits == []
    assert mock_urlopen.call_count == 2


def test_search_does_not_retry_on_401():
    """4xx that isn't 429 is a permanent auth/config error — don't retry."""
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "bad-key"})
    err = urllib.error.HTTPError(
        url="https://api.unsplash.com/search/photos",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b""),
    )

    with patch("lib.providers.unsplash.urlopen", side_effect=err) as mock_urlopen, \
            patch("lib.providers.unsplash.time.sleep"):
        hits = p.search("kitchen")

    assert hits == []
    # Permanent error → single attempt, no retry.
    assert mock_urlopen.call_count == 1


def test_search_handles_socket_timeout():
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "test-key"})

    with patch(
        "lib.providers.unsplash.urlopen",
        side_effect=socket.timeout("timed out"),
    ) as mock_urlopen, \
            patch("lib.providers.unsplash.time.sleep"):
        hits = p.search("kitchen")

    assert hits == []
    # Timeout is transient → one retry.
    assert mock_urlopen.call_count == 2


def test_search_handles_url_error():
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "test-key"})

    with patch(
        "lib.providers.unsplash.urlopen",
        side_effect=urllib.error.URLError("network unreachable"),
    ) as mock_urlopen, \
            patch("lib.providers.unsplash.time.sleep"):
        hits = p.search("kitchen")

    assert hits == []
    assert mock_urlopen.call_count == 2


def test_search_retry_then_success():
    """Transient failure → backoff → success on second attempt."""
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "test-key"})

    err = urllib.error.HTTPError(
        url="https://api.unsplash.com/search/photos",
        code=502,
        msg="Bad Gateway",
        hdrs=None,
        fp=io.BytesIO(b""),
    )

    side_effects = [err, _fake_response(_FIXTURE_RESPONSE)]
    with patch("lib.providers.unsplash.urlopen", side_effect=side_effects) as mock_urlopen, \
            patch("lib.providers.unsplash.time.sleep"):
        hits = p.search("kitchen")

    assert len(hits) == 1
    assert hits[0].url == "https://images.unsplash.com/photo-1?w=1080"
    assert mock_urlopen.call_count == 2


def test_search_handles_malformed_json():
    """Server returned 200 but the body isn't valid JSON — degrade gracefully."""
    from lib.providers.unsplash import UnsplashProvider

    p = UnsplashProvider({"access_key": "test-key"})

    fake = MagicMock()
    fake.read.return_value = b"<html>not json</html>"
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch("lib.providers.unsplash.urlopen", return_value=cm), \
            patch("lib.providers.unsplash.time.sleep"):
        hits = p.search("kitchen")

    assert hits == []


# ---------------------------------------------------------------------------
# Self-registration via the package import.
# ---------------------------------------------------------------------------


def test_unsplash_self_registers_via_package_import(monkeypatch):
    """Importing :mod:`lib.providers` should register the built-in."""
    # Drop the package out of sys.modules so the import re-executes
    # against the freshly emptied registry from the autouse fixture.
    import sys
    for mod_name in list(sys.modules):
        if mod_name == "lib.providers" or mod_name.startswith("lib.providers."):
            sys.modules.pop(mod_name, None)

    import lib.providers  # noqa: F401 — side-effect import

    assert "unsplash" in image_provider._REGISTRY
    instance = image_provider.get_provider("unsplash", {})
    from lib.providers.unsplash import UnsplashProvider

    assert isinstance(instance, UnsplashProvider)


def test_discover_providers_finds_bundled_unsplash(monkeypatch, tmp_path):
    """``discover_providers()`` must surface the bundled built-in.

    We restore the real bundled-root helper so the scan walks
    ``lib/providers/`` for real. The other roots stay neutered by the
    autouse fixture.
    """
    # Restore the real bundled root.
    from pathlib import Path

    real_bundled = Path(image_provider.__file__).resolve().parent / "providers"
    monkeypatch.setattr(image_provider, "_bundled_providers_root", lambda: real_bundled)

    # Drop any cached imports of lib.providers.* so the side-effect
    # import inside discover_providers re-executes.
    import sys
    for mod_name in list(sys.modules):
        if mod_name.startswith("feinschliff_providers._auto") and "unsplash" in mod_name:
            sys.modules.pop(mod_name, None)

    image_provider.discover_providers()

    assert "unsplash" in image_provider._REGISTRY
