# Design System — Typography, Spacing, Safe Zones

Reference for consistent visual design across all Remotion video compositions. Use these tokens in every project — never invent ad-hoc sizes.

---

## Brand Design Systems (awesome-design-md)

For branded videos in the style of other companies (Apple, Linear, Stripe, Vercel, Notion, etc.), fetch the company's DESIGN.md from [awesome-design-md](https://github.com/VoltAgent/awesome-design-md) — 76+ design systems as plain markdown.

**URL pattern:** `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/designs/<brand>/DESIGN.md`

**How to apply to Remotion `theme.ts`:**

1. Fetch the DESIGN.md for the target brand
2. Extract and map to the theme object:
   - **Color Palette & Roles** → override `bg`, `surface`, `text`, accent colors, and semantic colors
   - **Typography Rules** → override font loading (swap Google Fonts to brand-appropriate fonts), adjust scale weights
   - **Spacing & Layout** → adapt spacing tokens to brand's grid system
   - **Shape & Elevation** → override `radius`, add shadow patterns if the brand uses them
   - **Motion Language** → adapt animation timing and easing to match the brand's motion guidelines (if specified)

**Example:** For an Apple-style video, fetch Apple's DESIGN.md, then:
- Load SF Pro (or Inter as web substitute) instead of default font preset
- Use Apple's neutral palette (grays, whites, subtle blues)
- Apply Apple's spacing philosophy (generous whitespace, centered layouts)
- Use Apple's motion style (smooth spring animations, subtle parallax)

---

## Typography Scale

Sized for **1920×1080 (16:9)**. For 9:16 (1080×1920 Shorts), multiply all font sizes by **1.3–1.5** to maintain readability at phone scale.

| Role | Font | Size | Weight | Line Height | Use For |
|------|------|------|--------|-------------|---------|
| `display` | fontSans | 72px | 800 | 1.1 | Hero numbers, big stats |
| `h1` | fontSans | 56px | 700 | 1.2 | Scene titles |
| `h2` | fontSans | 40px | 600 | 1.25 | Section headings |
| `h3` | fontSans | 28px | 600 | 1.3 | Card titles |
| `body` | fontSans | 22px | 400 | 1.5 | Descriptions, paragraphs |
| `caption` | fontSans | 16px | 400 | 1.4 | Labels, footnotes |
| `label` | fontMono | 14px | 600 | 1.0 | Badges, tags, code labels |
| `code` | fontMono | 20px | 400 | 1.6 | Code blocks, terminal text |

**Rule of thumb:** If you can't read it at 0.4x scale in a still frame, it's too small. Use the visual feedback loop to verify.

---

## Font Pairing Presets

Load fonts using `@remotion/google-fonts`. Always specify explicit `weights` and `subsets` to avoid render-time failures.

### Preset 1: Tech (dev tools, terminals, coding content)

```typescript
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadJetBrainsMono } from "@remotion/google-fonts/JetBrainsMono";

const { fontFamily: fontSans } = loadInter({ weights: ["400", "600", "700", "800"], subsets: ["latin"] });
const { fontFamily: fontMono } = loadJetBrainsMono({ weights: ["400", "600"], subsets: ["latin"] });

// Usage in theme:
// fontSans → all prose, headers, UI labels
// fontMono → code, terminal output, badges
```

### Preset 2: Clean (consumer products, SaaS, data dashboards)

```typescript
import { loadFont as loadPlusJakarta } from "@remotion/google-fonts/PlusJakartaSans";
import { loadFont as loadFiraCode } from "@remotion/google-fonts/FiraCode";

const { fontFamily: fontSans } = loadPlusJakarta({ weights: ["400", "600", "700", "800"], subsets: ["latin"] });
const { fontFamily: fontMono } = loadFiraCode({ weights: ["400", "600"], subsets: ["latin"] });

// Usage in theme:
// fontSans → all UI text, clean and modern
// fontMono → metrics, data labels, inline code
```

### Preset 3: Editorial (storytelling, explainers, lifestyle)

```typescript
import { loadFont as loadDMSans } from "@remotion/google-fonts/DMSans";
import { loadFont as loadDMSerif } from "@remotion/google-fonts/DMSerifDisplay";

const { fontFamily: fontSans } = loadDMSans({ weights: ["400", "500", "700"], subsets: ["latin"] });
const { fontFamily: fontSerif } = loadDMSerif({ weights: ["400"], subsets: ["latin"] });

// Usage in theme:
// fontSans → body, captions, labels
// fontSerif → display, h1 — gives editorial gravitas
// (no mono needed; skip fontMono for this preset)
```

