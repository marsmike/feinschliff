# Motion Design Rules for Remotion Video Scenes

Codified rules for professional motion graphics in short-form vertical video (YouTube Shorts, Reels, TikTok) and animated explainer content. Every rule below is specific and implementable.

---

## 1. Timing and Duration

### Element Animation Durations
- **Micro-feedback** (toggles, checkmarks, icon swaps): 100-150ms (3-5 frames at 30fps)
- **Small elements** (badges, labels, small text): 200-300ms (6-9 frames)
- **Medium elements** (cards, panels, content blocks): 300-400ms (9-12 frames)
- **Large/hero elements** (full-screen transitions, title reveals): 500-700ms (15-21 frames)
- **Maximum for any single animation**: 1000ms (30 frames). Anything longer feels sluggish.

### Human Perception Thresholds
- Below 100ms: perceived as instant (use for color/opacity snaps)
- 150ms: minimum time for a viewer to consciously register a change
- 215-230ms: average human visual reaction time
- 350ms: upper limit before attention drifts to something else
- Above 500ms: feels like a deliberate pause (use only with intent)

### Frame Budget at 30fps
- 3 frames = 100ms (instant feel)
- 6 frames = 200ms (snappy)
- 9 frames = 300ms (standard)
- 15 frames = 500ms (deliberate)
- 30 frames = 1000ms (dramatic/hero only)

### Short-Form Pacing Rule
Something visually meaningful must happen on screen every 2-4 seconds. If a shot holds static for more than 5 seconds, the viewer's attention fades. For YouTube Shorts specifically, the first 1-2 seconds must contain motion or a visual hook.

---

## 2. Easing Curves

### Standard Easing Library (use consistently across entire video)

| Name | Use Case | Remotion Implementation |
|------|----------|------------------------|
| **Smooth (default)** | Most movements, repositioning | `spring({ frame, fps, config: { damping: 200 } })` |
| **Snappy** | Small elements, badges, icons | `spring({ frame, fps, config: { damping: 20, stiffness: 200 } })` |
| **Bouncy** | Attention-grabbing, playful emphasis | `spring({ frame, fps, config: { damping: 8 } })` |
| **Heavy** | Large elements, backgrounds | `spring({ frame, fps, config: { damping: 15, stiffness: 80, mass: 2 } })` |

### Easing Direction Rules
- **Entrances (element appearing)**: use ease-out / deceleration. Element arrives at full velocity and settles. CSS equivalent: `cubic-bezier(0.0, 0.0, 0.2, 1)`.
- **Exits (element leaving)**: use ease-in / acceleration. Element starts slow and exits at full velocity. CSS equivalent: `cubic-bezier(0.4, 0.0, 1, 1)`.
- **On-screen movement** (repositioning): use ease-in-out / standard. CSS equivalent: `cubic-bezier(0.4, 0.0, 0.2, 1)`.
- **Color and opacity changes**: use linear easing. Non-linear easing on color produces uneven blending.

### Consistency Rule
Pick ONE easing profile per element category and use it for the entire video. Mixing different spring configs for similar elements breaks visual cohesion. Document your choices in the project's theme.

---

## 3. Stagger and Choreography

### Stagger Timing
- **Standard stagger delay**: 50-100ms (2-3 frames at 30fps) between sequential elements
- **Maximum stagger delay**: 150ms (5 frames). Beyond this, the sequence feels disconnected.
- **Total sequence duration**: keep cascading animations under 1-2 seconds total
- **Formula**: for N items with D ms delay, total cascade = elementDuration + (N-1) * D. Keep this under 2000ms.

### Stagger Patterns
- **List/grid items**: uniform delay (every item gets same offset). Use `delay: i * STAGGER_DELAY`.
- **Hierarchical content**: title first, then subtitle (50ms later), then body (100ms later), then CTA (150ms later). Larger conceptual gaps = larger delays.
- **Left-to-right reading order**: stagger elements in the direction the eye naturally scans.

### Choreography Rules
- Never animate more than 3 unrelated things simultaneously. The eye cannot track them.
- Group related elements and animate them as a unit, then stagger the units.
- The most important element animates FIRST. Secondary elements follow.
- If two elements are conceptually linked, they should share the same animation timing.

---

## 4. Entrances and Exits

### Every Element Must Enter and Exit with Purpose
- No element should "just appear" or "just disappear" without animation (except hard cuts between scenes).
- No orphaned elements: if something enters, it must either persist through a scene transition or have an explicit exit animation.

