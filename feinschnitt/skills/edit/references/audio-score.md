# Audio Score — edit

Finals get scored; previews never do. Opt out: `--no-score` or
`"score": {"enabled": false}`.

## Music assets

- **Bring your own audio** — nothing ships. Royalty-free ONLY (a Content-ID match
  geo-blocks the upload and kills reach). Place files in
  `~/.local/share/feinschnitt/music/` and `.../sfx/` (env:
  `FEINSCHNITT_MUSIC_DIR` / `FEINSCHNITT_SFX_DIR`); missing assets skip, never fail.
- **Signature track:** `00-<track>.mp3` (alphabetical default); per-plan override:
  `"score": {"music": "other.mp3"}`.

## Cue sheet (auto-generated)

The plan is the cue sheet — never hand-author cues:

- `whoosh.*` on the hook.
- `pop.*` at every takeover entrance.
- `stroke.*` per caption-emphasis chunk — except the LAST emphasis, which stays
  silent (closers want silence).

## Levels

- Bed at −26 LUFS, sidechain-ducked under the untouched voice.
- Swell to ×1.6 ending at the climax (first `quote_pull`, else the last takeover);
  2 s hold, 3 s fall.
- Verify checks that the scored mix stays within −2/+6 dB of the source voice —
  the voice is the reference, never the casualty.
