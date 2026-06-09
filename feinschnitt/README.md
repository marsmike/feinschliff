# feinschnitt — video

Programmatic video for Claude Code: storyboard-driven [Remotion](https://remotion.dev)
production (`/video`) and recipe-driven CLI session recording (`/record`), part
of the **feinschmiede** family. Composes its siblings by their bare CLIs —
storyboard images via `feinbild imagine`, voiceover via `feinklang tts`.

## CLI

The plugin exposes a `feinschnitt` command on PATH (provisioned into a
self-contained venv on first run):

- `feinschnitt record <recipe.toml> [--out-dir D] [--dry-run] [--no-render] [--keep]`
  — drive a CLI session in tmux+asciinema from a recipe, emitting a
  post-processed `.cast` + `.scene-index.json` (+ `.gif`/`.mp4`). Recordings
  land in `${CLAUDE_PROJECT_DIR}/.recordings/<name>/`. Needs `tmux`,
  `asciinema`, and (for rendering) `agg`/`ffmpeg` on PATH.
- `feinschnitt analyze <video> [out.storyboard.md] [--no-frames] [--model M]`
  — reverse-engineer an existing video into a `.storyboard.md` with Gemini.
  Needs `GEMINI_API_KEY` and `ffmpeg`.

## Skills

- `remotion` (`/video`) — storyboard → build → verify video pipeline.
- `cli-recorder` (`/record`) — author a `recipe.toml` for `feinschnitt record`.

## License

MIT. `analyze` (video→storyboard) is adapted from iopho-team/iopho-skills (MIT).
