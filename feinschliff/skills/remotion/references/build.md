
# Remotion Build

Implement video compositions from storyboard + timing manifest. Every scene and beat gets built, visually verified, and audio-synced before final render.

## Prerequisites

Before starting, you should have:
- `docs/STORYBOARD.md` — Production storyboard with beat sheet (from remotion-storyboard)
- `src/timing.ts` — Frame-accurate timing manifest (from remotion-audio)
- `public/vo-beat*.mp3` — Per-beat voiceover audio files (from remotion-audio)
- `docs/storyboard/scene-*-composition.png` — AI-generated concept images (from remotion-storyboard) — use as visual targets

### Draft Mode (No Audio)

If audio files are not yet available, proceed in draft mode:

1. Estimate beat durations from VO script: **average 150 words/minute = 2.5 words/second**
2. Calculate frames: `estimatedFrames = Math.ceil((wordCount / 2.5) * fps)`
3. Create a placeholder `src/timing.ts` with estimated values and `draft: true` flag
4. Build all scenes visually — the feedback loop works without audio
5. Use silent `<Sequence>` blocks with estimated durations

When audio becomes available later:
1. Regenerate `src/timing.ts` with real `ffprobe` measurements
2. Re-check beat boundary alignment
3. Add `<Audio>` elements to each sequence
4. Final render with audio

This enables visual iteration while voiceover is being produced or reviewed.

## Process

### Step 1: Project Setup

**Preferred: Manual setup** (the `npx create-video@latest` command requires interactive input and cannot be automated):

```bash
mkdir my-video && cd my-video
npm init -y
npm install remotion @remotion/cli @remotion/google-fonts @remotion/transitions
npm install @remotion/layout-utils @remotion/media-utils react react-dom
npm install -D @types/react
```

Create `src/index.ts` and `src/Root.tsx` manually (see component implementation below).

**Alternative:** If running interactively, `npx create-video@latest` works but requires template selection.

After setup, set up the [CLAUDE.md template](claude-md-template.md) for the project.

### Step 2: Design System

Create `src/theme.ts` with design tokens. Choose a theme appropriate to the content:

**Dark theme** (tech, dev tools, coding):
```typescript
export const theme = {
  bg: "#0a0a0f",
  surface: "#1a1a24",
  surfaceBorder: "#2a3a2a",
  green: "#a3e635",
  purple: "#8b5cf6",
  pink: "#f472b6",
  cyan: "#67e8f9",
  orange: "#fb923c",
  text: "#e0e0e0",
  muted: "#888898",
  // ...fonts, radius, padding
} as const;
```

**Light theme** (consumer products, lifestyle, clean/friendly):
```typescript
export const theme = {
  bg: "#f8fafc",
  surface: "#ffffff",
  surfaceBorder: "#e2e8f0",
  accent: "#00a3e0",
  green: "#22c55e",
  orange: "#f97316",
  red: "#ef4444",
  text: "#1e293b",
  muted: "#64748b",
  // ...fonts, radius, padding
} as const;
```

Always load fonts via `@remotion/google-fonts` with explicit weights/subsets.

For the full design token reference — including typography scale, spacing scale, color palette with semantic colors and tint patterns, safe zones for both 16:9 and 9:16, the constants-first pattern, and font pairing presets — see [design-system.md](design-system.md). Always use named tokens from the design system. Never use raw pixel values for padding, font sizes, or gaps.

Read [color-script-rules.md](color-script-rules.md) to plan the color script before implementing scenes. Follow the color plan algorithm to assign dominant/secondary/accent colors per scene.

### YouTube Shorts Sizing Guide

For 1080x1920 (9:16 vertical), widgets must be large enough to read on a phone:

| Element | Minimum Size |
|---------|-------------|
| Body text | 26-32px |
| Headers/commands | 44-56px |
| Progress bars | 32-36px height |
| Card padding | 18-24px |
| Emojis | 44-100px |
| Badges/pills | 28-36px font, 14-22px padding |
| Gaps between cards | 16-20px |
| Edge margins | 50-60px left/right |

**Rule of thumb:** If you can't read it at 0.4x scale in a still frame, it's too small.

