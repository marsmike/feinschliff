# Beat Sheet Template

Use this format for production storyboards. Each scene contains multiple beats. Each beat is a story moment with technical specifications.

---

## Template

~~~markdown
# [Video Title] - Production Storyboard

**Target Duration:** ~[X] seconds
**FPS:** 30
**Resolution:** 1920x1080
**Narrative Structure:** [chosen structure name]
**Visual Approach:** [chosen approach name]

---

## Scene [N]: [Scene Title]

**Scene Duration:** ~[X] seconds
**Scene Purpose:** [What this scene accomplishes in the narrative]

---

### Beat [N.M]: [Story Moment Name]

**What happens:**
[Viewer experience — what they see and understand at this moment]

**Concept:**
[The specific idea/concept being communicated in this beat]

**Visualization Reasoning:**
[Why this visual type best represents the concept — e.g., "A flowchart works
best here because we're showing sequential decision points"]

**Visual Type:**
[Flowchart | Timeline | Comparison | Bar Chart | Network Graph | Layered Diagram |
Sequence Diagram | State Change | Feature List | Title Slide | etc.]

**Components:**
- Primary: [TitleSlide | StepList | NodeGraph | BarChart | Card | etc.]
- Supporting: [Card, Badge, ProgressBar, IconBadge, Typewriter, WordHighlight, etc.]
- Layout: [AbsoluteFill arrangement description]

**Animation:**
[Specific motion — stagger reveal, spring bounce, fade in, transform, draw lines, etc.]
[e.g., "Steps appear sequentially with 10-frame stagger, each with spring animation"]

**Voiceover:**
"[Exact narration text for this beat]"

**Duration:** ~[X] seconds

---
~~~

## Guidelines

- **Scene** = A high-level segment of the video (intro, explanation, demo, outro)
- **Beat** = A single story moment within a scene (one animation, one concept)
- Keep beats atomic: one concept, one visualization, one animation
- VO text should sound natural when spoken aloud
- Duration estimates are approximate — exact timing comes from audio analysis in Phase 2
- Component mapping should reference components from the remotion-build skill's component library
