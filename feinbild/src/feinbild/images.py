"""AI image generation — Replicate + Gemini providers (ported from imagine.sh).

`requests` instead of curl/jq; same endpoints, defaults, and output behavior.
Diagnostic lines go to stderr; the machine-readable result line goes to stdout.
No Unsplash provider exists; an absent UNSPLASH_ACCESS_KEY costs nothing.
"""

from __future__ import annotations

import base64
import tempfile
from datetime import datetime
from pathlib import Path

import requests


def _default_out(ext: str) -> Path:
    """Timestamped default output path (matches imagine.sh: no silent overwrite)."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(tempfile.gettempdir()) / f"imagine_{stamp}.{ext}"

_DEFAULT_MODEL = {"replicate": "black-forest-labs/flux-schnell", "gemini": "gemini-2.5-flash-image"}


class ImagineError(RuntimeError):
    """Usage/API error; the CLI prints it to stderr and exits 1."""


def default_model(provider: str) -> str:
    try:
        return _DEFAULT_MODEL[provider]
    except KeyError:
        raise ImagineError(f"Unknown provider '{provider}'. Use: replicate, gemini")


def _replicate_format(model: str) -> str:
    return "png" if any(t in model for t in ("kontext", "fill", "redux")) else "webp"


def generate(*, prompt: str, provider: str, model: str | None, aspect_ratio: str, out_path: Path | None, api_keys: dict) -> Path:
    if provider not in _DEFAULT_MODEL:
        raise ImagineError(f"Unknown provider '{provider}'. Use: replicate, gemini")
    model = model or default_model(provider)
    if provider == "replicate":
        return _replicate(prompt, model, aspect_ratio, out_path, api_keys.get("REPLICATE_API_KEY"))
    return _gemini(prompt, model, aspect_ratio, out_path, api_keys.get("GEMINI_API_KEY"))


def _replicate(prompt, model, aspect_ratio, out_path, key) -> Path:
    if not key:
        raise ImagineError("REPLICATE_API_KEY not set in ~/.env")
    fmt = _replicate_format(model)
    resp = requests.post(
        f"https://api.replicate.com/v1/models/{model}/predictions",
        headers={"Prefer": "wait", "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"input": {"prompt": prompt, "aspect_ratio": aspect_ratio, "output_format": fmt, "go_fast": True}},
        timeout=300,
    )
    data = resp.json()
    if data.get("status") != "succeeded":
        raise ImagineError(f"Replicate returned status '{data.get('status', 'unknown')}': {data.get('error') or data.get('detail') or data}")
    output = data.get("output")
    url = output[0] if isinstance(output, list) else output
    if not url:
        raise ImagineError("No image URL in Replicate response")
    out = out_path or _default_out(fmt)
    out.parent.mkdir(parents=True, exist_ok=True)
    img = requests.get(url, timeout=120)
    img.raise_for_status()  # a 403/404 on an expired signed URL must not be written as the "image"
    out.write_bytes(img.content)
    return out


def _gemini(prompt, model, aspect_ratio, out_path, key) -> Path:
    if not key:
        raise ImagineError("GEMINI_API_KEY not set in ~/.env")
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect_ratio}},
        },
        timeout=300,
    )
    data = resp.json()
    if data.get("error", {}).get("message"):
        raise ImagineError(f"Gemini API: {data['error']['message']}")
    b64 = None
    # `candidates` can be present-but-empty ([]) on a safety block — guard the
    # [0] access; read inlineData defensively (a partial part may lack "data").
    for part in (data.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData")
        if inline and inline.get("data"):
            b64 = inline["data"]
            break
    if not b64:
        raise ImagineError("No image data in Gemini response")
    out = out_path or _default_out("png")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(b64))
    return out
