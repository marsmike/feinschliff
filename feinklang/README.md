# feinklang

Audio voiceover for Claude Code — ElevenLabs text-to-speech behind a clean
`feinklang` CLI. Part of the [feinschmiede](../README.md) family.

```bash
feinklang tts --text "Hello, world." --out voiceover.mp3
feinklang voices --search Mike
```

Requires `ELEVENLABS_API_KEY` (export or a line in `~/.env`). Default voice:
**Hale**. See `skills/tts/references/parameters.md` for the full flag surface.

## Install

```bash
/plugin marketplace add marsmike/feinschliff   # once per machine
/plugin install feinklang@feinschmiede
```

## How it's packaged

- `src/feinklang/` — the Python package (`[project.scripts] feinklang =
  feinklang.cli:main`), a `requests`-based ElevenLabs client. No `curl`, no
  `jq`, no file-path coupling to other plugins.
- `bin/feinklang` — launcher: on first run it provisions a venv in
  `${CLAUDE_PLUGIN_DATA}/venv` from the bundled `wheels/` (offline), then execs
  the CLI. On PATH whenever the plugin is enabled.
- `wheels/` — offline wheelhouse (gitignored); rebuild with `./build-wheels.sh`.
- `skills/tts/`, `commands/tts.md` — document the **CLI**; no internal paths.

## Rebuild the wheelhouse

```bash
./build-wheels.sh   # builds feinklang's wheel + vendors requests' wheel closure
```

## Porting notes (vs the original `tts.sh` / `voices.sh`)

The CLI preserves the original parameter surface; two behaviors are
intentionally **broadened** (supersets — they don't break any prior usage):

- **Voice-name resolution is case-insensitive** for all named voices
  (`Hale`/`hale`, `Mike`/`mike`, `Lea`/`lea`), where the shell script matched
  only the exact `mike`/`Mike` and `lea`/`Lea` spellings.
- **`--play` works cross-platform** (tries `afplay`, then `ffplay`/`mpv`/
  `play`/`paplay`/`aplay`), not just macOS `afplay`, and is not restricted to
  mp3/wav.

`feinklang voices` takes `--category` and `--search` as **mutually exclusive**
flags (the API treats them as one filter), so passing both is a clear error
rather than a silent drop.
