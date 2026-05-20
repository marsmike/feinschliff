"""Tests for the pluggable image-provider framework.

Mirrors the discovery pattern used in :mod:`tests.test_brand_discovery`:
the discovery helpers are monkeypatched so each test pins exactly which
search paths are visible, and ``FEINSCHLIFF_PROVIDER_PATH`` stages fake
plugin directories under ``tmp_path``.
"""
from __future__ import annotations

import dataclasses
import os
import textwrap

import pytest

from lib.io import image_provider
from lib.io.image_provider import (
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
            from lib.io.image_provider import ImageProvider, register_provider

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
            from lib.io.image_provider import ImageProvider, register_provider

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


def test_discover_broken_plugin_emits_runtime_warning(tmp_path, monkeypatch):
    """A broken plugin must surface as a ``RuntimeWarning`` so operators
    see a visible signal in addition to the ``pipeline_log.log_event``
    record (which is a no-op when ``deck_dir is None`` — i.e. exactly
    during discovery). Without this warning, a broken plugin vanishes
    and later resurfaces as a confusing "unknown provider" KeyError far
    from the underlying cause.
    """
    plugin_root = tmp_path / "providers_warn"
    plugin_root.mkdir()
    (plugin_root / "broken.py").write_text(
        "raise ImportError('synthetic warn-probe failure')\n"
    )
    monkeypatch.setenv("FEINSCHLIFF_PROVIDER_PATH", str(plugin_root))

    with pytest.warns(RuntimeWarning, match=r"broken plugin.*broken\.py") as record:
        discover_providers()

    # Exactly one warning for the single broken file.
    matching = [w for w in record.list if issubclass(w.category, RuntimeWarning)]
    assert len(matching) >= 1
    msg = str(matching[0].message)
    # The warning must include enough context to diagnose:
    #   - source tier (env, since we used FEINSCHLIFF_PROVIDER_PATH)
    #   - filesystem path to the broken file
    #   - synthetic module name
    #   - exception repr (type + message)
    assert "source=env" in msg
    assert "broken.py" in msg
    assert "feinschliff_providers._auto" in msg
    assert "ImportError" in msg
    assert "synthetic warn-probe failure" in msg


def test_discover_broken_plugin_does_not_pollute_cwd(tmp_path, monkeypatch):
    """Regression: broken-plugin discovery must NOT write ``timing.jsonl``
    into the current working directory. Previously the discovery loop
    passed ``Path.cwd()`` as ``deck_dir`` and every broken import created
    a stray log in ``$HOME`` (or wherever the user happened to be).
    """
    # Switch cwd to a clean tmp dir so we can assert nothing lands there.
    work_dir = tmp_path / "workdir"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    plugin_root = tmp_path / "providers_nopollute"
    plugin_root.mkdir()
    (plugin_root / "broken.py").write_text(
        "raise ImportError('synthetic failure — timing.jsonl pollution probe')\n"
    )
    monkeypatch.setenv("FEINSCHLIFF_PROVIDER_PATH", str(plugin_root))

    discover_providers()  # must not raise

    # Nothing should have been written into cwd as a side-effect.
    assert not (work_dir / "timing.jsonl").exists(), (
        "broken-plugin discovery created timing.jsonl in cwd; "
        "log_event should no-op when deck_dir is None"
    )
    # And nothing in the plugin root either.
    assert not (plugin_root / "timing.jsonl").exists()


def test_plugin_label_disambiguates_same_named_roots(tmp_path, monkeypatch):
    """Two provider roots with the same directory name but different
    absolute parents must produce distinct synthetic module names, so a
    same-stem ``*.py`` in each one does not alias in ``sys.modules``.

    The previous label ignored the parent path, so e.g. ``/a/providers/``
    and ``/b/providers/`` both yielded ``..._auto.providers_<stem>`` —
    the second ``exec_module`` clobbered the first, and any duplicate
    ``name`` collision in ``register_provider`` got swallowed.
    """
    root_a = tmp_path / "alpha" / "providers"
    root_b = tmp_path / "beta" / "providers"
    root_a.mkdir(parents=True)
    root_b.mkdir(parents=True)

    # Same file stem in each root, but they register under DIFFERENT
    # provider names — both should land in the registry.
    (root_a / "shared.py").write_text(
        textwrap.dedent(
            """
            from lib.io.image_provider import ImageProvider, register_provider

            @register_provider
            class AlphaProvider(ImageProvider):
                name = "alpha_provider"
                def search(self, query, *, count=1, hints=None):
                    return []
            """
        )
    )
    (root_b / "shared.py").write_text(
        textwrap.dedent(
            """
            from lib.io.image_provider import ImageProvider, register_provider

            @register_provider
            class BetaProvider(ImageProvider):
                name = "beta_provider"
                def search(self, query, *, count=1, hints=None):
                    return []
            """
        )
    )

    monkeypatch.setenv(
        "FEINSCHLIFF_PROVIDER_PATH",
        f"{root_a}{os.pathsep}{root_b}",
    )

    # Labels alone must differ — proves the hash disambiguator works.
    label_a = image_provider._plugin_label_for(root_a)
    label_b = image_provider._plugin_label_for(root_b)
    assert label_a != label_b, (
        f"_plugin_label_for collided: {label_a!r} == {label_b!r}; "
        "two distinct roots must produce distinct synthetic module labels"
    )

    discover_providers()

    assert "alpha_provider" in image_provider._REGISTRY
    assert "beta_provider" in image_provider._REGISTRY
