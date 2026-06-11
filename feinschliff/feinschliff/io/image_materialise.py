"""Provider search + asset-lock pinning + HTTP materialisation for picture
``query:`` slots.

Extracted from ``feinschliff.dsl.pptx_emit`` (its only consumer) — everything
here is pure IO with no python-pptx / slide dependency:

- stable slot-id derivation from a query string (``_slot_id_from_query``);
- the ``asset_lock.json`` schema: read / atomic write / (de)serialising
  pinned ``ImageHit``s (``_read_lock``, ``_write_lock``, ``_entry_from_hit``,
  ``_hit_from_lock_entry``);
- ``lookup_lock_then_search`` — return the pinned hit for a slot when valid,
  otherwise search the active :class:`~feinschliff.io.image_provider.ImageProvider`
  and pin the first result;
- ``_materialise`` — resolve a hit URL to a local file, downloading
  ``http(s)://`` URLs into a content-addressed cache with retry + backoff;
- the throwaway-tempdir cache registry + atexit cleanup used when the
  emitter has no ``deck_dir`` to cache under.

The emitter accesses these via module-attribute lookups
(``image_materialise._materialise(...)``) so tests can patch a single
canonical location.
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .image_provider import ImageHit, ImageProvider


# ---------------------------------------------------------------------------
# Picture-query helpers (Task 7 — pluggable image provider)
# ---------------------------------------------------------------------------

# Stable slot-id derivation: lowercase, collapse non-alnum to single `_`,
# trim leading/trailing `_`, truncate to 40 chars. Used so re-running a
# build with the same DSL pins the same image again from asset_lock.json.
_SLOT_SLUG_RE = re.compile(r"[^A-Za-z0-9]+")

# MIME → file extension map for materialised cache filenames. Defaults to
# `.bin` for unknown/missing — the renderer falls back to PIL's auto-format
# detection which usually still works.
#
# ``image/jpg`` is the wrong-but-common variant of ``image/jpeg`` — some CDNs
# emit it; tolerating both keeps the extension chain honest.
_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg":  ".jpg",
    "image/png":  ".png",
    "image/webp": ".webp",
    "image/gif":  ".gif",
    "image/avif": ".avif",
    "image/svg+xml": ".svg",
    "image/bmp":  ".bmp",
    "image/tiff": ".tiff",
}

# Image mimes we accept as authoritative when read from a response's
# ``Content-Type`` header at download time (Findings #2 + #3). Provider hits
# carry a best-effort mime hint, but the actual bytes' type is determined
# by what the server returned — trusting Content-Type here kills both the
# Unsplash-hardcoded-mime fragility AND the ``.bin`` fallback risk for
# servers that swap the body's encoding via content negotiation.
_AUTHORITATIVE_IMAGE_MIMES = frozenset(_MIME_TO_EXT)

# HTTP materialise timing knobs — mirror the constants used in
# lib/providers/unsplash.py so the math is comprehensible. Two attempts
# at 14 s each plus a 1 s backoff between = 14 + 1 + 14 = 29 s worst case,
# safely under the 30 s wall budget the spec promises.
_PER_ATTEMPT_TIMEOUT_S = 14
_BACKOFF_S = 1.0


def _pick_ext_from_content_type(content_type: str) -> str:
    """Return a cache-file extension from an HTTP ``Content-Type`` header,
    or ``""`` if the header is missing, unparseable, or names a mime we
    don't recognise as an image.

    The header may carry a ``; charset=…`` or ``; boundary=…`` suffix;
    we strip everything after the first ``;`` and lowercase before
    looking the mime up. Whitespace either side of the mime token is
    tolerated. An empty / non-image / unknown mime returns ``""`` so
    the caller falls back to ``hit.mime`` → URL-path-suffix → ``.bin``.
    """
    if not content_type:
        return ""
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime in _AUTHORITATIVE_IMAGE_MIMES:
        return _MIME_TO_EXT[mime]
    return ""


# Throwaway-cache cleanup (Finding #1).
#
# When ``_emit_picture`` is invoked without ``ctx.deck_dir`` (library-mode
# callers who forgot to wire it) and a ``query:`` slot needs HTTP
# materialise, we fall back to a ``tempfile.mkdtemp`` directory. The
# RuntimeWarning at the call site prompts the operator to fix the wiring,
# but repeated library invocations across a long-running process would
# otherwise leak one tempdir per build.
#
# We register a single ``atexit`` handler the first time the fallback
# fires, and the handler ``shutil.rmtree``s every dir we've created. The
# ``_THROWAWAY_CLEANUP_REGISTERED`` guard ensures we only register once
# even across many fallback invocations.
_THROWAWAY_CACHE_DIRS: list[Path] = []
_THROWAWAY_CLEANUP_REGISTERED = False


def _cleanup_throwaway_caches() -> None:
    """Remove every throwaway cache dir we created during this process.

    Uses ``ignore_errors=True`` because any of these dirs may already have
    been cleaned by another path (a previous explicit teardown, the OS
    wiping ``/tmp``, etc.), and a process-exit handler must never raise.
    """
    for d in _THROWAWAY_CACHE_DIRS:
        shutil.rmtree(d, ignore_errors=True)


def _register_throwaway_cache_cleanup() -> None:
    """Register ``_cleanup_throwaway_caches`` with ``atexit`` exactly once.

    Subsequent calls are no-ops — the cleanup walks the full registry,
    so we don't need a separate atexit entry per dir.
    """
    global _THROWAWAY_CLEANUP_REGISTERED
    if _THROWAWAY_CLEANUP_REGISTERED:
        return
    _THROWAWAY_CLEANUP_REGISTERED = True
    atexit.register(_cleanup_throwaway_caches)


def _slot_id_from_query(query: str) -> str:
    """Derive a stable, deterministic slot id from a query string.

    "Kitchen morning light!" → "kitchen_morning_light".
    Empty/non-alnum-only inputs collapse to "asset" so the lock file
    never gets an empty key.
    """
    slug = _SLOT_SLUG_RE.sub("_", query.lower()).strip("_")
    if not slug:
        slug = "asset"
    return slug[:40]


def _read_lock(deck_dir: Path | None) -> dict:
    """Read ``<deck_dir>/asset_lock.json`` or return a fresh empty lock."""
    if deck_dir is None:
        return {"version": 1, "provider": None, "slots": {}}
    lock_path = deck_dir / "asset_lock.json"
    if not lock_path.is_file():
        return {"version": 1, "provider": None, "slots": {}}
    try:
        data = json.loads(lock_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "provider": None, "slots": {}}
    if not isinstance(data, dict):
        return {"version": 1, "provider": None, "slots": {}}
    data.setdefault("version", 1)
    data.setdefault("provider", None)
    data.setdefault("slots", {})
    return data


def _write_lock(deck_dir: Path | None, lock: dict) -> None:
    """Persist the lock as pretty-printed JSON. No-op if deck_dir is None.

    The write is done via tmp-file + ``os.replace`` so a crashed or
    interrupted build can't leave a half-written ``asset_lock.json`` that
    future runs fail to parse. The tmp file is created in the same
    directory as the lock so the rename is atomic on POSIX (cross-
    filesystem renames aren't atomic).
    """
    if deck_dir is None:
        return
    deck_dir.mkdir(parents=True, exist_ok=True)
    lock_path = deck_dir / "asset_lock.json"
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=lock_path.parent,
        prefix=".asset_lock.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        json.dump(lock, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, lock_path)


def _hit_from_lock_entry(entry: dict) -> "ImageHit | None":
    """Reconstruct an ``ImageHit`` from a lock-file slot dict. Returns None
    if the entry is missing required fields."""
    from .image_provider import ImageHit
    try:
        return ImageHit(
            url=entry["url"],
            license=entry.get("license", ""),
            attribution=entry.get("attribution", ""),
            width=entry.get("width"),
            height=entry.get("height"),
            mime=entry.get("mime", ""),
        )
    except KeyError:
        return None


def _url_is_resolvable(url: str) -> bool:
    """For ``file://`` URLs, verify the path exists on disk. For
    ``http(s)://`` URLs we trust the pin — pre-flighting every HEAD on
    every build would defeat the point of the lock cache."""
    if url.startswith("file://"):
        return Path(url[len("file://"):]).is_file()
    if url.startswith(("http://", "https://")):
        return True
    # Bare path — treat as filesystem; resolvable if it exists.
    return Path(url).is_file()


def _utc_now_iso_seconds() -> str:
    """ISO 8601 timestamp in UTC, truncated to seconds, with `Z` suffix.

    `datetime.now(timezone.utc).isoformat()` produces `+00:00` — we
    replace it with `Z` to match the spec example.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _entry_from_hit(hit: "ImageHit", query: str) -> dict:
    """Serialise an ImageHit + query into a lock-slot dict."""
    entry: dict = {
        "query": query,
        "url": hit.url,
        "license": hit.license,
        "attribution": hit.attribution,
        "mime": hit.mime,
        "pinned_at": _utc_now_iso_seconds(),
    }
    if hit.width is not None:
        entry["width"] = hit.width
    if hit.height is not None:
        entry["height"] = hit.height
    return entry


class _SearchError:
    """Sentinel returned by ``lookup_lock_then_search`` when
    ``provider.search`` raised.

    Distinct from ``None`` (legitimate empty-result miss) so the caller
    can mark the ``missing_assets`` entry as ``kind="search-error"``
    rather than ``kind="no-hit"``. Carries the exception type so the
    caller can surface a useful diagnostic without re-raising.
    """
    __slots__ = ("exc_type",)

    def __init__(self, exc_type: type):
        self.exc_type = exc_type


def lookup_lock_then_search(
    provider: "ImageProvider | None",
    deck_dir: Path | None,
    slot_id: str,
    query: str,
) -> "ImageHit | _SearchError | None":
    """Return a pinned hit for `slot_id` if available + valid; otherwise
    call ``provider.search(query, count=1)``, pin the first result, and
    return it. The lock is read from / written to
    ``<deck_dir>/asset_lock.json``. Returns ``None`` if the provider
    returns ``[]``.
    Returns a ``_SearchError`` sentinel if the provider raises — callers
    differentiate provider-crash from legitimate-no-hit on this signal.

    Failed searches are NOT pinned — a stale "no results" entry would
    block the slot from ever resolving, even after the provider's
    backing data improves.
    """
    assert provider is not None  # caller guards this
    lock = _read_lock(deck_dir)

    # Lock is scoped to a provider name; a brand switch invalidates the
    # whole file (different URL schemes, different licensing).
    if lock.get("provider") == provider.name:
        slot_entry = lock["slots"].get(slot_id)
        if slot_entry and slot_entry.get("query") == query:
            pinned_url = slot_entry.get("url", "")
            if _url_is_resolvable(pinned_url):
                hit = _hit_from_lock_entry(slot_entry)
                if hit is not None:
                    return hit
            # Stale — fall through to re-search and overwrite below.

    # Either no lock entry for this slot, or it's stale, or the lock
    # belongs to a different provider. Re-search.
    try:
        hits = provider.search(query, count=1)
    except Exception as exc:
        # Provider crashed (network, library bug, bad token, …). Surface
        # via warning + sentinel so the caller writes a search-error
        # entry to missing_assets; the build still completes with a
        # placeholder rect so a single bad slot doesn't block delivery.
        warnings.warn(
            f"image provider {provider.name!r} raised on search({query!r}): "
            f"{type(exc).__name__}: {exc}",
            RuntimeWarning,
            stacklevel=3,
        )
        return _SearchError(type(exc))
    if not hits:
        return None
    hit = hits[0]

    # If the lock belongs to a different provider, blow it away rather
    # than mixing pin sources in one file.
    if lock.get("provider") != provider.name:
        lock = {"version": 1, "provider": provider.name, "slots": {}}
    lock["slots"][slot_id] = _entry_from_hit(hit, query)
    lock["provider"] = provider.name
    _write_lock(deck_dir, lock)
    return hit


def _materialise(
    hit: "ImageHit", cache_dir: Path,
) -> tuple[Path | None, Exception | None]:
    """Resolve an ``ImageHit`` URL to a local Path.

    - ``file://`` → just check the file exists.
    - ``http(s)://`` → download to ``<cache_dir>/<sha1(url)>.<ext>`` if
      not already present. Two attempts at ``_PER_ATTEMPT_TIMEOUT_S`` s
      each with a ``_BACKOFF_S`` s pause between (worst case 29 s,
      under the 30 s spec ceiling). Returns ``(None, last_err)`` on
      persistent failure.
    - Bare path → treat as a filesystem path.

    Returns ``(path, None)`` on success and ``(None, err_or_None)`` on
    failure. The second element carries the last exception raised on the
    HTTP path so the caller can include error diagnostics in
    ``missing_assets`` entries; it is ``None`` for non-HTTP misses where
    no exception was involved (e.g. a missing ``file://`` target).

    The sha1+ext naming keeps re-runs cheap: repeated builds against the
    same URL skip the network entirely after the first successful fetch.
    """
    url = hit.url
    if url.startswith("file://"):
        p = Path(url[len("file://"):])
        return (p, None) if p.is_file() else (None, None)
    if url.startswith(("http://", "https://")):
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Pre-compute fallback extension from the hit's mime hint or the URL
        # path. The response's ``Content-Type`` may override this at
        # download time (Findings #2 + #3).
        ext = _MIME_TO_EXT.get(hit.mime.lower(), "")
        if not ext:
            from urllib.parse import urlparse
            url_path = urlparse(url).path
            url_ext = Path(url_path).suffix.lower()
            ext = url_ext if url_ext else ".bin"
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        # Fast-path: a prior run already cached this URL with the
        # fallback extension. Re-use without hitting the network. We
        # deliberately accept a small risk of staleness (Content-Type
        # might have flipped server-side) in exchange for not re-paying
        # the HTTP round trip on every rebuild.
        target = cache_dir / f"{digest}{ext}"
        if target.is_file():
            return (target, None)
        # Two-attempt budget mirrors lib/providers/unsplash.py:
        #   _PER_ATTEMPT_TIMEOUT_S (14) + _BACKOFF_S (1) + _PER_ATTEMPT_TIMEOUT_S (14)
        #   = 29 s worst case, safely under the 30 s spec ceiling.
        # urllib.request.urlretrieve uses the default socket timeout —
        # override per call by passing `timeout=` to urlopen explicitly.
        last_err: Exception | None = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(  # noqa: S310
                    url, timeout=_PER_ATTEMPT_TIMEOUT_S,
                ) as resp:
                    # Trust the response's ``Content-Type`` over ``hit.mime``
                    # when it names a known image mime (Findings #2 + #3).
                    # This protects against servers that content-negotiate
                    # (e.g. Unsplash → webp) and against ``hit.mime`` hints
                    # that were never set authoritatively in the first place.
                    # ``resp.headers`` is always present on a real
                    # ``http.client.HTTPResponse``; ``getattr`` keeps us
                    # safe against test fakes / unusual urlopen returns.
                    response_headers = getattr(resp, "headers", None)
                    response_ct = ""
                    if response_headers is not None:
                        # Both ``email.message.Message`` and ``dict`` support .get.
                        response_ct = response_headers.get("Content-Type", "") or ""
                    ct_ext = _pick_ext_from_content_type(response_ct)
                    if ct_ext:
                        ext = ct_ext
                    data = resp.read()
                # Re-derive target after the Content-Type override.
                target = cache_dir / f"{digest}{ext}"
                if target.is_file():
                    # Another build raced ahead and cached this URL with
                    # the same extension — re-use rather than re-write.
                    return (target, None)
                target.write_bytes(data)
                return (target, None)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_err = exc
                # Backoff only between attempts, never after the last.
                if attempt == 0:
                    time.sleep(_BACKOFF_S)
                continue
        return (None, last_err)
    # Bare path fallback.
    p = Path(url)
    return (p, None) if p.is_file() else (None, None)
