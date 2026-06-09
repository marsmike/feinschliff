# Animation Hooks & Utilities

Custom animation primitives for the design system. Use these alongside the spring presets and stagger patterns from [patterns.md](patterns.md).

## useSlideIn

Slide + fade in from a direction. Returns `{ opacity, transform }` style object.

```tsx
import { interpolate, Easing } from "remotion";

const useSlideIn = (
  frame: number,
  delay: number,
  duration = 20,
  from: "left" | "right" | "bottom" = "bottom",
  distance = 40
) => {
  const progress = interpolate(frame - delay, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const offset = (1 - progress) * distance;
  const transform =
    from === "left"
      ? `translateX(${-offset}px)`
      : from === "right"
        ? `translateX(${offset}px)`
        : `translateY(${offset}px)`;
  return { opacity: progress, transform };
};
```

Usage: `const style = useSlideIn(frame, beat.titleIn, 25, "bottom", 30);`

## useSlideOut

Slide + fade out to a direction. Returns `{ opacity, transform }` style object.

```tsx
const useSlideOut = (
  frame: number,
  start: number,
  duration = 15,
  to: "left" | "right" | "top" = "top",
  distance = 60
) => {
  const progress = interpolate(frame - start, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const offset = progress * distance;
  const transform =
    to === "left"
      ? `translateX(${-offset}px)`
      : to === "right"
        ? `translateX(${offset}px)`
        : `translateY(${-offset}px)`;
  return { opacity: 1 - progress, transform };
};
```

## breathe

Subtle scale oscillation for a "living" feel on static cards/text.

```tsx
const breathe = (frame: number, speed = 0.015, amount = 0.003) =>
  1 + Math.sin(frame * speed) * amount;

// Usage:
// style={{ transform: `scale(${breathe(frame)})` }}
```

## glowPulse

Pulsing box-shadow glow effect for emphasis.

```tsx
const glowPulse = (frame: number, color: string, speed = 0.05) => {
  const intensity = 10 + Math.sin(frame * speed) * 8;
  return `0 0 ${intensity}px ${color}40`;
};

// Usage:
// style={{ boxShadow: glowPulse(frame, theme.green) }}
```

## FloatingDots

Ambient background component — slow-moving translucent dots for depth.

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { theme } from "../theme";

const FloatingDots: React.FC = () => {
  const frame = useCurrentFrame();
  const dots = Array.from({ length: 20 }, (_, i) => ({
    x: (i * 137.5) % 100,
    y: (i * 73.1) % 100,
    size: 2 + (i % 3),
    speed: 0.3 + (i % 5) * 0.1,
    opacity: 0.05 + (i % 4) * 0.02,
  }));

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {dots.map((dot, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${dot.x}%`,
            top: `${(dot.y + frame * dot.speed * 0.05) % 110 - 5}%`,
            width: dot.size,
            height: dot.size,
            borderRadius: "50%",
            backgroundColor: theme.muted,
            opacity: dot.opacity + Math.sin(frame * 0.02 + i) * 0.01,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};
```

## Beat-Driven Timing Pattern

Define narration beats as frame timestamps, then use `useSlideIn`/`useSlideOut` keyed to beats. This is the core pattern for voice-over synced videos:

```tsx
const beat = {
  titleIn: 0,
  concept: fps * 3,
  detail: fps * 8,
  transition: fps * 12,
  end: fps * 15,
};

// Phase visibility: element appears at concept, exits before transition
{frame >= beat.concept && frame < beat.transition && (
  <div style={useSlideIn(frame, beat.concept, 20, "bottom")}>
    <Card>...</Card>
  </div>
)}

// Or use the <Beat> component (see components.md) for declarative version:
<Beat enter={beat.concept} exit={beat.transition - 5}>
  <Card>...</Card>
</Beat>
```

This pattern replaces complex `<Sequence>` nesting with explicit frame-range visibility + animation hooks. Each "beat" maps to a narration timestamp.

## useCountUp

Animate a number from `from` to `to` over a frame range. Returns a formatted string (localized integer or fixed decimals).

```tsx
const useCountUp = (
  frame: number,
  delay: number,
  duration: number,
  from: number,
  to: number,
  decimals = 0
) => {
  const progress = interpolate(frame - delay, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const value = from + (to - from) * progress;
  return decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString();
};
```

Usage: `const stars = useCountUp(frame, beat.statsIn, 40, 0, 13592);`

## useDrawLine

Animate SVG path drawing via `strokeDasharray` / `strokeDashoffset`. Returns style props to spread onto a `<path>` element.

```tsx
const useDrawLine = (
  frame: number,
  delay: number,
  duration: number,
  pathLength: number
) => {
  const progress = interpolate(frame - delay, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  return {
    strokeDasharray: pathLength,
    strokeDashoffset: pathLength * (1 - progress),
  };
};
```

Usage:

```tsx
<svg>
  <path
    d="M 0 100 Q 200 0 400 100"
    stroke={theme.green}
    strokeWidth={3}
    fill="none"
    {...useDrawLine(frame, beat.chartIn, 45, 520)}
  />
</svg>
```

## useRevealWords

Reveal text word-by-word with staggered opacity. Returns an array of `{ word, opacity }` objects for rendering.

```tsx
const useRevealWords = (
  text: string,
  frame: number,
  delay: number,
  framesPerWord = 4
) => {
  const words = text.split(" ");
  return words.map((word, i) => {
    const wordDelay = delay + i * framesPerWord;
    const opacity = interpolate(frame - wordDelay, [0, framesPerWord], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return { word, opacity };
  });
};
```

Usage:

```tsx
<p style={{ display: "flex", gap: 8 }}>
  {useRevealWords("Ship faster with Remotion", frame, beat.headlineIn).map(
    ({ word, opacity }, i) => (
      <span key={i} style={{ opacity }}>
        {word}
      </span>
    )
  )}
</p>
```
