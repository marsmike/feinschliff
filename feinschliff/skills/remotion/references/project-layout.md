# Project Layout

Every Remotion video project follows this directory structure.

```
<project>/
├── docs/
│   ├── STORYBOARD.md              # Phase 1 output
│   ├── VERIFICATION_REPORT.md     # Phase 5 output
│   └── storyboard/                # Concept images + eval keyframes
├── public/                        # Audio files (vo-beat*.mp3)
├── src/
│   ├── index.ts, Root.tsx         # Remotion entry points
│   ├── theme.ts                   # Design tokens
│   ├── timing.ts                  # Beat timing manifest
│   └── scenes/                    # Scene[N].tsx + MainVideo.tsx
├── out/                           # Renders + eval keyframes
└── CLAUDE.md                      # Project instructions
```

## Reference Index

| Phase | Primary Reference | Supporting References |
|-------|-------------------|----------------------|
| 1 Storyboard | [storyboard.md](storyboard.md) | [narrative-structures.md](narrative-structures.md), [visualization-reasoning.md](visualization-reasoning.md), [marketing-concepts.md](marketing-concepts.md), [beat-sheet-template.md](beat-sheet-template.md), [visual-storyboard-template.md](visual-storyboard-template.md), [animation-vocabulary.md](animation-vocabulary.md) |
| 2 Audio | [audio.md](audio.md) | [timing-manifest-template.md](timing-manifest-template.md), [audio-sync-patterns.md](audio-sync-patterns.md) |
| 3 Build | [build.md](build.md) | [design-system.md](design-system.md), [components.md](components.md), [components-extended.md](components-extended.md), [scene-templates.md](scene-templates.md), [animation-hooks.md](animation-hooks.md), [motion-design-rules.md](motion-design-rules.md), [color-script-rules.md](color-script-rules.md), [backgrounds.md](backgrounds.md), [patterns.md](patterns.md), [transition-catalog.md](transition-catalog.md), [elevenlabs-audio.md](elevenlabs-audio.md), [claude-md-template.md](claude-md-template.md), [official/](official/) |
| 4 Eval | [eval.md](eval.md) | — |
| 5 Verify | [verify.md](verify.md) | [verification-template.md](verification-template.md) |
