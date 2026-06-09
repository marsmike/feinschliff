"""feinklang command-line interface.

Subcommands:
  tts     — synthesize speech from text (ElevenLabs)
  voices  — list / search available voices

This CLI *is* the public surface of the feinklang plugin. Other plugins call
it as a bare command (it is on PATH whenever feinklang is enabled); they never
reach into feinklang's files. That CLI-as-capability coupling is what lets the
feinschmiede family survive plugin boundaries.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from . import __version__, client
from .env import load_home_env

API_KEY_HELP = "Get your API key from: https://elevenlabs.io/app/settings/api-keys"

# Best-effort local players, in preference order (macOS afplay first, then
# common Linux options). Used only when --play is passed.
_PLAYERS = [
    ["afplay"],
    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
    ["mpv", "--really-quiet"],
    ["play", "-q"],
    ["paplay"],
    ["aplay", "-q"],
]


def _require_api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        print("Error: ELEVENLABS_API_KEY environment variable is not set.", file=sys.stderr)
        print(API_KEY_HELP, file=sys.stderr)
        raise SystemExit(1)
    return key


def _maybe_play(path: Path) -> None:
    for player in _PLAYERS:
        if shutil.which(player[0]):
            print("Playing audio...", file=sys.stderr)
            try:
                subprocess.run([*player, str(path)], check=False)
            except OSError:
                continue
            return
    print("(no local audio player found; skipping playback)", file=sys.stderr)


def _cmd_tts(args: argparse.Namespace) -> int:
    if not args.text:
        print("Error: 'text' must not be empty.", file=sys.stderr)
        return 1
    key = _require_api_key()
    voice_id = client.resolve_voice(args.voice_id)
    if args.out:
        out_path = Path(args.out)
    else:
        ext = client.ext_for_format(args.format)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path(tempfile.gettempdir()) / f"tts_{stamp}.{ext}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = client.text_to_speech(
        api_key=key,
        text=args.text,
        voice_id=voice_id,
        model_id=args.model_id,
        output_format=args.format,
        stability=args.stability,
        similarity_boost=args.similarity_boost,
        speed=args.speed,
        out_path=out_path,
    )
    print(f"Generated: {out_path} ({n} bytes)")
    print(f"Voice: {voice_id} | Model: {args.model_id} | Format: {args.format}")
    if args.play:
        _maybe_play(out_path)
    return 0


def _cmd_voices(args: argparse.Namespace) -> int:
    key = _require_api_key()
    voices = client.list_voices(api_key=key, category=args.category, search=args.search)
    for cat, name, vid in voices:
        print(f"[{cat}] {name} → {vid}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="feinklang",
        description="ElevenLabs voiceover CLI (feinschmiede / feinklang).",
    )
    parser.add_argument("--version", action="version", version=f"feinklang {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("tts", help="Synthesize speech from text.")
    t.add_argument("--text", required=True, help="Text to convert to speech.")
    t.add_argument(
        "--out",
        "--output",
        dest="out",
        help="Output file path (default: a timestamped file in the temp dir).",
    )
    t.add_argument(
        "--voice-id",
        "--voice",
        dest="voice_id",
        default=None,
        help="Voice ID or name (Hale, Mike, Lea). Default: Hale.",
    )
    t.add_argument(
        "--model-id",
        "--model",
        dest="model_id",
        default="eleven_multilingual_v2",
        help="Model: eleven_multilingual_v2 (default), eleven_v3, eleven_flash_v2_5.",
    )
    t.add_argument(
        "--format",
        dest="format",
        default="mp3_44100_128",
        help="Output format, e.g. mp3_44100_128 (default), wav_44100, opus_48000_64.",
    )
    t.add_argument("--stability", type=float, default=0.5, help="Voice stability 0-1 (default 0.5).")
    t.add_argument(
        "--similarity-boost",
        dest="similarity_boost",
        type=float,
        default=0.75,
        help="Voice similarity 0-1 (default 0.75).",
    )
    t.add_argument("--speed", type=float, default=1.0, help="Speech rate 0.7-1.2 (default 1.0).")
    t.add_argument("--play", action="store_true", help="Play audio locally after generation.")
    t.set_defaults(func=_cmd_tts)

    v = sub.add_parser("voices", help="List or search available voices.")
    # --category and --search map to mutually exclusive query params upstream;
    # surface the conflict instead of silently dropping one.
    vfilter = v.add_mutually_exclusive_group()
    vfilter.add_argument("--category", help="Filter by category (cloned, professional, premade).")
    vfilter.add_argument("--search", help="Search voices by name.")
    v.set_defaults(func=_cmd_voices)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_home_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except client.ElevenLabsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        # File-write failures and network errors (requests' exceptions subclass
        # OSError) surface as a clean message, never a traceback.
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
