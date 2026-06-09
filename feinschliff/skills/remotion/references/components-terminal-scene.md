# TerminalScene — embed real CLI recordings as React-composited scenes

`TerminalScene` renders an asciicast v3 recording (produced by the `cli-recorder` plugin) as a frame-accurate React-composited terminal — not a video clip embedded in a frame, but actual cells the Remotion compositor can zoom, highlight, transition, and audio-sync.

## When to use

Use `TerminalScene` when:

- The video needs to demo a real CLI session (Claude Code, `kubectl`, `npm install`, `git rebase -i`, an SSH session). The recording contains actual command output, not faked-by-Typewriter text.
- You want to layer Remotion effects (zooms, captions, chapter markers, audio sync) over terminal content.
- You want chapter-relative trimming — render only step `ask` through step `compact` of a longer recording.

Use the existing `Typewriter` / `CodeBlock` components when:

- You're animating a *fake* terminal (illustrative, not a real session).
- Determinism matters more than fidelity to a real run.

## Inputs

| Input | What | Source |
|-------|------|--------|
| `castUrl` | Path/URL to a `.cast` file (asciicast v3) | Produced by `cli-recorder/scripts/train_recorder.py` |
| `sceneIndexUrl` | Path/URL to the `.scene-index.json` sidecar | Produced alongside the .cast |
| `startStep` / `endStep` | Step IDs from the recipe | Used to trim playback to a chapter |

The recipe's step IDs (`discover`, `inspect`, `ask`, …) become first-class navigation primitives. A `terminal_recording` storyboard scene that renders steps `ask` through `code` is one prop away.

## Dependencies

Add to your Remotion project:

```bash
npm install @xterm/headless
```

`@xterm/headless` is the same VT/ANSI parser as `xterm.js`, but without the DOM renderer. We feed it the cast events; it builds an in-memory cell grid; we read cells and render React.

## Files in this reference

- [`official/assets/terminal-scene.tsx`](official/assets/terminal-scene.tsx) — the React component
- [`official/assets/use-terminal-state.ts`](official/assets/use-terminal-state.ts) — the hook (cast → cell grid for time `t`)

Copy both into your Remotion project's `src/components/` (or wherever your component layer lives).

## Usage

### Minimal — play a full recording back

```tsx
import {TerminalScene} from '../components/TerminalScene';
import {staticFile} from 'remotion';

export const MyTerminalScene: React.FC = () => (
  <TerminalScene
    castUrl={staticFile('recordings/claude-commands.cast')}
  />
);
```

`useCurrentFrame()` inside the component drives playback automatically — composition frame `f` shows the terminal state at `t = f / fps` seconds.

### Trimmed — render only one chapter

```tsx
<TerminalScene
  castUrl={staticFile('recordings/claude-commands.cast')}
  sceneIndexUrl={staticFile('recordings/claude-commands.scene-index.json')}
  startStep="ask"
  endStep="compact"
/>
```

Playback begins at `step.ask.start_s` and freezes at `step.compact.end_s`. Useful when the storyboard breaks one recording into multiple scenes.

### With zoom + highlight (cinematic pass)

```tsx
<TerminalScene
  castUrl={staticFile('recordings/claude-commands.cast')}
  zoom={{scale: 1.6, row: 5, col: 0}}              // zoom into upper-left region
  highlight={{fromRow: 5, toRow: 8, fromCol: 0, toCol: 100}}  // emphasise rows 5-8
/>
```

### Combined with TitleSlide / Sequence

```tsx
<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={90}>
    <TitleSlide title="Discover the commands" />
  </TransitionSeries.Sequence>
  <TransitionSeries.Transition presentation={fade()} timing={linearTiming({durationInFrames: 15})} />
  <TransitionSeries.Sequence durationInFrames={fps * 12}>
    <TerminalScene
      castUrl={staticFile('recordings/claude-commands.cast')}
      startStep="discover"
      endStep="discover"
    />
  </TransitionSeries.Sequence>
</TransitionSeries>
```

## Audio sync

The scene-index.json gives you per-step start/end times. To narrate per step:

```tsx
const sceneIdx = useMemo(() => loadSceneIndex(staticFile('recordings/claude-commands.scene-index.json')), []);

<>
  <TerminalScene castUrl={staticFile('recordings/claude-commands.cast')} />
  {sceneIdx.steps.map((s) => (
    <Sequence
      key={s.id}
      from={Math.round(s.start_s * fps)}
      durationInFrames={Math.round((s.end_s - s.start_s) * fps)}
    >
      <Audio src={staticFile(`vo/${s.id}.mp3`)} />
    </Sequence>
  ))}
</>
```

The audio phase of the Remotion pipeline can produce one `vo-<step-id>.mp3` per step — labels from the recipe become VO text directly.

## Performance & follow-ups

The skeleton rebuilds the terminal grid by replaying events from t=0 every frame. For a 2-minute recording rendered at 30 fps that's 3,600 replays — fine for short clips, slow for longer ones. The hook has cache hooks (`snapshotCache`, `KEYFRAME_INTERVAL_S`) wired but not yet populating; populating them is M2's tightest follow-up:

1. Snapshot the headless terminal's serialise() output every `KEYFRAME_INTERVAL_S`.
2. For frame at time `t`, find the latest keyframe ≤ `t`, restore from it, replay only the delta.

Other M2 follow-ups (intentionally left for an M2.5 pass):

- **Full 256-colour palette** — currently 8-colour via `PALETTE_8`.
- **Cursor rendering** — read xterm's cursor position, render a blink-clip overlay at that cell.
- **Font loading** — Remotion projects need to call `loadFont()` for JetBrainsMono Nerd Font. Provide a helper in `font-loader.ts`.
- **`useStepCap` / `useStepOffset`** — currently rely on a `globalThis` cache. Wire properly to a context provider that pre-loads scene indexes via `delayRender`.

These are documented inside the TSX/TS files at the relevant call sites.

## Storyboard mapping

The Remotion storyboard schema gains a new scene type that points at a `cli-recorder` recipe:

```yaml
# In docs/STORYBOARD.md scene block
scene 3:
  type: terminal_recording
  recipe: ../recordings/claude-commands/claude-commands.recipe.toml
  span_steps: [ask, code]
  overlay:
    chapter_title: "Live Coding"
    show_step_labels: true
  voiceover:
    sync: per_step
```

See [storyboard.md](storyboard.md) for the full schema, and [build.md](build.md) for how Phase 3 invokes the recorder when artifacts are missing or stale.
