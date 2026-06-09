# Reusable Components

Progressive disclosure: primitives -> compositions -> scene templates. Build up from small pieces.

All components use the theme from `src/theme.ts`. Import it:

```typescript
import { theme } from "../theme";
```

---

## Layer 0: Official Components (from remotion-dev/skills)

These are battle-tested components from the official Remotion skills. Copy into your project's `src/components/`.

### Typewriter

Character-by-character text reveal with blinking cursor.

```tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { theme } from "../theme";

const getTypedText = (text: string, frame: number, framesPerChar = 2) => {
  const charsVisible = Math.floor(frame / framesPerChar);
  return text.slice(0, charsVisible);
};

const Cursor: React.FC<{ color?: string }> = ({ color = theme.green }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame % 16, [0, 8, 8, 16], [1, 1, 0, 0]);
  return (
    <span style={{ opacity, color, fontWeight: 400 }}>|</span>
  );
};

export const Typewriter: React.FC<{
  text: string;
  framesPerChar?: number;
  fontSize?: number;
  color?: string;
  cursorColor?: string;
  delay?: number;
}> = ({ text, framesPerChar = 2, fontSize = 24, color = theme.green, cursorColor, delay = 0 }) => {
  const frame = useCurrentFrame();
  const adjustedFrame = Math.max(0, frame - delay);
  const typed = getTypedText(text, adjustedFrame, framesPerChar);
  const done = typed.length >= text.length;

  return (
    <span style={{ fontFamily: theme.fontMono, fontSize, color, whiteSpace: "pre" }}>
      {typed}
      {!done && <Cursor color={cursorColor || color} />}
    </span>
  );
};
```

Usage:
```tsx
<Typewriter text="npx remotion still MyComp frame.png" delay={30} />
```

### WordHighlight

Highlight a word with a colored background that scales in from the left.

```tsx
import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

export const WordHighlight: React.FC<{
  word: string;
  color?: string;
  delay?: number;
  durationInFrames?: number;
  fontSize?: number;
}> = ({ word, color = "#a3e63540", delay = 0, durationInFrames = 20, fontSize = 48 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame,
    fps,
    delay,
    durationInFrames,
    config: { damping: 200 },
  });

  const scaleX = Math.max(0, Math.min(1, progress));

  return (
    <span style={{ position: "relative", display: "inline-block" }}>
      <span
        style={{
          position: "absolute",
          left: -4,
          right: -4,
          top: -2,
          bottom: -2,
          backgroundColor: color,
          borderRadius: 4,
          transform: `scaleX(${scaleX})`,
          transformOrigin: "left center",
        }}
      />
      <span style={{ position: "relative", fontSize }}>{word}</span>
    </span>
  );
};
```

### BarChart

Animated bar chart with staggered spring entry.

```tsx
import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

interface BarData {
  label: string;
  value: number;
  color?: string;
}

export const BarChart: React.FC<{
  data: BarData[];
  width?: number;
  height?: number;
  maxValue?: number;
  staggerDelay?: number;
  delay?: number;
}> = ({ data, width = 800, height = 400, maxValue, staggerDelay = 8, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const max = maxValue || Math.max(...data.map((d) => d.value));
  const barWidth = (width - (data.length + 1) * 12) / data.length;

  return (
    <div style={{ width, height, position: "relative", display: "flex", alignItems: "flex-end", gap: 12, padding: "0 12px" }}>
      {data.map((bar, i) => {
        const progress = spring({
          frame,
          fps,
          delay: delay + i * staggerDelay,
          config: { damping: 18, stiffness: 80 },
        });

        const barHeight = (bar.value / max) * (height - 40) * progress;

        return (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", width: barWidth }}>
            <div
              style={{
                width: barWidth,
                height: barHeight,
                backgroundColor: bar.color || theme.green,
                borderRadius: "4px 4px 0 0",
              }}
            />
            <div style={{ fontFamily: theme.fontSans, fontSize: 12, color: theme.muted, marginTop: 8, textAlign: "center" }}>
              {bar.label}
            </div>
          </div>
        );
      })}
    </div>
  );
};
```

Usage:
```tsx
<BarChart
  data={[
    { label: "Jan", value: 120, color: theme.green },
    { label: "Feb", value: 80, color: theme.cyan },
    { label: "Mar", value: 200, color: theme.purple },
  ]}
  delay={30}
/>
```

---

## Layer 1: Design System Primitives

### Card

Dark surface with rounded border. The basic container for everything.