### Step 3: Component Implementation (Parallel Per-Scene)

Read [motion-design-rules.md](motion-design-rules.md) for timing, easing, and animation rules. ALL build agents must use the 4 named spring presets (smooth/snappy/bouncy/heavy) — do not invent custom spring configs.

**Dispatch one Agent per scene in parallel.** Each scene is independent — no shared state between Scene0.tsx and Scene3.tsx. Use the Agent tool to spawn sub-agents simultaneously.

Each agent receives:
- The scene's section from `docs/STORYBOARD.md` (Visual, Audio, Analysis, Components)
- The scene's concept images from `docs/storyboard/` as visual targets
- `src/theme.ts` and `src/timing.ts` for design tokens and frame ranges
- Reference to [scene-templates.md](scene-templates.md) — customize an existing template rather than building from scratch
- Reference to [components.md](components.md), [patterns.md](patterns.md), [animation-hooks.md](animation-hooks.md)

Each agent writes one file: `src/scenes/Scene[N].tsx`

```
Agent "build-scene-0": Read Scene 0 spec + concept images → write Scene0.tsx
Agent "build-scene-1": Read Scene 1 spec + concept images → write Scene1.tsx
Agent "build-scene-2": Read Scene 2 spec + concept images → write Scene2.tsx
...all dispatched in a single message with multiple Agent tool calls
```

After all agents complete, create `src/scenes/MainVideo.tsx` that sequences all scenes with `<Sequence>` + `<Audio>` per beat.

### Step 4: Visual Feedback Loop (Parallel Per-Scene)

**Dispatch one verification Agent per scene in parallel.** Each agent independently renders, inspects, and fixes its scene.

Each verification agent:
1. **Render** 3 key frames (start, middle, end) — `npx remotion still src/index.ts Scene[N] frame.png --frame=[F] --scale=0.5`
2. **Inspect** — Read each PNG with vision, compare against concept images from `docs/storyboard/`
3. **Fix** — Edit `Scene[N].tsx` to resolve layout issues (overlap, spacing, alignment, colors)
4. **Re-render** — Verify the fix, repeat until the scene passes

```
Agent "verify-scene-0": Render Scene0 stills → inspect → fix → re-render
Agent "verify-scene-1": Render Scene1 stills → inspect → fix → re-render
...all dispatched in parallel
```

**Rules:**
- Always render after significant layout changes — don't code blind
- Check at least 3 key frames per scene: start, middle, end
- Use `--scale=0.5` for fast iteration, `--scale=1` for final check
- If text overlaps or overflows, fix before proceeding

### Step 5: Audio Integration

**Use per-beat audio files**, placing each `<Audio>` inside its beat's `<Sequence>`. Do NOT place a single `<Audio>` at the composition root — this causes clipping when beats have different audio durations.

Use TransitionSeries instead of raw Sequence for scene sequencing. See [transition-catalog.md](transition-catalog.md) for the MainVideo template with transitions + audio.

Verify sync at key beat boundaries by rendering frames at beat start points.

### Step 6: Final Render (Parallel)

Use `parallel-render.sh` to render each scene as a separate MP4 in parallel, then concatenate with ffmpeg xfade transitions:

```bash
# Preview quality (fast, parallel)
${CLAUDE_PLUGIN_ROOT}/skills/remotion/scripts/parallel-render.sh --preview <project-dir> Scene0 Scene1 Scene2 Scene3 Scene4 Scene5

# Production quality (parallel)
${CLAUDE_PLUGIN_ROOT}/skills/remotion/scripts/parallel-render.sh <project-dir> Scene0 Scene1 Scene2 Scene3 Scene4 Scene5

# Custom options
${CLAUDE_PLUGIN_ROOT}/skills/remotion/scripts/parallel-render.sh --crf 18 --transition 0.5 --type fade <project-dir> Scene0 Scene1 Scene2 ...
```

**Fallback** (if parallel-render.sh is unavailable):
```bash
npx remotion render src/index.ts Main out/final.mp4 --codec h264 --crf 18
```

## Known Gotchas

