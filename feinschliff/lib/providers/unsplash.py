"""Built-in reference image provider — Unsplash.

Provides build-time picture resolution against
``https://api.unsplash.com/search/photos`` for brand packs that declare
``$image_provider: {kind: "unsplash"}`` in their ``tokens.json``.

Design notes
------------

* **No new dep.** Uses :mod:`urllib.request` rather than ``requests`` so
  the OSS dep list stays lean. Parsing is straight :func:`json.loads`.
* **Stub mode is the default.** Without ``UNSPLASH_ACCESS_KEY`` in the
  environment (or an ``access_key`` in config), :meth:`search` returns
  ``[]`` and emits a single :func:`warnings.warn` on the first call so
  OSS users without a key are not blocked from building. The flag is
  captured at construction time and immutable thereafter.
* **Transient-failure retry.** A single retry covers 429 / 5xx and
  network errors (``socket.timeout`` / :class:`urllib.error.URLError`).
  Permanent 4xx (401, 403, 404, …) gets a single attempt — retrying
  won't help. 30s total wall budget split as ``timeout=14`` per attempt
  plus a short backoff sleep between (14 + 1 + 14 = 29s worst case).
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import warnings
from typing import Any
from urllib.request import Request, urlopen

from lib.image_provider import ImageHit, ImageProvider, register_provider

# Endpoint + timing knobs.
_ENDPOINT = "https://api.unsplash.com/search/photos"
# Two-attempt budget: 14 + 1 (backoff) + 14 = 29s, within the 30s
# total-budget commitment in the spec.
_PER_ATTEMPT_TIMEOUT_S = 14
_BACKOFF_S = 1.0
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Module-level "warned once per process" flag. Stub-mode search emits a
# single warning regardless of how many UnsplashProvider instances exist
# or how often search() is called.
_STUB_WARNED: bool = False


@register_provider
class UnsplashProvider(ImageProvider):
    """Resolve build-time picture queries via the Unsplash search API."""

    name = "unsplash"

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        # Config key wins over env; both empty → stub mode.
        cfg_key = self.config.get("access_key")
        env_key = os.environ.get("UNSPLASH_ACCESS_KEY")
        self.access_key: str | None = cfg_key or env_key or None
        # Cached at construction; `_stub` is effectively immutable for
        # the lifetime of the instance.
        self._stub: bool = not self.access_key

    # -- Public API ------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        count: int = 1,
        hints: dict | None = None,  # noqa: ARG002 — reserved for future use
    ) -> list[ImageHit]:
        if self._stub:
            _warn_stub_once()
            return []

        url = self._build_url(query, count)
        payload = self._fetch_with_retry(url)
        if payload is None:
            return []
        return _parse_results(payload)

    # -- Internals -------------------------------------------------------

    def _build_url(self, query: str, count: int) -> str:
        params = urllib.parse.urlencode({"query": query, "per_page": max(1, int(count))})
        return f"{_ENDPOINT}?{params}"

    def _fetch_with_retry(self, url: str) -> dict[str, Any] | None:
        """Fetch + parse JSON, with a single retry on transient failure.

        Returns the parsed JSON payload, or ``None`` on permanent /
        exhausted failure. Never raises — picture-emit's contract with
        the provider is "return ``[]`` on miss, never throw at the
        caller".
        """
        attempt = 0
        last_error: BaseException | None = None
        while attempt < 2:
            try:
                req = Request(
                    url,
                    headers={
                        "Authorization": f"Client-ID {self.access_key}",
                        "Accept-Version": "v1",
                        "User-Agent": "feinschliff-image-provider/0.1",
                    },
                )
                with urlopen(req, timeout=_PER_ATTEMPT_TIMEOUT_S) as resp:
                    body = resp.read()
                try:
                    return json.loads(body)
                except (ValueError, json.JSONDecodeError) as exc:
                    # Body wasn't JSON. Treat as a non-retryable parse
                    # failure — Unsplash doesn't recover from this on a
                    # second try, and we'd just burn budget.
                    last_error = exc
                    break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in _RETRYABLE_STATUS and attempt == 0:
                    attempt += 1
                    time.sleep(_BACKOFF_S)
                    continue
                # Permanent failure (401, 403, 404, …) or retry already
                # used — give up.
                break
            except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
                # Network-layer failure — retry once.
                last_error = exc
                if attempt == 0:
                    attempt += 1
                    time.sleep(_BACKOFF_S)
                    continue
                break
            except Exception as exc:  # noqa: BLE001 — defensive net
                # Anything else (bug, encoding error, …) — give up
                # rather than burn budget on a likely-permanent issue.
                last_error = exc
                break

        # All paths land here on failure. Emit a single warning so the
        # operator notices but the build continues.
        if last_error is not None:
            warnings.warn(
                f"unsplash search failed after {attempt + 1} attempt(s): "
                f"{type(last_error).__name__}: {last_error}",
                RuntimeWarning,
                stacklevel=2,
            )
        return None


def _warn_stub_once() -> None:
    """Emit the "no key configured" warning at most once per process."""
    global _STUB_WARNED
    if _STUB_WARNED:
        return
    _STUB_WARNED = True
    warnings.warn(
        "UNSPLASH_ACCESS_KEY is not set (and no access_key in $image_provider "
        "config); UnsplashProvider is running in stub mode and search() will "
        "return no hits. Set UNSPLASH_ACCESS_KEY to enable live lookups.",
        RuntimeWarning,
        stacklevel=2,
    )


def _parse_results(payload: dict[str, Any]) -> list[ImageHit]:
    """Map an Unsplash search JSON payload to a list of :class:`ImageHit`."""
    results = payload.get("results") or []
    out: list[ImageHit] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        urls = row.get("urls") or {}
        regular = urls.get("regular") or urls.get("full") or urls.get("small")
        if not regular:
            continue
        user = row.get("user") or {}
        author = user.get("name") or user.get("username") or "Unknown"
        width = row.get("width")
        height = row.get("height")
        out.append(
            ImageHit(
                url=regular,
                license="Unsplash License",
                attribution=f"{author} on Unsplash",
                width=int(width) if isinstance(width, int) else None,
                height=int(height) if isinstance(height, int) else None,
                # ``image/jpeg`` is a best-effort hint — the ``urls.regular``
                # endpoint carries ``?fm=jpg`` so jpeg is the typical body,
                # but Unsplash may content-negotiate to webp / avif. The
                # ``_materialise`` step in ``lib/dsl/pptx_emit`` re-types
                # the cache file from the response's ``Content-Type`` at
                # download time, so this hint is non-authoritative.
                mime="image/jpeg",
            )
        )
    return out


__all__ = ["UnsplashProvider"]
