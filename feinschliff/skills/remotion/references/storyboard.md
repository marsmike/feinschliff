
# Remotion Storyboard Creator

Turn concepts into structured, approved storyboards using Claude's visualization reasoning. This skill determines the best way to visually explain an idea, then creates a detailed beat sheet that drives the entire video production.

## Storyboard Format

All storyboards use the `.storyboard.md` format defined in [visual-storyboard-template.md](visual-storyboard-template.md):
- **YAML frontmatter** — structured metadata (style, colors, audio, content type, framework)
- **Per-scene sections** — Visual (shot type, layout, text, animation), Audio (VO transcript), Analysis (narrative purpose, sales element, visualization reasoning)
- **Inline thumbnails** — AI-generated concept images (Phase 1) or extracted keyframes (Phase 0/3.5) alongside each scene

This format is shared with Phase 0 (analyze) (reverse-engineering existing videos) and `remotion-eval` (comparing renders against the spec).

## Process

### Step 0: Reference Analysis (optional)

If reference videos were analyzed with Phase 0 (analyze) (Phase 0), read the `.storyboard.md` files in `docs/` to understand:
- Scene structure and pacing from successful videos
- Color palettes and visual styles that work
- Narrative frameworks (PAS, AIDA, Before-After) used in the genre
- Typical scene durations and transition patterns

Use these as informed starting points, not rigid templates.

### Step 1: Concept Discussion

Ask clarifying questions one at a time to understand:
- What topic/concept needs explaining
- Who is the target audience
- Desired video length (~30s, ~60s, ~2min)
- Key concepts that must be covered
- Tone (educational, casual, technical, inspirational)
- **Visual style / brand** — if the user wants a specific company's look (e.g., "Apple-style", "Linear-style"), fetch the brand's DESIGN.md from awesome-design-md and apply it to the theme. See [design-system.md](design-system.md) § Brand Design Systems.

### Step 2: Narrative Structure Proposals

Propose 2-3 different narrative approaches. Read [narrative-structures.md](narrative-structures.md) for the catalog of structures.
Read [marketing-concepts.md](marketing-concepts.md) for proven short-form ad concepts (transformation reveal, kinetic typography, enemy personification, etc.).