---

## Spacing Scale

4px-based system. Every gap, padding, and margin must use one of these tokens — no raw pixel values.

| Token | Value | Typical Use |
|-------|-------|-------------|
| `xs` | 4px | Inline gaps, icon-to-label spacing |
| `sm` | 8px | Tight padding inside badges/pills |
| `md` | 16px | Card internal padding (compact) |
| `lg` | 24px | Card internal padding (comfortable), section gaps |
| `xl` | 40px | Between major elements, section breaks |
| `2xl` | 64px | Between scenes/blocks, generous whitespace |
| `3xl` | 80px | Edge margins, hero section breathing room |

---

## Color Palette

### Semantic Colors

Use these for state feedback and alerts — consistent across all themes.

| Role | Light Theme | Dark Theme | Use For |
|------|------------|-----------|---------|
| `success` | `#22c55e` | `#a3e635` | Positive metrics, completed states |
| `warning` | `#f59e0b` | `#fb923c` | Cautions, partial results |
| `error` | `#ef4444` | `#f87171` | Failures, negative metrics |
| `info` | `#3b82f6` | `#67e8f9` | Neutral callouts, tips |

### Tint Scale Pattern

For any accent color, generate three tint variants for layered UI (backgrounds, borders, subtle text):

```typescript
// Example: green accent tints
const greenBg     = "rgba(163, 230, 53, 0.06)";   // 6% — card/panel background fill
const greenBorder = "rgba(163, 230, 53, 0.19)";   // 19% — border, divider lines
const greenMuted  = "rgba(163, 230, 53, 0.38)";   // 38% — secondary text, icons

// Apply the same pattern to every accent color in your theme:
// purpleBg / purpleBorder / purpleMuted
// cyanBg   / cyanBorder   / cyanMuted
// orangeBg / orangeBorder / orangeMuted
// etc.
```

This three-step tint scale ensures sufficient contrast at each layer while maintaining color cohesion.

---

## Safe Zones

Pixel boundaries that keep content visible across all display surfaces (TVs, YouTube player UI, mobile crop).

### 16:9 — 1920×1080

| Zone | Value | Notes |
|------|-------|-------|
| Edge margins (min) | 80px left/right | Never place text closer to edge |
| Title safe (recommended) | 120px all sides | Comfortable for most content |
| Max content width | 1680px | Centered within 1920px frame |
| Top safe | 80px | Clear of YouTube chapter markers |
| Bottom safe | 120px | Clear of YouTube progress bar overlay |

```
┌─────────────────────────────────────┐  1920px
│  80px edge │                        │
│  ┌───────────────────────────────┐  │
│  │   120px title safe all sides  │  │
│  │                               │  │
│  │   max content: 1680px wide    │  │
│  │                               │  │
│  └───────────────────────────────┘  │
│                        │ 80px edge  │
└─────────────────────────────────────┘
```

### 9:16 — 1080×1920 (YouTube Shorts / TikTok)

| Zone | Value | Notes |
|------|-------|-------|
| Side margins (min) | 50px left/right | Absolute minimum for phone screens |
| Side margins (recommended) | 64px left/right | Better for tall phones with curved edges |
| Top safe (Shorts UI) | 120px | Clear of Shorts header/like buttons |
| Bottom safe (Shorts UI) | 180px | Clear of caption overlay and nav bar |
| Max content width | 952px | 1080 − (2 × 64px) |
| Title safe (all sides) | 80px minimum | For text that must never be cropped |

```
┌───────────────┐  1080px
│  top: 120px   │
│ ┌───────────┐ │
│ │ 64px side │ │
│ │           │ │
│ │ max 952px │ │  1920px
│ │   wide    │ │
│ │           │ │
│ └───────────┘ │
│ bottom: 180px │
└───────────────┘
```

---

## Constants-First Pattern

Define all scene configuration at the top of each component file in a single `SCENE_CONFIG` object. This makes values easy to find, tweak, and visually verify.

### Correct — constants at top

```typescript
// src/scenes/Scene1.tsx

const SCENE_CONFIG = {
  // Typography
  titleSize: 56,
  bodySize: 22,
  captionSize: 16,
  // Spacing
  cardPadding: 24,
  cardGap: 16,
  edgeMargin: 120,
  // Animation
  entranceDuration: 20,
  staggerDelay: 8,
  // Layout
  maxContentWidth: 1680,
} as const;

export const Scene1: React.FC = () => {
  return (
    <AbsoluteFill style={{ padding: SCENE_CONFIG.edgeMargin }}>
      <h1 style={{ fontSize: SCENE_CONFIG.titleSize }}>Title</h1>
    </AbsoluteFill>
  );
};
```

