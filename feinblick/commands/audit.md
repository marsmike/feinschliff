---
name: audit
description: "Gate a repo on newly introduced findings. Usage: /audit [--changed-since <ref>]"
user_invocable: true
---

# /audit

Run the gated audit and emit machine-readable findings:

```bash
feinblick audit --changed-since origin/main --format json
```