### Entrance Patterns (pick one per element type, stay consistent)
- **Fade up + slide**: opacity 0->1 with translateY(30px -> 0). The default safe choice.
- **Scale pop**: scale 0.8->1 with opacity 0->1. Good for badges, icons, emphasis.
- **Slide from direction**: translateX or translateY with opacity. Direction should match reading flow or narrative direction.
- **Typewriter/reveal**: for text. Characters or words appear sequentially.

### Exit Patterns
- Exits should be 20-30% faster than entrances. If entrance is 300ms, exit should be 200-250ms.
- Exits should reverse the entrance direction (entered from left = exits to left).
- Fade-out is always acceptable as a universal exit.
- Never exit an element toward the viewer's next focus point (it creates visual collision).

### Anticipation Rule
For hero/emphasized animations, add a small counter-movement before the main motion. Example: scale to 0.95 over 3 frames before scaling to 1.1 over 9 frames. This signals "something is about to happen" and draws the eye.

---

## 5. Scene Transitions

### Transition Duration
- **Hard cut**: 0 frames. Use for high-energy pacing, beat-matched edits.
- **Fade/dissolve**: 10-15 frames (333-500ms). Use for emotional moments, passage of time.
- **Slide/wipe**: 10-20 frames (333-666ms). Use for spatial scene changes.
- **Morph/match cut**: 15-20 frames (500-666ms). Use for conceptual connections between scenes.

### Transition Selection Rules
- Use the SAME transition type for scenes of the same narrative category (all "explanation" scenes use the same transition).
- Use a DIFFERENT transition type to signal a narrative shift (explanation -> demo = different transition).
- Maximum 2-3 transition types per video. More than that feels chaotic.
- Hard cuts should make up 50-70% of transitions. They are the default.
- Reserve fancy transitions (morph, match cut) for 1-2 key moments.

### Visual Flow Continuity
- If Scene A ends with motion moving right, Scene B should start with motion from the left (preserving momentum).
- If Scene A ends with a focal point in the top-right, Scene B should begin its focal point nearby (top-right or center), not bottom-left.
- Match the dominant color temperature at the seam: do not cut from warm orange directly to cold blue without a transitional beat.

### Remotion Implementation
```
TransitionSeries.Transition timing: linearTiming({ durationInFrames: 15 })
Default presentation: fade()
For spatial changes: slide({ direction: "from-right" })
For reveals: wipe({ direction: "from-left" })
```
Remember: transitions REDUCE total duration. Two 60-frame scenes with a 15-frame transition = 105 frames total.

---

## 6. Visual Continuity Across Scenes

### Element Consistency
- Recurring elements (logos, labels, progress indicators) must appear in the SAME position across all scenes. Pick a corner and stick with it.
- Text styling (font, size, weight, color) for the same semantic role must be identical across scenes. A "section title" looks the same in Scene 1 and Scene 5.
- If an element persists across scenes, it should NOT re-animate. It stays in place while other elements transition.

### Motion Language Consistency
- Define a "motion vocabulary" at the start: elements enter from bottom, exit by fading, emphasis uses scale pulse. Apply this vocabulary to every scene.
- The speed/energy of animation should match the narrative beat. Calm explanation = slower, smoother springs (damping: 200). Exciting reveal = snappier springs (damping: 20).
- Do not introduce a new animation pattern in the last third of the video. Establish all patterns in the first 30%.

### Spatial Consistency
- Maintain a consistent "camera distance." If Scene 1 shows elements at a certain scale, Scene 2 should not dramatically zoom without narrative reason.
- Use a consistent grid/layout system. If content is centered in Scene 1, it should be centered in Scene 3 (unless a deliberate layout shift is the point).

---

## 7. Color and Emotional Flow

### Color Script Rules
- Plan color temperature for each scene BEFORE animating. Map: warm (red/orange/yellow) = energy, excitement, urgency. Cool (blue/purple/cyan) = calm, trust, reflection. Neutral (gray/white) = information, transition.
- Each scene should have ONE dominant color that sets its emotional tone. Secondary colors support but do not compete.
- Color transitions between scenes should be gradual. Adjacent scenes should share at least one color from their palettes.
- Limit the active palette to 3-4 colors per scene (1 dominant, 1-2 supporting, 1 accent).

### Saturation and Brightness Rules
- High saturation = high energy, youthful, playful. Use for hooks and CTAs.
- Low saturation = serious, nostalgic, premium. Use for reflective moments.
- Increase brightness/saturation at the climax of your narrative arc.
- Decrease brightness slightly for setup/context scenes.

