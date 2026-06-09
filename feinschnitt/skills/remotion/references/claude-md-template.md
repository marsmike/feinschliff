# CLAUDE.md Template for Remotion Projects

Drop this into your Remotion project root as `CLAUDE.md`.

---

```markdown
# CLAUDE.md

## Project Type

Remotion v4 — programmatic video creation with React.

## Commands

```bash
npm run dev           # Start Remotion Studio (dev server with preview)
npx remotion still src/index.ts <id> frame.png --frame=N  # Render single frame
npx remotion render src/index.ts <id> out.mp4             # Render full video
npm install @remotion/transitions  # scene transitions (fade, slide, wipe)
```

## Architecture

- `src/index.ts` — entry point (`registerRoot`)
- `src/Root.tsx` — composition registration
- `src/theme.ts` — design tokens and font loading
- `src/components/` — reusable React components (Card, Badge, etc.)
- `src/compositions/` — video compositions (one per file)
- `public/` — static assets (audio, images), reference with `staticFile()`

## Critical Conventions

- **`<Img>` not `<img>`** — Remotion's `<Img>` waits for load before frame capture
- **`staticFile()`** — always use for files in `public/`
- **`delayRender` / `continueRender`** — required for async resources (fonts, data fetching)
- **`@remotion/google-fonts`** — load fonts with explicit `weights` and `subsets`
- **Theme tokens** — all colors, fonts, spacing from `src/theme.ts`

## Visual Feedback Loop

After writing or editing a composition, always render a still frame and inspect it:

```bash
npx remotion still src/index.ts <CompositionId> frame.png --frame=0 --scale=0.5
```

Then read `frame.png` to check the layout. Fix any issues before proceeding.

## Design System

Dark theme with colored accents. See `src/theme.ts` for all tokens.

## Animation Reference

- `src/components/Beat.tsx` — declarative enter/exit tied to narration beats
- `src/components/Typewriter.tsx` — character-by-character text reveal
- Spring presets: smooth (damping: 200), snappy (damping: 20, stiffness: 200), bouncy (damping: 8)
```
