# feinschmiede (Phase 0 — scratch marketplace)

Fine-grained, branded media plugins for Claude Code. The load-bearing idea:
**plugins share *capabilities* (each other's CLIs), never *files* (paths).** A
plugin's `bin/` CLI is on PATH whenever it's enabled, and `dependencies` in
`plugin.json` guarantee a needed plugin is installed + enabled — so one plugin
calls another's CLI as a bare command, which survives plugin boundaries the way
`${CLAUDE_PLUGIN_ROOT}/skills/<other>/…` file paths cannot.

This directory is the **Phase 0 proof-of-concept** from
`2026-06-09-feinschmiede-plugin-split-{spec,plan}`. It contains:

- **`feinklang/`** — audio voiceover (ElevenLabs TTS) as a clean Python package
  exposing the `feinklang` CLI. Zero engine dependency, so it isolates the
  plugin/CLI/venv plumbing from the engine-distribution risk. The
  `bin/feinklang` launcher bootstraps a self-contained venv from bundled wheels
  on first run — the reusable template for the whole family.
- **`feinklang-consumer/`** — a throwaway plugin that `dependencies: ["feinklang"]`
  and calls `feinklang` as a bare command, to prove the cross-plugin chain.

## Local test (the Phase 0 gate)

```bash
# 1. Build the offline wheelhouse (once, or whenever the package changes).
cd feinklang && ./build-wheels.sh && cd ..

# 2. Add this directory as a local marketplace, then install feinklang.
#    (Run these inside Claude Code.)
#    /plugin marketplace add /absolute/path/to/feinschmiede
#    /plugin install feinklang@feinschmiede

# 3. From a fresh install, the bare command works (audio with a key, else a
#    clean "key missing" error):
feinklang tts --text "hello" --out /tmp/x.mp3

# 4. Cross-plugin: install the consumer; feinklang auto-installs + enables and
#    its command resolves on PATH:
#    /plugin install feinklang-consumer@feinschmiede
#    /feinklang-smoke
```

`ELEVENLABS_API_KEY` (export or a line in `~/.env`) is needed for real audio;
without it the CLI prints a clear key-missing error, which is enough to verify
the plugin/CLI/venv wiring.

## Notes

- **Wheels are gitignored** and rebuilt by `build-wheels.sh`; the binary
  dependency (`charset-normalizer`) is vendored both as the build-machine ABI
  wheel and as its pure-python fallback, so the wheelhouse still installs under
  a different interpreter. Phase 3 (PyPI via Trusted Publishing) replaces
  vendoring with `uv pip install <pkg>==<pinned>`.
- This `feinschmiede/` tree is a scratch marketplace living inside the
  feinschliff repo for the POC; the full repo move to a `feinschmiede`
  marketplace root is a later phase.
- **Cross-plugin dependency gate (step 4) caveat.** Claude Code's `dependencies`
  auto-install resolves robustly via **git-backed** marketplace sources with
  version tags. Adding this marketplace by a local *uncommitted* path may not
  auto-resolve `feinklang-consumer`'s dependency on `feinklang`. If
  `/feinklang-smoke` shows `feinklang` did **not** auto-install, first
  `git add` (and ideally tag) `feinschmiede/` so the source has a resolvable
  ref, or install `feinklang` explicitly — the PATH/CLI half of the gate still
  holds regardless. The launcher/venv mechanism (steps 1–3) is the make-or-break
  risk Phase 0 set out to prove, and it is verified independently of this.
