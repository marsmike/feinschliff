# feinschnitt — video

Programmatic video for Claude Code: storyboard-driven [Remotion](https://remotion.dev)
production (`/video`) and recipe-driven CLI session recording (`/record`), part
of the **feinschmiede** family. Composes its siblings by their bare CLIs —
storyboard images via `feinbild imagine`, voiceover via `feinklang tts`.

## Install

```bash
/plugin marketplace add marsmike/feinschmiede   # once per machine
/plugin install feinschnitt@feinschmiede
```

The Remotion video path (`/video`) requires **Node >= 18** on PATH. The CLI
recording path (`/record`) requires `tmux`, `asciinema` >= 3.0, and optionally
`agg`/`ffmpeg` for rendering. The edit path (`/edit`) requires **ffmpeg** and
**Node >= 18**; install `pip install 'feinschnitt[edit]'` for faster-whisper
(hardware-accelerated transcription).

## CLI

The plugin exposes a `feinschnitt` command on PATH (provisioned into a
self-contained venv on first run):

- `feinschnitt record <recipe.toml> [--out-dir D] [--dry-run] [--no-render] [--keep]`
  — drive a CLI session in tmux+asciinema from a recipe, emitting a
  post-processed `.cast` + `.scene-index.json` (+ `.gif`/`.mp4`). Recordings
  land in `${CLAUDE_PROJECT_DIR}/.recordings/<name>/`. Needs `tmux`,
  `asciinema` >= 3.0 (post-processing requires asciicast v3 delta
  timestamps), and (for rendering) `agg`/`ffmpeg` on PATH.
- `feinschnitt analyze <video> [out.storyboard.md] [--no-frames] [--model M]`
  — reverse-engineer an existing video into a `.storyboard.md` with Gemini.
  Needs `GEMINI_API_KEY` and `ffmpeg`.
- `feinschnitt edit` — plan-driven editing of pre-recorded talking-head footage
  into brand-themed cuts: transcript-aligned overlays, zoom punch-ins,
  preview→final ladder; voice track is untouched. Subcommands:
  `workdir` · `transcribe` · `lint` · `align` · `render` · `verify`.

## Skills

- `remotion` (`/video`) — storyboard → build → verify video pipeline.
- `cli-recorder` (`/record`) — author a `recipe.toml` for `feinschnitt record`.
- `edit` (`/edit`) — edit plan → brand-themed cut of talking-head footage.

## License

MIT. `analyze` (video→storyboard) is adapted from iopho-team/iopho-skills (MIT).
