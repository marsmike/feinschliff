# Animation Vocabulary

A constrained set of named animations that map 1:1 to specific implementations. All storyboard animation descriptions MUST use names from this vocabulary.

## Entrance Animations

| Name | Implementation | Description |
|------|---------------|-------------|
| `fade-in` | `spring({ damping: 200 })` on opacity | Simple fade, 20 frames |
| `slide-up` | `useSlideIn(frame, delay, 20, "bottom")` | Slide + fade from below |
| `slide-left` | `useSlideIn(frame, delay, 20, "left")` | Slide + fade from left |
| `slide-right` | `useSlideIn(frame, delay, 20, "right")` | Slide + fade from right |
| `spring-in` | `spring({ damping: 8 })` on scale 0→1 | Bouncy scale entrance |
| `stagger-up` | `slide-up` with `delay: i * STAGGER_DELAY` | Sequential items from below |
| `stagger-left` | `slide-left` with `delay: i * STAGGER_DELAY` | Sequential items from left |
| `typewriter` | `<Typewriter>` component | Character-by-character reveal |
| `count-up` | `<CountUp>` component | Number interpolation |
| `draw-line` | SVG `strokeDashoffset` interpolation | Line/edge drawing |
| `reveal-words` | Per-word opacity with stagger | Word-by-word text appearance |
| `checklist` | `<AnimatedChecklist>` component | Sequential checkmarks |
| `code-reveal` | `<CodeBlock revealMode="line-by-line">` | Line-by-line code appearance |

## Exit Animations

| Name | Implementation | Description |
|------|---------------|-------------|
| `fade-out` | `interpolate` opacity 1→0 | Simple fade, 15 frames |
| `slide-out-up` | `useSlideOut(frame, start, 15, "top")` | Slide + fade upward |
| `slide-out-left` | `useSlideOut(frame, start, 15, "left")` | Slide + fade left |
| `scale-down` | `spring` on scale 1→0 | Shrink and disappear |

## Continuous Animations

| Name | Implementation | Description |
|------|---------------|-------------|
| `breathe` | `breathe(frame)` | Subtle scale oscillation |
| `glow-pulse` | `glowPulse(frame, color)` | Pulsing box-shadow |
| `float` | `FloatingDots` component | Ambient background dots |

## Transitions (between scenes)

| Name | Implementation | Description |
|------|---------------|-------------|
| `crossfade` | `fade()` transition | Standard dissolve |
| `slide-over` | `slide({ direction })` transition | New scene slides over |
| `wipe` | `wipe({ direction })` transition | Directional wipe |
| `cut` | No transition | Hard cut |

## Usage in Storyboard

Each beat's animation description field MUST reference vocabulary names, not free-text descriptions.

**Correct:**
- "Steps appear with `stagger-up`, 8-frame delay"
- "Title enters with `fade-in`, subtitle follows with `slide-up` at delay 20"
- "Nodes connected by `draw-line` left to right"
- "Scene transition: `crossfade`"

**Incorrect:**
- "Steps appear sequentially with a spring bounce animation"
- "Title fades in smoothly while subtitle slides up underneath"
- "Lines animate between nodes"
- "Smooth transition to next scene"

The vocabulary names are not suggestions — each one maps to a specific implementation the build phase can execute without interpretation.
