# Color Script Rules for Remotion Video Scenes

Codified color script techniques from Pixar/animation studio workflows, adapted for 15-30 second short-form vertical video (YouTube Shorts, Reels, TikTok). Every rule below is specific and implementable by an AI agent generating Remotion scene code.

---

## 1. Color Budget Per Scene

- **1 dominant color** occupies 60%+ of the scene area (background + largest elements).
- **1 secondary color** occupies 20-30% of the scene area (supporting elements, secondary text).
- **1 accent color** occupies 5-10% of the scene area (highlights, icons, interactive elements).
- **Neutrals are free.** Black (`#000`-`#222`), white (`#EEE`-`#FFF`), and grays (`#333`-`#DDD`) do not count toward the 3-color budget.
- **Never exceed 3 chromatic colors per scene.** If you need variety, use lightness/saturation variants of the same hue.
- **When intensity rises, increase saturation of existing colors.** Do not introduce a 4th chromatic hue for emphasis. Instead, push the accent from 50% saturation to 80%.

### Example

```
Scene: "Problem Statement"
Dominant:  #1A1A2E (dark navy)     — 65% area (background)
Secondary: #E94560 (warm red)      — 25% area (problem text, icons)
Accent:    #FFD700 (gold)          — 10% area (highlight spark)
Neutrals:  #FFFFFF (text), #888888 (subtext) — free
```

---

## 2. Color Temperature and Emotional Arc

### Temperature-to-Emotion Mapping

| Scene Purpose | Temperature | Hue Range (H in HSL) | Saturation | Brightness |
|---------------|-------------|----------------------|------------|------------|
| Hook / Intro | Neutral-cool | 180-240° (cyan-blue) | 30-50% | Medium (50-70%) |
| Problem / Tension | Warm-hot | 0-30° (red-orange) | 60-85% | Medium-high (55-75%) |
| Solution / Relief | Cool-neutral | 140-200° (green-cyan) | 40-60% | High (65-85%) |
| Proof / Data | Neutral | 200-260° (blue-indigo) | 20-40% | Medium (50-70%) |
| Celebration / Win | Warm gold | 35-55° (gold-amber) | 70-90% | High (70-90%) |
| CTA / Final | Brand dominant | Brand hue ± 15° | 60-80% | High (70-85%) |

### 5-Position Temperature Spectrum

```
1: Cool → 2: Cool-Neutral → 3: Neutral → 4: Warm-Neutral → 5: Warm
```

**Adjacent scenes must shift by at most 1 step.** A scene at position 2 (cool-neutral) can move to 1 (cool) or 3 (neutral), never to 4 or 5. This prevents jarring temperature jumps.

### Example Arc for a 5-Scene Video

```
Scene 1 (Hook):     Cool-Neutral  [2]
Scene 2 (Problem):  Neutral       [3]
Scene 3 (Tension):  Warm-Neutral  [4]
Scene 4 (Solution): Neutral       [3]
Scene 5 (CTA):      Warm-Neutral  [4]
```

---

## 3. Scene-to-Scene Color Transitions

### Shared Element Bridge

Adjacent scenes must share exactly **one chromatic color**, but it must play a **different role** in each scene. If Scene 2 uses `#E94560` as dominant, Scene 3 must use `#E94560` as secondary or accent, not dominant again.

### Background Pattern (Pick ONE Per Video)

| Pattern | Rule | Best For |
|---------|------|----------|
| **Gradient Walk** | Each scene's background hue rotates 15-30° from the previous scene. Direction (clockwise/counter-clockwise on color wheel) stays consistent for the entire video. | Videos with a steady emotional build |
| **Anchor and Explore** | One recurring background color appears in every 2nd scene (scenes 1, 3, 5...). Odd-numbered scenes use a contrasting background. | Videos alternating between narrator and content |
| **Convergence** | Early scenes use diverse background hues. Each subsequent scene's background moves closer to the final scene's background color. | Videos building toward a reveal or CTA |

**Pick one pattern per video. Do not mix patterns.**

### Luminance Continuity

Background luminance (L in HSL) between adjacent scenes must not jump more than **25 percentage points**. A scene with L:80 background can transition to L:55 or L:100, but not to L:30.

---

## 4. Brand Color Integration

- **Brand primary as accent:** The brand's primary color appears as the accent color in at least 60% of scenes.
- **Brand primary as dominant:** The brand color may serve as dominant in at most 40% of scenes. Overuse dilutes its impact.
- **Brand-adjacent palette:** Derive 3-4 supporting colors by rotating 30-60° from the brand hue on the color wheel. These are the secondary/accent candidates for non-brand-dominant scenes.
- **No complementary clash:** Never place the brand color directly on its complementary background (180° opposite). Use a split-complementary (150° or 210°) or analogous background instead.
- **CTA earns dominant status:** The final scene (CTA) is where the brand color graduates from accent to dominant. This creates a sense of arrival.

### Example: Brand Color `#2563EB` (Blue, H:220°)

```
Brand-adjacent palette:
  #0EA5E9 (H:195°, -25° from brand)  — cool cyan
  #6366F1 (H:245°, +25° from brand)  — indigo
  #8B5CF6 (H:265°, +45° from brand)  — violet
  #06B6D4 (H:185°, -35° from brand)  — teal
```

---

## 5. Rules for 15-30s Vertical Video

### Global Hue Budget

- **Total unique chromatic hues across the entire video: 6 or fewer.** Count hues by rounding to the nearest 30° on the color wheel. Two colors at H:35° and H:50° count as one hue bucket; H:35° and H:80° count as two.

### First/Last Scene Coherence

