---
name: feinklang-smoke
description: "Run the feinschmiede Phase-0 cross-plugin smoke test."
user_invocable: true
---

# /feinklang-smoke

Verify the `dependencies → auto-install → PATH → bare-CLI` chain. Run:

```bash
command -v feinklang && feinklang --version && feinklang voices
```

Report whether `feinklang` resolved on PATH and ran. A "key missing" error
from `feinklang voices` still counts as success for the PATH / auto-install
check.
