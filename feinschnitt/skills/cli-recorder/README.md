# cli-recorder

Drive any CLI session in tmux+asciinema, capture it as an asciicast v3 with a structured scene-index sidecar. Use the artifacts standalone (docs, support tickets, demos) or as input to the Remotion `TerminalScene` component for full educational videos.

## Quick start

```bash
# 1. Author a recipe (interactive — uses the cli-recorder skill)
claude
> /record install-kubectl

# 2. Run the recorder
python3 scripts/train_recorder.py recipes/install-kubectl.recipe.toml

# 3. Outputs land in recordings/<name>/
recordings/install-kubectl/
├── install-kubectl.cast              # asciicast v3, post-processed (idle compressed)
├── install-kubectl.scene-index.json  # step → time-window map
└── install-kubectl.gif               # rendered preview (if agg installed)
```

## Recipe format

A recipe describes a CLI session as a sequence of human-style steps. See [schema/recipe.schema.json](schema/recipe.schema.json) for the full schema and [profiles/](profiles/) for ready-made defaults per CLI family.

```toml
[recording]
title       = "Claude Code: Commands & Settings Tour"
command     = "claude"
profile     = "claude-code"

[[step]]
id          = "discover"
label       = "Discover commands with /help"
action      = "type_prompt"
text        = "/help"
dismiss_key = "Escape"

[[step]]
id          = "ask"
label       = "Ask about slash commands"
action      = "type_prompt"
text        = "what are the 3 most important slash commands a new Claude Code user should know?"
```

## Step actions

| Action            | Purpose                                                                              |
|-------------------|--------------------------------------------------------------------------------------|
| `type_prompt`     | Type `text` character-by-character at `typing_wpm`, send Enter, wait for Claude idle |
| `send_key`        | Send a single named key (`Escape`, `Tab`, `Ctrl+C`)                                  |
| `wait_for_pattern`| Block until a regex appears in the pane (e.g. password prompt)                       |
| `pause`           | Sleep N seconds (mid-recording beats / breathing room)                               |

## Profiles

Profiles preset everything that's CLI-specific:

- **`claude-code`** — Claude Code (modal dialog dismiss=Escape, idle compression, Nerd Font cols/rows)
- **`generic`** — plain shell (`bash`, `zsh`, npm/git/docker/kubectl)
- **`interactive-tui`** — vim, less, htop (TUIs that own the screen)

Per-recipe overrides are merged on top of the profile.

## Outputs

For each run the recorder writes:

- **`<name>.cast`** — asciicast v3, post-processed (cursor artifacts stripped, idle gaps compressed).
- **`<name>.scene-index.json`** — `{recipe, cast, duration_s, fps_hint, steps:[{id,label,start_s,end_s,type}...]}`. Consumed by Remotion's `TerminalScene` for chapter markers, audio sync, zoom focal points.
- **`<name>.gif`** / **`<name>.mp4`** — rendered preview (only if `agg`/`ffmpeg` are on PATH).

## Pairing with Remotion

The Remotion plugin's `TerminalScene` component reads `.cast` directly via `@xterm/headless` and renders it as composited React text — so all Remotion features (zoom, highlight, transitions, narration) work natively on terminal recordings. See [`components-extended.md`](../remotion/references/components-extended.md) for the integration.

## See also

- [schema/recipe.schema.json](schema/recipe.schema.json) — recipe validation
- [SKILL.md](SKILL.md) — interactive recipe authoring