For each option, describe:
- The story flow (how the narrative unfolds)
- The emotional arc (how the viewer's engagement changes)
- Why this structure fits the topic

Present options and let the user choose.

### Step 3: Visualization Approach Proposals (Per Scene)

For each scene in the chosen narrative, use Claude's visualization reasoning:

1. Identify the concept being communicated
2. Determine which visual type best represents it
3. Explain the reasoning

Read [visualization-reasoning.md](visualization-reasoning.md) for the concept-to-visual mapping guide.

Present 2-3 visualization approaches for the overall video style, then apply per-scene. Let the user choose.

### Step 4: Beat Sheet Generation

Generate the production storyboard using the beat sheet format. Read [beat-sheet-template.md](beat-sheet-template.md) for the exact format.

Each beat includes:
- Story moment description
- Concept being communicated
- Visualization reasoning (why this visual type)
- Visual type (flowchart, timeline, diagram, etc.)
- Component mapping (Remotion components to use)
- Animation description (how things move/appear) — **Animation descriptions MUST use names from [animation-vocabulary.md](animation-vocabulary.md).** Do not use free-text animation descriptions. Each vocabulary name maps to a specific implementation the build phase can execute without interpretation.
- Voiceover script (exact words)
- Color plan (dominant/secondary/accent per scene — follow the color plan algorithm from color-script-rules.md)
- Estimated duration

### Step 5: Write Storyboard Document

This is an **atomic step** — the storyboard document and its concept images are created together as a single deliverable. Do not generate images without writing the document, and do not write the document without generating images.

**5a. Create output directory and generate concept images:**

```bash
mkdir -p docs/storyboard
```

For each scene N, generate two AI concept images using the `feinbild imagine` CLI. Build prompts from the storyboard context — the YAML frontmatter, treatment, beat sheet, and color script all provide detail to feed into the image prompt.

1. **Scene composition** — shows what the scene should look like (layout, elements, colors)

   Build from the scene's Visual section. Use the prompt template:
   ```
   [Style], [shot type]. [Subject description] in [environment/background].
   [Lighting/mood from treatment]. [Specific visual details from beat sheet].
   ```

   Example:
   ```
   Flat illustration storyboard frame, wide shot. A large window icon centered
   on a light background with a soft blue radial glow behind it, a bold title
   below and a red warning badge at the bottom. Decorative circles at corners
   with low opacity. Clean modern consumer-friendly design, playful mood.
   ```

   ```bash
   feinbild imagine --prompt "<built prompt>" --provider replicate --aspect-ratio "<from YAML resolution>" --out "docs/storyboard/scene-N-composition.png"
   ```

2. **Concept illustration** — illustrates the idea being communicated

   Build from the scene's Analysis section + narrative context:
   ```
   [Style], [composition type]. [What the concept shows — narrative purpose].
   [Key visual elements that communicate the idea]. [Mood/emotional beat].
   [Dominant colors described as objects, not hex codes].
   ```

   Example:
   ```
   Professional infographic illustration, centered composition. The frustration
   of old-fashioned window cleaning shown through cleaning tools — a bucket,
   squeegee, and cloth next to a streaky dirty window. Mood of dread and
   tedium. Muted blue and red tones on a light background.
   ```

   ```bash
   feinbild imagine --prompt "<built prompt>" --provider replicate --aspect-ratio "<from YAML resolution>" --out "docs/storyboard/scene-N-concept.png"
   ```

**Prompt rules for Flux Schnell:**
- Write natural sentences, not keyword lists — Flux uses T5 XXL and understands language
- Structure: **Subject + Action + Style + Context** — what comes first gets most attention
- 30-80 words sweet spot — focused prompts beat long keyword dumps
- **Never request text in the image** — Flux garbles text. All text is in the storyboard document.
- **Never put hex codes loosely** — if you must reference colors, attach them to objects: "the badge is #FF0000", not "color palette #FF0000"
- Use spatial composition: "In the foreground... Behind it... In the background..."
- Pull specific details from storyboard sections: subject from Visual, mood from Treatment, concept from Analysis
- Good style keywords: `flat illustration`, `clean geometric shapes`, `soft gradients`, `minimalist vector`, `professional infographic`

**Model selection:**
- Default: `black-forest-labs/flux-schnell` (~0.5s, ~$0.003/image) — fast, cheap, good flat illustration
- High quality: `black-forest-labs/flux-1.1-pro-ultra` (~$0.06/image, 4MP) — best quality, use for final/client-facing storyboards
- Free: Gemini provider with `gemini-2.5-flash-image` (500 free/day)

**Rate limiting:** Replicate allows ~6 requests/minute on low-credit accounts. Generate images sequentially with 10s pauses between calls.

**5b. Write the storyboard document:**

Save the production storyboard to `docs/STORYBOARD.md` in the project directory, embedding references to the generated images. This is the source of truth for the entire production — it drives audio generation, component implementation, and verification.

Use the [visual-storyboard-template.md](visual-storyboard-template.md) format. The document must include these sections **in order**:

1. **YAML frontmatter** — tech specs, style, audio, content metadata (including target_audience, objective, cta)
2. **Logline** — one sentence (max 25 words) capturing what this video is and why it matters
3. **Synopsis** — 3-5 sentences describing the narrative arc (beginning → middle → end) in present tense
4. **Creative Brief** — objective, target audience, key message, CTA, tone, constraints
5. **Treatment** — 1-2 paragraphs describing how the video *feels* when watched (emotional journey, pacing, mood shifts)
6. **Full Script** — all voiceover text as a continuous read with scene markers
7. **Color Script** — one-line emotional color arc across scenes
8. **Scene-by-scene breakdown** — per-scene panels with concept images, Visual, Audio, Analysis, Components

Animation descriptions use [animation-vocabulary.md](animation-vocabulary.md) names.

**5c. Present to user for approval.**

The complete storyboard (document + images) is the deliverable. The storyboard gets updated as scenes are refined through the evaluation loop. Commit to git after approval.

## Key Principles

- **One question at a time** during concept discussion
- **Visualization reasoning per beat** — every concept gets the optimal visual treatment
- **User approval at each stage** — narrative, then visuals, then full storyboard
- **Concrete, not abstract** — describe specific visual elements, not vague ideas
- **Audio-aware** — write VO scripts knowing they will be spoken and timed
- **Every beat MUST have voiceover** — no silent beats. Even short visual punchlines need a punchy VO line (e.g., "One command. Done."). Silent beats cause dead air and disrupt pacing.
