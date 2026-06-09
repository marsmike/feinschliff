"""Lightweight ``~/.env`` loader (no third-party dependency).

Mirrors the old ``tts.sh`` / ``voices.sh`` convenience of ``source "$HOME/.env"``
so an ``ELEVENLABS_API_KEY`` kept in ``~/.env`` is picked up without exporting
it. Kept dependency-free on purpose — the only runtime wheel we vendor is
``requests``.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_home_env() -> None:
    """Populate ``os.environ`` from ``~/.env`` for keys not already set.

    Parses simple ``KEY=VALUE`` lines (optionally ``export``-prefixed); ignores
    blank lines and ``#`` comments. An explicit environment variable always
    wins — we never override something the caller exported.
    """
    env_path = Path.home() / ".env"
    if not env_path.is_file():
        return
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        # Strip only a matched surrounding quote pair (don't mangle a value that
        # merely starts or ends with a quote).
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
