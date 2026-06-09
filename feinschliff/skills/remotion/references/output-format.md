# Output Format

The `.storyboard.md` format is both human-readable and machine-parseable:

```
video.storyboard.md          <- YAML frontmatter + scene-by-scene markdown
frames/
  scene-001.jpg              <- Keyframe at midpoint of scene 1
  scene-002.jpg              <- Keyframe at midpoint of scene 2
  ...
```

## YAML Frontmatter

```yaml
---
title: "Video Title"
duration_seconds: 19
resolution: "1080x1920"
fps: 30
style:
  visual_style: "clean, modern, minimalist"
  color_palette: ["#005691", "#ea0016", "#22c55e"]
  typography: "Inter bold, JetBrains Mono for data"
  mood: "playful, product-focused"
audio:
  has_voiceover: true
  voiceover_language: "en"
  voiceover_tone: "friendly, conversational"
  has_music: false
  has_sfx: true
content:
  type: "product_demo"
  framework: "Before-After"
  key_message: "Bosch GlassVAC cleans windows 40x faster"
---
```

## Per-Scene Breakdown

```markdown
### Scene 1: Hook (0:00 - 0:02, 2s)
**Thumbnail**: ![scene-001](./frames/scene-001.jpg)

#### Visual
- **Shot Type**: wide
- **Camera Movement**: static
- **Subject**: Large window emoji centered, title text below
- **Background**: Radial gradient, Bosch blue center glow
- **Text On Screen**: "Window Cleaning" / "The Old Way"
- **Graphics/Animation**: Spring entrance, floating decorative dots
- **Layout**: Top 30% empty, content centered, bottom 30% badge

#### Audio
- **Voiceover**: "Window cleaning... the old way."
- **Music**: none
- **SFX**: none

#### Analysis
- **Narrative Purpose**: Hook -- stop the scroll, establish topic
- **Emotional Beat**: Curiosity, slight tension
- **Sales Element**: hook
- **Transition Out**: fade to ->
```

## Storyboard-to-Remotion Mapping

| Storyboard Field | Remotion Equivalent |
|---|---|
| `style.color_palette` | `src/theme.ts` color tokens |
| `style.typography` | Font loading in theme |
| Scene timestamps | `src/timing.ts` beat ranges |
| `audio.voiceover` text | TTS input for audio phase |
| `visual.layout` | Component positioning |
| `visual.graphics_animation` | Animation implementation |
| `analysis.transition_out` | xfade transition type |

## Cost

| Video Length | Gemini Flash Cost | Notes |
|---|---|---|
| < 30s | ~$0.001 | Short ads, demos |
| 1-5 min | ~$0.01 | Explainers, tutorials |
| 5-15 min | ~$0.03 | Long-form content |

## Tips

- Gemini processes video natively -- no need to pre-extract frames
- Short videos (< 30s) produce the most accurate scene detection
- For longer videos, consider splitting: `ffmpeg -ss START -to END -i input.mp4 clip.mp4`
- Use `--no-frames` for faster processing when you only need the text breakdown
- The generated `.storyboard.md` can be committed to git alongside your Remotion project