```tsx
import React from "react";
import { theme } from "../theme";

export const Card: React.FC<{
  children: React.ReactNode;
  width?: number | string;
  accent?: string;
  glow?: boolean;
  style?: React.CSSProperties;
}> = ({ children, width, accent = theme.surfaceBorder, glow = false, style }) => (
  <div
    style={{
      backgroundColor: theme.surface,
      border: `1px solid ${accent}`,
      borderRadius: theme.radius,
      padding: theme.padding,
      width,
      boxShadow: glow ? `0 0 20px ${accent}40` : undefined,
      ...style,
    }}
  >
    {children}
  </div>
);
```

### Badge

Small label pill for status indicators, tags, categories.

```tsx
import React from "react";
import { theme } from "../theme";

export const Badge: React.FC<{
  label: string;
  color?: string;
  icon?: string;
}> = ({ label, color = theme.green, icon }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      backgroundColor: `${color}20`,
      color,
      padding: "4px 12px",
      borderRadius: 6,
      fontFamily: theme.fontMono,
      fontSize: 14,
      fontWeight: 600,
      letterSpacing: "0.05em",
      textTransform: "uppercase",
    }}
  >
    {icon && <span>{icon}</span>}
    {label}
  </div>
);
```

### ProgressBar

Horizontal fill bar with label and percentage.

```tsx
import React from "react";
import { theme } from "../theme";

export const ProgressBar: React.FC<{
  progress: number; // 0-1
  label?: string;
  color?: string;
  width?: number | string;
}> = ({ progress, label, color = theme.green, width = "100%" }) => (
  <div style={{ width }}>
    {label && (
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontFamily: theme.fontSans,
          fontSize: 14,
          color: theme.text,
          marginBottom: 8,
        }}
      >
        <span>{label}</span>
        <span style={{ color: theme.muted }}>{Math.round(progress * 100)}%</span>
      </div>
    )}
    <div
      style={{
        height: 8,
        backgroundColor: `${theme.muted}30`,
        borderRadius: 4,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${progress * 100}%`,
          backgroundColor: color,
          borderRadius: 4,
        }}
      />
    </div>
  </div>
);
```

### IconBadge

Small colored square with icon — for category indicators.

```tsx
import React from "react";
import { theme } from "../theme";

export const IconBadge: React.FC<{
  icon: string;
  color?: string;
  size?: number;
}> = ({ icon, color = theme.purple, size = 36 }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: 8,
      backgroundColor: `${color}30`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: size * 0.5,
    }}
  >
    {icon}
  </div>
);
```

### ColorText

Text with individually colored words — for emphasis in titles.

```tsx
import React from "react";
import { theme } from "../theme";

type TextSegment = string | { text: string; color: string };

export const ColorText: React.FC<{
  segments: TextSegment[];
  fontSize?: number;
  fontFamily?: string;
}> = ({ segments, fontSize = 48, fontFamily = theme.fontSans }) => (
  <div style={{ fontFamily, fontSize, fontWeight: 600, color: theme.text, lineHeight: 1.3 }}>
    {segments.map((seg, i) =>
      typeof seg === "string" ? (
        <span key={i}>{seg}</span>
      ) : (
        <span key={i} style={{ color: seg.color }}>
          {seg.text}
        </span>
      )
    )}
  </div>
);
```

### Beat

Declarative wrapper for beat-driven enter/exit animations. The core timing component for voice-over synced videos. Replaces manual frame-range checks + useSlideIn/useSlideOut.

```tsx
import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";

