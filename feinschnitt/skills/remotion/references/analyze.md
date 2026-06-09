# Phase 0: Analyze — Video to Storyboard

Reverse-engineer any video into a structured `.storyboard.md` with scene breakdowns, visual descriptions, audio transcripts, color palettes, and keyframe thumbnails.

Based on [iopho-team/iopho-skills](https://github.com/iopho-team/iopho-skills) (MIT).

## Prerequisites

Requires `google-generativeai`, `ffmpeg`, and `GEMINI_API_KEY`. Get a key at https://aistudio.google.com/apikey.

## Usage

```bash
feinschnitt analyze path/to/video.mp4
feinschnitt analyze path/to/video.mp4 --no-frames          # faster, text only
feinschnitt analyze path/to/video.mp4 docs/reference.storyboard.md  # custom output
feinschnitt analyze path/to/video.mp4 --model gemini-2.5-flash      # alt model
```

## Output

Produces a `.storyboard.md` (YAML frontmatter + per-scene markdown) and a `frames/` directory with keyframe images. For the full format spec and field mapping, see [output-format.md](output-format.md).

## Pipeline Integration

Use as Phase 0 before creating your own video:

1. Find reference videos (YouTube search, competitor research)
2. Download with `yt-dlp`
3. Analyze with this to get `.storyboard.md`
4. Use as blueprint in Phase 1 (storyboard phase)