| Gotcha | Fix |
|--------|-----|
| Async data not ready | `delayRender()` / `continueRender()` pair |
| Images flash/missing | `<Img>` from remotion, not `<img>` |
| Static files not found | `public/` dir + `staticFile()` |
| Text overflow | CSS `overflow: hidden` or `measureText()` |
| Font missing in render | `@remotion/google-fonts` with explicit `weights`/`subsets` |
| `useCurrentFrame()` resets | By design inside `<Sequence>` |
| Audio clips/cuts off mid-beat | Beat duration (frames) must be >= audio duration. Measure with `ffprobe` |
| Audio only plays in first beat | Use per-beat `<Audio>` inside each `<Sequence>`, not one at composition root |
| Shell CWD resets after `npx remotion` | Always prefix with `cd /project/path &&` in every command |
| Stale audio after regenerating clips | Clear bundle cache: `rm -rf node_modules/.cache` then re-render |
| Sub-beat audio overlaps (step lists) | Each sub-element audio needs its own `<Sequence>` with timing from `stepTimings`, not arbitrary frame spacing |

## Reference Files

| File | Contents |
|------|----------|
| [design-system.md](design-system.md) | Typography scale, spacing, color palette, safe zones, constants-first pattern |
| [backgrounds.md](backgrounds.md) | Gradients, grid/dot patterns, vignette, noise, accent glows, layering guide |
| [components.md](components.md) | Typewriter, WordHighlight, BarChart, Card, Badge, Beat, StepList, PipelineFlow |
| [components-extended.md](components-extended.md) | CountUp, CodeBlock, NodeGraph, QuoteCard, SplitScreen, BrowserMockup, AnimatedChecklist, StatHero |
| [scene-templates.md](scene-templates.md) | IntroScene, DataScene, ComparisonScene, CodeDemoScene, QuoteScene, FlowScene, OutroScene |
| [animation-vocabulary.md](animation-vocabulary.md) | Constrained animation names mapping to implementations |
| [animation-hooks.md](animation-hooks.md) | useSlideIn, useSlideOut, useCountUp, useDrawLine, useRevealWords, breathe, glowPulse, FloatingDots |
| [patterns.md](patterns.md) | Transitions, springs, stagger, audio viz, sequencing, Zod params |
| [motion-design-rules.md](motion-design-rules.md) | Timing, easing presets, stagger, Disney principles, rhythm, micro-details |
| [color-script-rules.md](color-script-rules.md) | Color budget, temperature mapping, scene transitions, brand integration |
| [transition-catalog.md](transition-catalog.md) | TransitionSeries API, built-in + custom presentations, narrative mapping |
| [elevenlabs-audio.md](elevenlabs-audio.md) | ElevenLabs voice-over pipeline, audio sync |
| [claude-md-template.md](claude-md-template.md) | Drop-in CLAUDE.md for Remotion projects |
| [official/](official/) | Full Remotion API reference (37 files from remotion-dev/skills) |

## Validation Checklist

- [ ] All compositions registered in Root file
- [ ] `delayRender`/`continueRender` for all async resources
- [ ] `<Img>` used (not `<img>`), `staticFile()` for public/ assets
- [ ] Theme tokens used consistently — no raw pixel values for spacing/font sizes
- [ ] **Constants-first pattern** — all configurable values at top of each scene
- [ ] **Background layers** — at minimum gradient + one pattern, not flat bg color
- [ ] **Typography scale** — display/h1/h2/h3/body/caption/label roles used correctly
- [ ] **Safe zones** — content within safe zone for target format (16:9 or 9:16)
- [ ] Key frames visually inspected (start, middle, end of each scene)
- [ ] Text does not overflow at target resolution
- [ ] Audio synced to timing manifest beat boundaries
- [ ] Sub-beat audio (step lists) plays sequentially, no overlap
- [ ] **Animation vocabulary** — all animations use named vocabulary terms
- [ ] **Spring presets** — only smooth/snappy/bouncy/heavy configs used (from motion-design-rules.md)
- [ ] **Color script compliance** — each scene's dominant color matches the color plan
- [ ] **Transitions** — MainVideo uses TransitionSeries, max 2-3 transition types
- [ ] Transcript generated at `docs/TRANSCRIPT.md`
- [ ] Final MP4 renders and plays correctly