export const Beat: React.FC<{
  children: React.ReactNode;
  enter: number;       // frame to start entering
  exit?: number;       // frame to start exiting (omit = stay forever)
  enterDuration?: number;
  exitDuration?: number;
  enterFrom?: "left" | "right" | "bottom";
  exitTo?: "left" | "right" | "top";
  distance?: number;
}> = ({
  children,
  enter,
  exit,
  enterDuration = 20,
  exitDuration = 15,
  enterFrom = "bottom",
  exitTo = "top",
  distance = 40,
}) => {
  const frame = useCurrentFrame();

  if (frame < enter) return null;
  if (exit && frame > exit + exitDuration) return null;

  const enterProgress = interpolate(frame - enter, [0, enterDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  let exitProgress = 0;
  if (exit && frame >= exit) {
    exitProgress = interpolate(frame - exit, [0, exitDuration], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.in(Easing.cubic),
    });
  }

  const opacity = enterProgress * (1 - exitProgress);
  const enterOffset = (1 - enterProgress) * distance;
  const exitOffset = exitProgress * distance;

  const translateX =
    enterFrom === "left" ? -enterOffset :
    enterFrom === "right" ? enterOffset :
    exitTo === "left" ? -exitOffset :
    exitTo === "right" ? exitOffset : 0;

  const translateY =
    (enterFrom === "bottom" ? enterOffset : 0) +
    (exitTo === "top" ? -exitOffset : 0);

  return (
    <div style={{ opacity, transform: `translate(${translateX}px, ${translateY}px)` }}>
      {children}
    </div>
  );
};
```

Usage with beat timestamps:
```tsx
const beat = { title: 0, cards: fps * 3, transition: fps * 10 };

<Beat enter={beat.title} exit={beat.cards - 5}>
  <TitleSlide segments={[...]} />
</Beat>

<Beat enter={beat.cards} exit={beat.transition} enterFrom="left">
  <StepList steps={steps} />
</Beat>
```

**Note:** `<FadeIn>` is superseded by `<Beat>`. Use `<Beat enter={0}>` for simple fade-in.

---

## Layer 2: Compositions

### TitleSlide

Full-screen title with colored text and optional subtitle.

```tsx
import React from "react";
import { AbsoluteFill } from "remotion";
import { theme } from "../theme";
import { ColorText, TextSegment } from "./ColorText";

export const TitleSlide: React.FC<{
  segments: TextSegment[];
  subtitle?: string;
}> = ({ segments, subtitle }) => (
  <AbsoluteFill
    style={{
      backgroundColor: theme.bg,
      justifyContent: "center",
      alignItems: "center",
      padding: 80,
    }}
  >
    <div style={{ textAlign: "center", maxWidth: 1400 }}>
      <ColorText segments={segments} fontSize={56} />
      {subtitle && (
        <div
          style={{
            fontFamily: theme.fontSans,
            fontSize: 24,
            color: theme.muted,
            marginTop: 24,
          }}
        >
          {subtitle}
        </div>
      )}
    </div>
  </AbsoluteFill>
);
```

### StepList

Vertical or horizontal list of items with icon badges. Use spring stagger for progressive reveal.

```tsx
import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Card } from "./Card";
import { IconBadge } from "./IconBadge";
import { Badge } from "./Badge";

interface Step {
  icon: string;
  title: string;
  description: string;
  status?: string;
  color?: string;
}

export const StepList: React.FC<{
  steps: Step[];
  direction?: "row" | "column";
  gap?: number;
  staggerDelay?: number;
  delay?: number;
}> = ({ steps, direction = "row", gap = 20, staggerDelay = 8, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: "flex", flexDirection: direction, gap }}>
      {steps.map((step, i) => {
        const progress = spring({
          frame,
          fps,
          delay: delay + i * staggerDelay,
          config: { damping: 200 },
        });

        return (
          <div
            key={i}
            style={{
              flex: direction === "row" ? 1 : undefined,
              opacity: progress,
              transform: `translateY(${(1 - progress) * 30}px)`,
            }}
          >
            <Card accent={step.color || theme.surfaceBorder}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <IconBadge icon={step.icon} color={step.color || theme.purple} />
                <span style={{ fontFamily: theme.fontSans, fontSize: 20, fontWeight: 700, color: theme.text }}>
                  {step.title}
                </span>
              </div>
              <div style={{ fontFamily: theme.fontSans, fontSize: 14, color: theme.muted, marginBottom: 8 }}>
                {step.description}
              </div>
              {step.status && <Badge label={step.status} color={theme.green} icon="✓" />}
            </Card>
          </div>
        );
      })}
    </div>
  );
};
```

### MetricCard

Card with a title, progress bar, and status text.

```tsx
import React from "react";
import { theme } from "../theme";
import { Card } from "./Card";
import { Badge } from "./Badge";
import { ProgressBar } from "./ProgressBar";