### Dark Theme Specifics (matching your theme.ts)
- Background: deep dark (#0a0a0f). Never pure black (#000000) -- it kills contrast hierarchy.
- Surface elements: slightly lighter (#1a1a24) to create depth without competing.
- Text: off-white (#e0e0e0), not pure white (#ffffff) -- reduces eye strain.
- Accent colors (green #a3e635, purple #8b5cf6, pink #f472b6, cyan #67e8f9, orange #fb923c): use ONE per scene as dominant accent. The others can appear as secondary.
- Muted text (#888898): for labels, timestamps, supporting info only.

---

## 8. Safe Zones for Vertical Video (1080x1920)

### Platform-Safe Content Area
- **Top buffer**: 250px from top (platform UI: username, audio label)
- **Bottom buffer**: 320px from bottom (CTA buttons, description, engagement UI)
- **Side buffers**: 120px each side (device cropping variance)
- **Effective safe zone**: approximately 840x1350px centered

### Text Placement Rules
- **Primary text**: place in the upper third of the safe zone (y: 250-700px)
- **Subtitles/lower thirds**: position at y: ~1500px (10-12% above bottom edge, above platform UI)
- **Never place critical text** in the bottom 320px or top 250px
- **Minimum text size**: 42px for body text, 64px for titles (must be readable on a phone at arm's length)

### Layout Strategy
- Guide the viewer's eye top-to-bottom using vertical motion and layout hierarchy
- Center the primary focal point vertically (around y: 800-1000px)
- Leave breathing room: never fill more than 70% of the safe zone with content

---

## 9. The 12 Animation Principles (Applied to Motion Graphics)

### Squash and Stretch
- Apply subtle scale deformation (2-5%) during fast movements to convey elasticity and energy.
- Horizontal squash on landing (scaleX: 1.05, scaleY: 0.95), vertical stretch on launch (scaleX: 0.95, scaleY: 1.05).
- Duration: 2-3 frames for the deformation, 3-5 frames to settle back.

### Anticipation
- Before a major movement, apply a small counter-movement (10-20% of the main movement magnitude).
- Duration: 2-4 frames for anticipation, then the main action.
- Example: before sliding right by 200px, slide left by 20-40px first.

### Follow-Through and Overlapping Action
- Stagger animated properties so they do NOT all start and end at the same time.
- If an element moves and fades, start the movement 2-3 frames before the fade.
- Child elements should lag behind parent elements by 2-4 frames (overlapping action).
- After the main motion stops, allow 2-3 frames of overshoot settling (Remotion springs handle this naturally with low damping).

### Secondary Action
- Add a subtle secondary animation to reinforce the primary one. Example: text slides in (primary) while a subtle glow pulses behind it (secondary).
- Secondary actions should be 50% or less of the visual weight of the primary action.
- Never let secondary actions distract from the primary. If in doubt, remove them.

### Arcs
- Movement paths should follow curves, not straight lines. Objects moving across the screen should arc slightly.
- For Remotion: combine translateX and translateY interpolations with different timing to create natural arcs.
- Straight-line motion is acceptable only for mechanical/technical elements (code, data, UI chrome).

### Exaggeration
- Motion graphics lack faces and bodies, so exaggerate property changes by 10-30% beyond their "realistic" endpoint.
- A notification badge should scale to 1.1-1.2 before settling at 1.0, not just appear at 1.0.
- Text emphasis: briefly scale to 105-110% then settle to 100%.

### Staging
- Only ONE thing should demand the viewer's primary attention at any moment.
- Use contrast (bright element on dark background), motion (only the focus element moves), and scale (larger = more important) to direct attention.
- Everything else in the scene should be visually subordinate: muted colors, static, smaller.

---

## 10. Micro-Details That Signal Quality

### Polish Checklist
- [ ] Every animated element has both an entrance and exit animation
- [ ] No element teleports (appears/disappears without transition)
- [ ] Stagger delays are consistent across similar element groups
- [ ] The same spring config is used for the same element type throughout the video
- [ ] Text is within the safe zone on all platforms
- [ ] Minimum 42px font size for any visible text
- [ ] No animation exceeds 1 second without narrative justification
- [ ] Color accent is consistent within each scene (one dominant accent)
- [ ] Scene transitions use no more than 3 different types total
- [ ] Hard cuts are on the beat (if music/rhythm is present)

### Subtle Details That Elevate Quality
- **Slight rotation on entrance**: add 1-3 degrees of rotation that settles to 0 during entrance animations. Creates organic feel.
- **Opacity never starts at exactly 0**: start at 0.01-0.02 so the element is "present" in the render tree before animating.
- **Drop shadows animate WITH the element**: shadow offset and blur should change as elements move (closer to surface = smaller shadow).
- **Background subtle motion**: a very slow drift (0.5-1px/second) on background elements prevents the scene from feeling frozen.
- **Consistent border radius**: use the same radius value (e.g., theme.radius = 12) on all rounded elements. Mixed radii look unpolished.
- **Text kerning matters**: use letter-spacing of -0.02em to -0.01em on large titles for tighter, more professional feel.

### Common Mistakes to Avoid
- Linear easing on movement (looks robotic). Always use spring or ease-in-out.
- All elements animating at exactly the same time (looks like a slideshow, not motion design).
- Bouncy springs on everything (exhausting to watch). Reserve bounce for 1-2 emphasis moments per scene.
- Inconsistent animation speed between scenes without narrative reason.
- Text that is readable in the editor but too small on a phone screen.
- Forgetting that 30fps means each frame is 33ms -- animations specified in ms must be converted to frame counts.

---

## 11. Rhythm and Music Sync

### Beat Mapping
- Major visual changes (scene cuts, hero reveals) should land ON the beat.
- Minor visual changes (element entrances, text reveals) should land on the half-beat or off-beat.
- At 120 BPM: beat every 500ms (15 frames at 30fps), half-beat every 250ms (7-8 frames).
- At 90 BPM: beat every 667ms (20 frames), half-beat every 333ms (10 frames).

### Pacing Arc for 30-60 Second Videos
- **0-3s (Hook)**: fastest pacing, most visual density. 1-2 second shot length.
- **3-15s (Setup)**: moderate pacing. 2-3 second shots. Establish the visual language.
- **15-40s (Core)**: varied pacing. Mix 2-4 second shots. Alternate dense and breathing room.
- **40-55s (Climax)**: accelerating pacing. Shorter shots, faster transitions.
- **55-60s (Resolution)**: decelerate. Hold the final frame 2-3 seconds.

### Breathing Room Rule
After every "dense" moment (multiple elements animating, fast cuts), include a "breath" -- a 1-2 second hold where nothing new animates and the viewer can absorb. Ratio: roughly 1 second of breath per 3-4 seconds of motion.

---

## 12. Production Quality Checklist

### Pre-Render Verification
- [ ] All springs measured with `measureSpring()` to confirm they settle within their Sequence duration
- [ ] No `<img>` tags -- only Remotion's `<Img>` component (waits for load)
- [ ] All async operations wrapped in `delayRender()` / `continueRender()`
- [ ] Frame rate is 30fps and all timing calculations use `fps` variable, not hardcoded 30
- [ ] Resolution is 1080x1920 for vertical, 1920x1080 for horizontal
- [ ] `extrapolateRight: "clamp"` on all `interpolate()` calls to prevent overshoot
- [ ] No CSS animations or CSS transitions -- all motion via `spring()` or `interpolate()`

### Visual Quality
- [ ] Text contrast ratio meets WCAG AA (4.5:1 minimum for body text)
- [ ] No single-frame flickers at scene boundaries
- [ ] Transitions overlap correctly (check math: total frames = sum of scenes - sum of transitions)
- [ ] Background is never pure black (#000000) or pure white (#ffffff)
- [ ] All images and video assets are at least 1080p resolution

### Export Settings
- Codec: H.264 for web delivery, ProRes 422 for archive/editing
- Frame rate: match composition fps exactly (30fps -> export 30fps)
- Resolution: 1080x1920 (vertical) or 1920x1080 (horizontal), never scaled
- Quality: CRF 18 or lower for final output
- Audio: AAC 192kbps minimum if audio track present

---

## Quick Reference: Remotion Spring Presets

```typescript
// Copy these into your project and use consistently
export const springs = {
  // Default: cards, containers, backgrounds
  smooth: { damping: 200 },
  // Small elements: badges, icons, labels
  snappy: { damping: 20, stiffness: 200 },
  // Emphasis moments only (1-2 per scene max)
  bouncy: { damping: 8 },
  // Large/heavy elements: full-screen, hero images
  heavy: { damping: 15, stiffness: 80, mass: 2 },
} as const;

// Standard stagger: 8 frames (267ms at 30fps)
export const STAGGER_FRAMES = 8;

// Transition duration: 15 frames (500ms at 30fps)
export const TRANSITION_FRAMES = 15;
```

---

Sources for these rules:
- Material Design motion/duration/easing specifications
- Carbon Design System motion guidelines
- Nielsen Norman Group animation duration research
- Disney's 12 Principles of Animation adapted for motion graphics
- School of Motion transition techniques
- Platform-specific safe zone specifications (TikTok, Instagram, YouTube)
- Chromatic/Storybook animation timing guidelines