### Wrong — inline magic numbers

```typescript
// DO NOT DO THIS
export const Scene1: React.FC = () => {
  return (
    <AbsoluteFill style={{ padding: 120 }}>        {/* where did 120 come from? */}
      <h1 style={{ fontSize: 56 }}>Title</h1>      {/* can't tweak without hunting */}
      <p style={{ marginTop: 18 }}>Body</p>         {/* not a spacing token */}
    </AbsoluteFill>
  );
};
```

Constants-first also makes visual QA faster: when a still frame shows bad spacing, you change one number at the top instead of hunting through JSX.

---

## TypeScript Implementation

Add to `src/theme.ts` alongside your color palette. Extend your existing `theme` object or export separately.

```typescript
// src/theme.ts

// --- Font loading (choose one preset from Font Pairing Presets) ---
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadJetBrainsMono } from "@remotion/google-fonts/JetBrainsMono";

const { fontFamily: fontSans } = loadInter({
  weights: ["400", "600", "700", "800"],
  subsets: ["latin"],
});
const { fontFamily: fontMono } = loadJetBrainsMono({
  weights: ["400", "600"],
  subsets: ["latin"],
});

// --- Typography scale ---
export const typography = {
  display: { fontSize: 72, fontWeight: 800, lineHeight: 1.1, fontFamily: fontSans },
  h1:      { fontSize: 56, fontWeight: 700, lineHeight: 1.2, fontFamily: fontSans },
  h2:      { fontSize: 40, fontWeight: 600, lineHeight: 1.25, fontFamily: fontSans },
  h3:      { fontSize: 28, fontWeight: 600, lineHeight: 1.3, fontFamily: fontSans },
  body:    { fontSize: 22, fontWeight: 400, lineHeight: 1.5, fontFamily: fontSans },
  caption: { fontSize: 16, fontWeight: 400, lineHeight: 1.4, fontFamily: fontSans },
  label:   { fontSize: 14, fontWeight: 600, lineHeight: 1.0, fontFamily: fontMono },
  code:    { fontSize: 20, fontWeight: 400, lineHeight: 1.6, fontFamily: fontMono },
} as const;

// --- Spacing scale (4px base) ---
export const spacing = {
  xs:   4,
  sm:   8,
  md:   16,
  lg:   24,
  xl:   40,
  "2xl": 64,
  "3xl": 80,
} as const;

// --- Safe zones ---
export const safeZones = {
  landscape: {
    edgeMargin: 80,
    titleSafe: 120,
    maxContentWidth: 1680,
    topSafe: 80,
    bottomSafe: 120,
  },
  portrait: {
    sideMargin: 64,
    topSafe: 120,
    bottomSafe: 180,
    maxContentWidth: 952,
    titleSafe: 80,
  },
} as const;

// --- Compose into theme (example dark/tech theme) ---
export const theme = {
  // Colors
  bg: "#0a0a0f",
  surface: "#1a1a24",
  surfaceBorder: "#2a3a2a",
  green: "#a3e635",
  purple: "#8b5cf6",
  cyan: "#67e8f9",
  orange: "#fb923c",
  text: "#e0e0e0",
  muted: "#888898",

  // Semantic
  success: "#a3e635",
  warning: "#fb923c",
  error: "#f87171",
  info: "#67e8f9",

  // Tints (green example — repeat pattern for each accent)
  greenBg:     "rgba(163, 230, 53, 0.06)",
  greenBorder: "rgba(163, 230, 53, 0.19)",
  greenMuted:  "rgba(163, 230, 53, 0.38)",

  // Typography
  typography,

  // Spacing
  spacing,

  // Safe zones
  safeZones,

  // Shape
  radius: 12,
  radiusSm: 6,
  radiusLg: 20,
} as const;

export type Theme = typeof theme;
```

### Usage in components

```typescript
import { theme } from "../theme";

// Typography
<h1 style={{ ...theme.typography.h1, color: theme.text }}>Scene Title</h1>
<p style={{ ...theme.typography.body, color: theme.muted }}>Description</p>

// Spacing
<div style={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>

// Safe zones (landscape)
<AbsoluteFill style={{ padding: theme.safeZones.landscape.titleSafe }}>
```
