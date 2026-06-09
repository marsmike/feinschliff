---
name: feinklang-smoke
description: Phase-0 smoke test — verifies the feinklang CLI is callable as a bare command from a dependent plugin.
---

# feinklang cross-plugin smoke test

This plugin declares `feinklang` as a dependency. Enabling it should make
Claude Code auto-install and auto-enable `feinklang`, putting its `feinklang`
launcher on PATH. That proves the load-bearing coupling model of the
feinschmiede split: **share capabilities across plugins (CLIs), never files.**

Run, as bare commands (no path, no `cd`):

```bash
command -v feinklang        # should print a path
feinklang --version         # should print "feinklang <version>"
feinklang voices            # lists voices (with ELEVENLABS_API_KEY) or a clean key-missing error
```

If `command -v feinklang` resolves and `feinklang --version` runs, the
`dependencies → auto-install → PATH → CLI call` chain works. A "key missing"
error from `voices` still counts as success for this PATH/auto-install check —
it only tests the wiring, not the API call.
