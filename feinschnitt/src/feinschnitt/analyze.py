#!/usr/bin/env python3
"""
video_to_storyboard.py — Analyze a video with Gemini and produce a .storyboard.md

Ported from iopho-team/iopho-skills (MIT license) and adapted for the Remotion pipeline.

Usage:
    python3 video_to_storyboard.py <video_path> [output_path] [--no-frames] [--model MODEL]
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

genai = None  # lazily imported in run_analyze (keeps `feinschnitt record` dep-free)


class AnalyzeError(RuntimeError):
    """User-facing analyze error (clean message, no traceback)."""


PROMPT = """Analyze this video in detail and produce a complete .storyboard.md document.

Output EXACTLY this structure — YAML frontmatter first, then scene-by-scene markdown:

---
title: "<detected or inferred title>"
duration_seconds: <total>
resolution: "<WxH>"
fps: <detected>
style:
  visual_style: "<e.g. clean, modern, minimalist>"
  color_palette: ["#hex1", "#hex2", "#hex3"]
  typography: "<font style description>"
  mood: "<overall mood>"
audio:
  has_voiceover: <true/false>
  voiceover_language: "<lang>"
  voiceover_tone: "<e.g. friendly, authoritative>"
  has_music: <true/false>
  music_style: "<e.g. upbeat electronic>"
  music_mood: "<e.g. energetic, calm>"
  has_sfx: <true/false>
content:
  type: "<e.g. product_demo, explainer, tutorial>"
  framework: "<e.g. PAS, AIDA, Before-After>"
  key_message: "<one-line summary>"
---

For EACH scene (detect natural cuts/transitions — aim for fine-grained scene detection):

### Scene N: <Title> (<start> – <end>, <duration>s)

#### Visual
- **Shot Type**: <wide / medium / close-up / macro / screen-recording>
- **Camera Movement**: <static / pan-left / pan-right / zoom-in / zoom-out / tracking>
- **Subject**: <what is shown — be specific about elements, positions, sizes>
- **Background**: <background treatment — color, gradient, texture>
- **Text On Screen**: "<exact text visible>"
- **Graphics/Animation**: <describe animations, transitions, particles, effects>
- **Layout**: <describe spatial arrangement — where elements sit in the frame>

#### Audio
- **Voiceover**: "<exact transcript of spoken words>"
- **Music**: <description of music if present>
- **SFX**: <sound effects if present>

#### Analysis
- **Narrative Purpose**: <what this scene accomplishes in the story>
- **Emotional Beat**: <what the viewer should feel>
- **Sales Element**: <problem / agitation / solution / proof / cta / hook / none>
- **Transition Out**: <cut / fade / slide / dissolve> to →

Be extremely detailed. Capture every text element, icon, animation, color change, and audio cue.
Note the color palette used — extract specific hex codes where possible.
Describe layout in terms of screen zones (top, center, bottom) for a vertical/horizontal format.
This storyboard will be used to recreate the video with Remotion."""


def upload_and_wait(path: str, model_name: str):
    print(f"[1/4] Uploading {path} to Gemini File API...")
    f = genai.upload_file(path)
    print(f"  Uploaded: {f.name}, state={f.state.name}")

    while f.state.name == "PROCESSING":
        time.sleep(3)
        f = genai.get_file(f.name)
        print(f"  Processing... state={f.state.name}")

    if f.state.name != "ACTIVE":
        raise RuntimeError(f"File failed to process: {f.state.name}")

    print(f"  Ready: {f.uri}")
    return f


def analyze(file_obj, model_name: str) -> str:
    print(f"[2/4] Analyzing with {model_name}...")
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        [file_obj, PROMPT],
        generation_config={"temperature": 0.2, "max_output_tokens": 8192},
        request_options={"timeout": 300},
    )
    print(f"  Done. ~{len(response.text)} chars")
    return response.text


def extract_frames(video_path: str, storyboard_text: str, frames_dir: Path) -> str:
    """Parse timestamps from storyboard, extract midpoint frames with ffmpeg."""
    print("[3/4] Extracting keyframes...")
    frames_dir.mkdir(exist_ok=True)

    pattern = re.compile(r"### Scene (\d+):[^\n]*\((\d+):(\d+)\s*[–-]\s*(\d+):(\d+)")
    scenes = pattern.findall(storyboard_text)

    inserted = storyboard_text
    for scene_num, m1, s1, m2, s2 in scenes:
        t1 = int(m1) * 60 + int(s1)
        t2 = int(m2) * 60 + int(s2)
        midpoint = (t1 + t2) / 2

        frame_file = frames_dir / f"scene-{int(scene_num):03d}.jpg"
        cmd = [
            "ffmpeg", "-ss", str(midpoint), "-i", video_path,
            "-frames:v", "1", "-q:v", "3", str(frame_file),
            "-y", "-loglevel", "error"
        ]
        subprocess.run(cmd, check=False)

        if frame_file.exists():
            print(f"  scene-{int(scene_num):03d}.jpg @ {midpoint:.1f}s")
            thumb_ref = f"\n**Thumbnail**: ![scene-{int(scene_num):03d}](./frames/scene-{int(scene_num):03d}.jpg)\n"
            header_pat = re.compile(
                rf"(### Scene {scene_num}:[^\n]*\n)", re.MULTILINE
            )
            inserted = header_pat.sub(r"\1" + thumb_ref, inserted, count=1)

    print(f"  {len(scenes)} frames extracted")
    return inserted


def run_analyze(args) -> int:
    # Validate inputs BEFORE importing the heavy Gemini SDK, so a missing key or
    # missing video yields a clean error even when google-generativeai is absent.
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AnalyzeError("GEMINI_API_KEY not set in ~/.env")

    video_path = args.video_path
    if not Path(video_path).exists():
        raise AnalyzeError(f"video not found: {video_path}")

    global genai
    import google.generativeai as genai
    genai.configure(api_key=api_key)

    out_path = (
        Path(args.output_path) if args.output_path
        else Path(video_path).with_suffix(".storyboard.md")
    )
    frames_dir = out_path.parent / "frames"

    file_obj = upload_and_wait(video_path, args.model)
    try:
        text = analyze(file_obj, args.model)
    finally:
        try:
            genai.delete_file(file_obj.name)
        except Exception:
            pass

    if not args.no_frames:
        text = extract_frames(video_path, text, frames_dir)

    print(f"[4/4] Writing {out_path}...")
    out_path.write_text(text, encoding="utf-8")

    scene_count = len(re.findall(r"^### Scene", text, re.MULTILINE))
    print(f"\n✓ Done → {out_path}")
    print(f"  Scenes detected: {scene_count}")
    print(f"  Output size: {len(text)} chars")
    return 0


def add_parser(sub) -> None:
    ap = sub.add_parser("analyze",
                        help="Analyze a video with Gemini and emit a .storyboard.md.")
    ap.add_argument("video_path", help="path to the input video file")
    ap.add_argument("output_path", nargs="?", default=None,
                    help="output .storyboard.md (default: <video>.storyboard.md)")
    ap.add_argument("--no-frames", action="store_true",
                    help="skip ffmpeg midpoint-frame extraction")
    ap.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
                    help="Gemini model (default: gemini-2.0-flash)")
    ap.set_defaults(func=run_analyze)
