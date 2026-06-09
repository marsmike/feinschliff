# Storyboard Template (.storyboard.md)

Production storyboard format compatible with both human reading and machine parsing. Uses YAML frontmatter for structured metadata and per-scene breakdowns with visual, audio, and analysis sections.

This format is shared between:
- **remotion-storyboard** (Phase 1) — creating storyboards for new videos
- **Phase 0 (analyze)** — reverse-engineering storyboards from existing videos
- **remotion-eval** — comparing rendered output against the storyboard spec

## Project Structure

```
docs/
├── STORYBOARD.md                      # Production storyboard
├── reference.storyboard.md            # Analyzed reference video (optional)
└── storyboard/
    ├── scene-1-composition.png        # AI-generated scene layout (Phase 1)
    ├── scene-1-concept.png            # AI-generated concept art (Phase 1)
    ├── Scene0_000.png                 # Rendered keyframes (Phase 3.5 eval)
    └── frames/
        └── scene-001.jpg              # Frames from analyzed videos (Phase 0)
```

## Template

~~~markdown
---
title: "{{Video Title}}"
duration_seconds: {{total}}
resolution: "{{WxH}}"
fps: {{fps}}
style:
  visual_style: "{{e.g. clean, modern, minimalist}}"
  color_palette: ["#hex1", "#hex2", "#hex3"]
  typography: "{{font descriptions}}"
  mood: "{{overall mood}}"
audio:
  has_voiceover: true
  voiceover_language: "{{lang}}"
  voiceover_tone: "{{e.g. friendly, authoritative}}"
  has_music: false
  music_style: ""
  has_sfx: false
content:
  type: "{{e.g. product_demo, explainer, tutorial}}"
  framework: "{{e.g. PAS, AIDA, Before-After}}"
  key_message: "{{one-line summary}}"
  target_audience: "{{who is watching}}"
  objective: "{{awareness / conversion / education}}"
  cta: "{{call to action}}"
---

# {{Video Title}} — Production Storyboard

## Logline

{{One sentence (max 25 words) capturing what this video is about and why anyone should care.}}

## Synopsis

{{3-5 sentences describing the narrative arc — beginning, middle, end. How the story unfolds at a high level without scene-by-scene detail. Written in present tense.}}

## Creative Brief

- **Objective**: {{What the video must achieve — awareness, conversion, education, entertainment}}
- **Target Audience**: {{Who is watching — demographics, psychographics, viewing context}}
- **Key Message**: {{The one takeaway the viewer should retain}}
- **Call to Action**: {{What the viewer should do after watching}}
- **Tone**: {{3-5 adjectives — e.g. playful, confident, scroll-stopping}}
- **Constraints**: {{Platform rules, brand guidelines, legal, duration limits}}

## Treatment

