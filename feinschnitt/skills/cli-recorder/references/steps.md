# CLI Recorder — per-step procedure

The full detail behind the 7-step process in `SKILL.md`. Apply one question at
a time; prefer multiple choice over open-ended.

## Step 1 — Discover intent

Three things to nail down before writing anything:

- **The CLI** — exact binary that gets recorded (`claude`, `bash`, `kubectl`, `vim`).
- **Audience** — beginner discovering the tool? expert checking a workflow?
- **Takeaway** — one sentence the viewer should leave with. This becomes the recipe's `title` and shapes step labels.

Don't dump these as a bulleted list. Have an actual conversation: "What CLI are we recording?" → user answers → "Who's the viewer?" → answer → "And the one thing they should walk away knowing?".

## Step 2 — Profile

Map the CLI to one of the bundled profiles:

| Profile           | Use for                                                    |
|-------------------|------------------------------------------------------------|
| `claude-code`     | `claude` CLI specifically                                  |
| `generic`         | bash, zsh, npm, git, docker, kubectl, brew, curl, …        |
| `interactive-tui` | vim, less, htop, k9s, lazygit, fzf — anything that owns the screen |

Default to `generic` unless the CLI obviously fits another profile. If unsure, ask the user.

## Step 3 — Sketch the steps

Aim for **3–9 beats**. Fewer than 3 is a screenshot; more than 9 is a course module.

Each beat needs:

- **`id`** (lowercase, kebab/snake-case) — stable identifier for the scene index. Prefer semantic IDs (`discover`, `install`, `verify`) over positional ones (`step1`, `step2`).
- **`label`** (sentence case, < 50 chars) — becomes a chapter marker / VO beat title in the resulting video.
- **`action`** — `type_prompt` covers ~80% of beats. The others are `send_key`, `wait_for_pattern`, `pause`.

Sketch the labels first, before any `text` content. The labels are the storyboard; the `text` is the implementation. If a label can't be reduced to a clean sentence, that beat is doing too much — split it.

## Step 4 — Resolve interactive bits

Walk through the sketched beats and ask:

- For each `type_prompt` step targeting a known modal command (Claude `/help`, `/status`, `/cost`; vim `:help`; etc.), confirm `dismiss_key = "Escape"` (or `q`, `:q`, etc.). The `claude-code` profile auto-fills this for the listed modal commands; for other CLIs, the recipe is responsible.
- If a step waits for a password prompt or interactive confirmation, use `wait_for_pattern` with the regex.
- If you need a beat of "nothing happening" so the viewer can absorb output, insert a `pause` step with `duration = 2.0`.

## Step 5 — Tune cadence

Defaults from the profile are fine for almost everything. Only override when:

- **Typing feels rushed/sluggish.** Default `typing_wpm = 125`. Bump to 160 for "expert" feel; drop to 90 for "deliberate teaching".
- **Idle compression too aggressive.** Default `idle_speedup = 4.0`. Drop to 2.0 if Claude's response generation is itself the lesson and you want viewers to *feel* the pause.
- **Idle gaps still too long after compression.** Drop `idle_time_limit` from 2.5 to 1.0 — caps any single pause to 1s in the cast metadata.

## Step 6 — Write the recipe

Save to `${CLAUDE_PROJECT_DIR}/.recordings/recipes/<name>.recipe.toml`. File naming: short, kebab-case, descriptive (`install-kubectl`, `claude-commands-tour`, `git-rebase-i-walkthrough`). The stem becomes the output directory name.

Required structure:

```toml
[recording]
title       = "..."         # human-readable, stored in cast metadata
command     = "..."         # binary to spawn in tmux
profile     = "..."         # claude-code | generic | interactive-tui
# (other fields inherit from the profile; override here only if needed)

[[step]]
id          = "..."
label       = "..."
action      = "type_prompt"
text        = "..."
# dismiss_key only if needed
```

Validate against `${CLAUDE_PLUGIN_ROOT}/skills/cli-recorder/schema/recipe.schema.json` before declaring done.

## Step 7 — Show + offer dry-run

Read the written file back to the user. Then suggest:

```bash
feinschnitt record ${CLAUDE_PROJECT_DIR}/.recordings/recipes/<name>.recipe.toml --dry-run
```

The dry-run parses the recipe, applies the profile, and prints each resolved step. The user can tweak before recording for real.

**Stop here.** Do not run the recorder. Do not start a Remotion video. Hand off to the user.

## Anti-patterns

- **Asking 4 questions at once.** Always one at a time.
- **Writing the recipe before agreeing on labels.** Labels = storyboard; the rest is mechanics.
- **Defaulting to `text` content first.** Sketch labels, *then* fill the text.
- **Ignoring profiles.** "Just use generic for everything" loses the auto-dismiss for Claude modals, etc.
- **Modeling >9 beats in one recipe.** That's a course, not a clip. Suggest splitting into chapter recipes.
- **Auto-running the recorder.** Hard gate: stop after writing the file.

## Examples of good labels

✓ `"Discover commands with /help"`
✓ `"Inspect session state"`
✓ `"Ask a real question"`
✓ `"Install kubectl via Homebrew"`
✓ `"Verify the install with kubectl version"`

✗ `"Step 3"` (positional)
✗ `"Type the slash help command and then press escape to close the dialog"` (run-on)
✗ `"Show stuff"` (uninformative)