export const MetricCard: React.FC<{
  title: string;
  subtitle?: string;
  progress: number;
  progressLabel: string;
  status?: string;
  statusIcon?: string;
  accent?: string;
}> = ({ title, subtitle, progress, progressLabel, status, statusIcon = "✓", accent = theme.green }) => (
  <Card accent={accent} glow>
    {subtitle && <Badge label={subtitle} color={accent} />}
    <div
      style={{
        fontFamily: theme.fontSans,
        fontSize: 28,
        fontWeight: 700,
        color: theme.text,
        margin: "12px 0 20px",
      }}
    >
      {title}
    </div>
    <ProgressBar progress={progress} label={progressLabel} color={accent} />
    {status && (
      <div
        style={{
          fontFamily: theme.fontSans,
          fontSize: 14,
          color: theme.muted,
          marginTop: 12,
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <span style={{ color: accent }}>{statusIcon}</span>
        {status}
      </div>
    )}
  </Card>
);
```

### PipelineFlow

Horizontal or vertical flow of steps connected by arrows.

```tsx
import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";
import { Card } from "./Card";
import { IconBadge } from "./IconBadge";

export interface PipelineStep {
  icon: string;
  title: string;
  description: string;
  color?: string;
}

export const PipelineFlow: React.FC<{
  steps: PipelineStep[];
  direction?: "row" | "column";
  staggerDelay?: number;
  delay?: number;
}> = ({ steps, direction = "row", staggerDelay = 12, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: "flex", flexDirection: direction, alignItems: "center", gap: 0 }}>
      {steps.map((step, i) => {
        const progress = spring({
          frame,
          fps,
          delay: delay + i * staggerDelay,
          config: { damping: 200 },
        });

        return (
          <React.Fragment key={i}>
            <div style={{ flex: 1, opacity: progress, transform: `translateY(${(1 - progress) * 20}px)` }}>
              <Card accent={step.color || theme.surfaceBorder}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                  <IconBadge icon={step.icon} color={step.color || theme.purple} />
                  <span style={{ fontFamily: theme.fontSans, fontSize: 18, fontWeight: 700, color: theme.text }}>{step.title}</span>
                </div>
                <div style={{ fontFamily: theme.fontSans, fontSize: 13, color: theme.muted }}>{step.description}</div>
              </Card>
            </div>
            {i < steps.length - 1 && (
              <div
                style={{
                  fontFamily: theme.fontMono,
                  fontSize: 20,
                  color: theme.green,
                  padding: direction === "row" ? "0 8px" : "8px 0",
                  flexShrink: 0,
                  opacity: progress,
                }}
              >
                {direction === "row" ? "→" : "↓"}
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
```

---

## Layer 3: Scene Templates

Copy and customize these full compositions.

### ExplainerIntro

Title slide with animated fade-in, then subtitle.

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";
import { ColorText, TextSegment } from "../components/ColorText";

export const ExplainerIntro: React.FC<{
  segments: TextSegment[];
  subtitle?: string;
}> = ({ segments, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: { damping: 200 } });
  const subtitleProgress = spring({ frame, fps, delay: Math.round(fps * 0.8), config: { damping: 200 } });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg, justifyContent: "center", alignItems: "center", padding: 80 }}>
      <div style={{ textAlign: "center", maxWidth: 1400, opacity: titleProgress, transform: `translateY(${(1 - titleProgress) * 20}px)` }}>
        <ColorText segments={segments} fontSize={56} />
        {subtitle && (
          <div style={{ opacity: subtitleProgress, fontFamily: theme.fontSans, fontSize: 24, color: theme.muted, marginTop: 24 }}>
            {subtitle}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
```

### ArchitectureDiagram

Orchestrator card at top, connector arrows, child step cards below. Uses spring stagger for animated entry.

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";
import { MetricCard } from "../components/MetricCard";
import { StepList } from "../components/StepList";
import { ColorText, TextSegment } from "../components/ColorText";

interface Step {
  icon: string;
  title: string;
  description: string;
  status?: string;
  color?: string;
}

export const ArchitectureDiagram: React.FC<{
  title: { segments: TextSegment[] };
  orchestrator: { title: string; subtitle: string; progress: number; progressLabel: string; status: string };
  steps: Step[];
}> = ({ title, orchestrator, steps }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({ frame, fps, config: { damping: 200 } });
  const orchProgress = spring({ frame, fps, delay: Math.round(fps * 0.5), config: { damping: 200 } });
  const connectorProgress = spring({ frame, fps, delay: Math.round(fps * 1.2), config: { damping: 200 } });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.bg, padding: 60, justifyContent: "space-between" }}>
      <div style={{ textAlign: "center", opacity: titleProgress }}>
        <ColorText segments={title.segments} fontSize={44} />
      </div>

      <div style={{ display: "flex", justifyContent: "center", opacity: orchProgress, transform: `translateY(${(1 - orchProgress) * 20}px)` }}>
        <MetricCard
          title={orchestrator.title}
          subtitle={orchestrator.subtitle}
          progress={orchestrator.progress}
          progressLabel={orchestrator.progressLabel}
          status={orchestrator.status}
        />
      </div>

      <div style={{ display: "flex", justifyContent: "center", gap: 60, fontFamily: theme.fontMono, fontSize: 14, color: theme.purple, opacity: connectorProgress }}>
        {steps.map((_, i) => (
          <div key={i} style={{ textAlign: "center" }}>
            <div style={{ fontSize: 20 }}>↓</div>
            <div>SPAWN</div>
          </div>
        ))}
      </div>

      <StepList steps={steps} delay={Math.round(fps * 1.8)} />
    </AbsoluteFill>
  );
};
```