{{1-2 paragraphs in present tense describing how the video FEELS when watched. The viewer's emotional journey from first frame to last. Covers pacing, rhythm, visual style, and mood shifts. Reads like a short story — bridges strategy and execution.}}

## Full Script

{{All voiceover text as a continuous read, with scene markers. This allows reviewing the narration as prose, independent of visual specifications.}}

> **[Scene 0]** "{{VO text}}"
> **[Scene 1]** "{{VO text}}"
> ...

## Color Script

{{One-line emotional color arc across scenes:}}
```
Scene 0 → Scene 1 → Scene 2 → ...
#hex       #hex       #hex
mood       mood       mood
```

---

### Scene {{N}}: {{Title}} ({{start}} – {{end}}, {{duration}}s)
**Scene Visual**: ![scene-{{N}}](./storyboard/scene-{{N}}-composition.png)
**Concept Art**: ![concept-{{N}}](./storyboard/scene-{{N}}-concept.png)

#### Visual
- **Shot Type**: {{wide / medium / close-up / screen-recording}}
- **Camera Movement**: {{static / pan / zoom-in / zoom-out}}
- **Subject**: {{what is shown — specific elements, positions, sizes}}
- **Background**: {{color, gradient, texture — include hex codes}}
- **Text On Screen**: "{{exact text visible}}"
- **Graphics/Animation**: {{describe animations, particles, effects with frame ranges}}
- **Layout**: {{where elements sit — top/center/bottom zones, spacing}}

#### Audio
- **Voiceover**: "{{exact transcript}}"
- **Music**: {{description or "none"}}
- **SFX**: {{description or "none"}}

#### Analysis
- **Narrative Purpose**: {{what this scene accomplishes}}
- **Emotional Beat**: {{what the viewer should feel}}
- **Sales Element**: {{hook / problem / agitation / solution / proof / cta / none}}
- **Visualization Type**: {{bar chart / timeline / step list / title slide / etc.}}
- **Visualization Reasoning**: {{why this visual type fits this concept}}
- **Transition Out**: {{cut / fade / slide / dissolve}} to →

#### Components (Remotion)
- {{Component}}: {{specs — font, size, color, animation, spring config}}
- ...

---
~~~

## Field Reference

### YAML Frontmatter

| Field | Type | Purpose |
|---|---|---|
| `style.visual_style` | string | Overall aesthetic — eval agents compare against this |
| `style.color_palette` | array | Hex codes — maps to `theme.ts`, eval checks compliance |
| `style.typography` | string | Font choices — maps to font loading |
| `content.framework` | string | Narrative framework — structures the scene sequence |
| `content.key_message` | string | The one thing the viewer should remember |
| `content.target_audience` | string | Who is watching — demographics, context |
| `content.objective` | string | What the video must achieve |
| `content.cta` | string | What the viewer should do after watching |

### Per-Scene Fields

| Field | Maps to Remotion | Eval checks |
|---|---|---|
| Shot Type | Component composition | Layout matches spec |
| Text On Screen | JSX text content | Text is readable, correct |
| Graphics/Animation | Animation code + spring configs | Progression across keyframes |
| Layout | AbsoluteFill positioning | Zones match, no dead space |
| Voiceover | TTS input (Phase 2) | Audio syncs with visuals |
| Sales Element | Narrative arc position | Emotional flow is coherent |
| Visualization Type | Component choice | Right visual for the concept |
| Transition Out | ffmpeg xfade type | Transitions match spec |

## Guidelines

- **YAML is machine-parsed** — eval agents read `style.color_palette` and check hex codes in renders
- **Voiceover is exact** — the text goes directly to TTS in Phase 2
- **Layout uses zones** — describe in terms of top/center/bottom, not pixel positions
- **Animation uses frame ranges** — "Frame 5-20: bar grows with spring" not "bar animates in"
- **Hex codes are specific** — "#005691" not "blue". Extracted from reference videos or brand guidelines.
- **Images use relative paths** — `![scene-1](./storyboard/scene-1-composition.png)` for portability
- **Adapt image syntax to platform** — use `![[file.png]]` for Obsidian, `![alt](path)` for GitHub/git

## Generating Scene Images

### From AI generation (new videos, Phase 1)

For new storyboards created from ideas, generate concept images before any code exists. Use `/imagine` with Flux Schnell (default — fast and cheap):

```bash
# Scene composition — built from Visual section + YAML style metadata
${CLAUDE_PLUGIN_ROOT}/skills/imagine/scripts/imagine.sh '{"prompt": "flat illustration storyboard panel, <aspect>: <subject>, <layout>, <background>, <visual_style>, color palette <hex codes>, <mood>", "provider": "replicate", "aspect_ratio": "<from resolution>", "output": "docs/storyboard/scene-N-composition.png"}'

# Concept illustration — built from Analysis section + narrative context
${CLAUDE_PLUGIN_ROOT}/skills/imagine/scripts/imagine.sh '{"prompt": "infographic illustration, <aspect>: <narrative_purpose>, <visualization_type>, <emotional_beat>, clean flat illustration, professional infographic", "provider": "replicate", "aspect_ratio": "<from resolution>", "output": "docs/storyboard/scene-N-concept.png"}'
```

Default model: `black-forest-labs/flux-schnell` (~0.5s, ~$0.003/image). For client-facing storyboards: `black-forest-labs/flux-1.1-pro-ultra` (~$0.06/image, best quality, 4MP). Avoid requesting text in prompts — Flux renders text poorly.

### From Remotion compositions (Phase 3.5 eval loop)

After scenes are built in Phase 3, render keyframe stills for evaluation:

```bash
cd <project-dir>
for scene in Scene0 Scene1 ...; do
  TOTAL=<frames>
  for pct in 0 25 50 75 100; do
    FRAME=$((TOTAL * pct / 100))
    [ $pct -eq 100 ] && FRAME=$((TOTAL - 1))
    npx remotion still src/index.ts $scene \
      out/eval/$scene/frame_$(printf '%03d' $pct).png \
      --frame=$FRAME --scale=0.5 --quiet
  done
done
```

### From existing videos (Phase 0 analysis)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/remotion/scripts/video_to_storyboard.py \
  path/to/video.mp4 docs/reference.storyboard.md
```

Frames are automatically extracted at scene midpoints into `frames/`.