- The **first scene's dominant color** and the **last scene's dominant color** must be the same hue or analogous (within 40° of each other on the color wheel). This creates visual bookending.
- The first scene establishes either the **warmest** or the **coolest** color in the video's palette. No middle-temperature starts.

### Vertical Format (9:16) Specifics

- Background occupies a larger proportion of total pixels in 9:16 than 16:9. Treat the background color as the **primary color decision** for every scene.
- Large background areas amplify saturation perception. Reduce background saturation by 10-15% compared to what you would use in 16:9.

### Contrast Minimums

- **Text on background:** Minimum 4.5:1 luminance contrast ratio (WCAG AA).
- **Graphical elements on background:** Minimum 3:1 luminance contrast ratio.
- **Small text (below 18px equivalent):** Minimum 7:1 luminance contrast ratio.
- Validate contrast with relative luminance formula: `L = 0.2126*R + 0.7152*G + 0.0722*B` (linearized sRGB values). Ratio = `(L_lighter + 0.05) / (L_darker + 0.05)`.

---

## 6. Color Plan Algorithm

Step-by-step procedure for an AI agent to generate a per-scene color specification.

### Inputs

```
scene_count:    number        // total scenes in the video
emotional_arc:  string[]      // per-scene emotion label from Section 2 table
brand_colors:   string[]      // 1-3 hex codes, first is primary
```

### Steps

1. **Derive brand-adjacent palette.** Take `brand_colors[0]`, extract its hue. Generate 3-4 colors at +30°, -30°, +60°, -60° from brand hue, keeping saturation within 40-70% and lightness within 40-70%. Combine with brand colors to form the **master palette** (max 6 chromatic hues).

2. **Assign temperature per scene.** Map each `emotional_arc[i]` to a temperature position (1-5) using the table in Section 2. Validate that no two adjacent scenes differ by more than 1 step. If they do, insert a transitional temperature or adjust the arc.

3. **Choose background pattern.** Select one of: `gradient_walk`, `anchor_explore`, `convergence`. Use `convergence` if the video builds to a reveal. Use `anchor_explore` if the video alternates narrator/content. Use `gradient_walk` as the default.

4. **Assign background colors.** Apply the chosen pattern to select a background color for each scene from the master palette. Verify adjacent backgrounds differ by no more than 25 L-points.

5. **Assign dominant/secondary/accent per scene.** For each scene:
   - Dominant = background color (60%+ area).
   - Secondary = one color from master palette matching the scene's temperature (20-30% area).
   - Accent = brand primary if this scene is in the 60%+ accent group, otherwise another palette color (5-10% area).
   - Verify the shared-element bridge: at least one chromatic color from the previous scene appears in a different role.

6. **Validate all constraints:**
   - First and last scene dominants are within 40° of each other.
   - Peak saturation occurs at the emotional climax scene.
   - No adjacent background luminance jumps exceed 25%.
   - Total unique hues (rounded to 30° buckets) is 6 or fewer.
   - Adjacent temperature steps are 1 or less.
   - All text contrast ratios meet 4.5:1 minimum.

7. **Output format:**

```typescript
type ColorPlan = {
  masterPalette: string[];           // 4-6 hex codes
  backgroundPattern: 'gradient_walk' | 'anchor_explore' | 'convergence';
  scenes: Array<{
    sceneIndex: number;
    emotion: string;
    temperature: 1 | 2 | 3 | 4 | 5;
    dominant: string;                // hex
    secondary: string;              // hex
    accent: string;                 // hex
    background: string;             // hex (may equal dominant)
    textColor: string;              // hex
    contrastRatio: number;          // computed, must be >= 4.5
  }>;
};
```

---

## 7. Light Theme Specifics

Rules for videos using light/white backgrounds (product ads, clean UI demos, minimalist style).

### Background Lightness

- Background stays in the **L:90-98 range** (HSL lightness). Pure white is L:100; stay just below it to avoid harsh screen glare.
- Never use L:100 (`#FFFFFF`) as the full-frame background. Use `#F8F8F8` (L:97) or `#FAFAFA` (L:98) minimum.

### Tinted Whites for Temperature

Shift emotional temperature through subtle background tinting instead of saturated backgrounds:

| Temperature | Tinted White | Hex Example |
|-------------|-------------|-------------|
| Cool | Blue-tinted white | `#F0F4F8` |
| Cool-neutral | Gray-blue white | `#F5F7FA` |
| Neutral | Pure near-white | `#F8F8F8` |
| Warm-neutral | Cream white | `#FAF8F5` |
| Warm | Gold-tinted white | `#FFF8F0` |

### Foreground Color Rules

- On light backgrounds, **all color expression comes from foreground elements** (text, icons, illustrations, data viz).
- Accent colors must have **minimum 50% saturation** to read clearly against L:90+ backgrounds. Below 50% saturation, colors appear washed out.
- Secondary colors need **minimum 40% saturation**.
- Dark text on light backgrounds: use `#1A1A1A` to `#333333`, never pure `#000000` (too harsh).

### Shadow and Depth

- Use subtle box shadows (`rgba(0,0,0,0.06)` to `rgba(0,0,0,0.12)`) to separate foreground cards from the light background.
- Colored shadows (using the dominant color at 8-15% opacity) add warmth without introducing new hues.

### Light Theme Contrast Check

- Colored text on white needs extra validation. Many brand blues and greens fail 4.5:1 on white at their standard saturation. Darken the color (reduce L to 35-45%) rather than increasing saturation.
- Large colored areas (filled cards, banners) on light backgrounds: the fill color becomes the new "background" for contrast purposes. Check text contrast against the fill, not against the page background.