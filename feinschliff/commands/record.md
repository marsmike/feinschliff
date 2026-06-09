---
name: record
description: "Author a CLI session recording recipe (cli-recorder). Usage: /record <what to record>"
user_invocable: true
---

# /record

Author a `recipe.toml` for recording a CLI session, using the `cli-recorder` skill.

## Instructions

1. Treat the user's input as the recording intent (e.g. "a tour of git rebase -i").
2. Engage the `cli-recorder` skill and walk through its interactive recipe-authoring Q&A.
3. Stop after the recipe is written and validated — the user runs `train_recorder.py` themselves.
4. If nothing is provided, ask what CLI session they want to record.
