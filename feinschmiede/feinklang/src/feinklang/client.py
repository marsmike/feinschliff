"""Minimal ElevenLabs API client (text-to-speech + voice listing).

Ported from the original ``tts.sh`` / ``voices.sh`` shell scripts: same
endpoints, same default voice (Hale), same parameter surface — but using
``requests`` instead of shelling out to ``curl`` + ``jq``.
"""

from __future__ import annotations

import requests

API_BASE = "https://api.elevenlabs.io"
DEFAULT_VOICE_ID = "wWWn96OtTHu1sn8SRGEr"  # Hale

# Named voices for convenience (case-insensitive), mirroring tts.sh.
NAMED_VOICES = {
    "hale": "wWWn96OtTHu1sn8SRGEr",
    "mike": "mxqV8Q77peldUYcdIgb0",
    "lea": "M39iqBUcu1jyiwM5PfSy",
}

# Output-format prefix -> file extension (matches tts.sh's case table).
_EXT_BY_PREFIX = {"mp3": "mp3", "wav": "wav", "pcm": "pcm", "opus": "ogg"}


class ElevenLabsError(RuntimeError):
    """API or usage error; the CLI prints the message to stderr and exits 1."""


def resolve_voice(voice: str | None) -> str:
    """Map a voice name (Hale/Mike/Lea, any case) to its ID; pass IDs through."""
    if not voice:
        return DEFAULT_VOICE_ID
    return NAMED_VOICES.get(voice.lower(), voice)


def ext_for_format(output_format: str) -> str:
    """Return the file extension implied by an ElevenLabs ``output_format``."""
    prefix = output_format.split("_", 1)[0]
    return _EXT_BY_PREFIX.get(prefix, "mp3")


def text_to_speech(
    *,
    api_key: str,
    text: str,
    voice_id: str,
    model_id: str = "eleven_multilingual_v2",
    output_format: str = "mp3_44100_128",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    speed: float = 1.0,
    out_path,
) -> int:
    """Synthesize ``text`` and write the audio bytes to ``out_path``.

    ``voice_id`` is expected to be already resolved (see :func:`resolve_voice`).
    Returns the number of bytes written. Raises :class:`ElevenLabsError` on a
    non-200 response.
    """
    url = f"{API_BASE}/v1/text-to-speech/{voice_id}"
    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "speed": speed,
        },
    }
    resp = requests.post(
        url,
        params={"output_format": output_format},
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=120,
    )
    if resp.status_code != 200:
        raise ElevenLabsError(f"API returned HTTP {resp.status_code}\n{resp.text.strip()}")
    data = resp.content
    out_path.write_bytes(data)
    return len(data)


def list_voices(*, api_key: str, category: str | None = None, search: str | None = None):
    """Return ``[(category, name, voice_id), ...]`` for the account's voices."""
    params: dict[str, object] = {"page_size": 50}
    if search:
        params["search"] = search
    elif category:
        params["category"] = category
    resp = requests.get(
        f"{API_BASE}/v2/voices",
        params=params,
        headers={"xi-api-key": api_key},
        timeout=60,
    )
    if resp.status_code != 200:
        raise ElevenLabsError(f"API returned HTTP {resp.status_code}\n{resp.text.strip()}")
    voices = resp.json().get("voices", [])
    return [
        (v.get("category", "?"), v.get("name", "?"), v.get("voice_id", "?"))
        for v in voices
    ]
