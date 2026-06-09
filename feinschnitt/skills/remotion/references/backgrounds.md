# Background Components for Remotion Videos

Professional, layerable background components to replace flat `#0a0a0f` backgrounds. All components use `AbsoluteFill` and are designed to be stacked in layers.

---

## 1. Gradient Backgrounds

### `RadialGradientBg`

Radial gradient with configurable center position.

```tsx
import { AbsoluteFill } from "remotion";

interface RadialGradientBgProps {
  color1: string; // Inner color
  color2: string; // Outer color
  centerX?: number; // 0–100, default 50
  centerY?: number; // 0–100, default 50
}

export const RadialGradientBg: React.FC<RadialGradientBgProps> = ({
  color1,
  color2,
  centerX = 50,
  centerY = 50,
}) => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at ${centerX}% ${centerY}%, ${color1}, ${color2})`,
      }}
    />
  );
};
```

**Usage:**
```tsx
<RadialGradientBg color1="#1a1a2e" color2="#0a0a0f" centerX={40} centerY={35} />
```

---

### `LinearGradientBg`

Linear gradient with configurable angle.

```tsx
import { AbsoluteFill } from "remotion";

interface LinearGradientBgProps {
  from: string; // Start color
  to: string;   // End color
  angle?: number; // Degrees, default 160
}

export const LinearGradientBg: React.FC<LinearGradientBgProps> = ({
  from,
  to,
  angle = 160,
}) => {
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${angle}deg, ${from}, ${to})`,
      }}
    />
  );
};
```

**Usage:**
```tsx
<LinearGradientBg from="#0f172a" to="#020617" angle={160} />
```

---

### `AnimatedGradientBg`

Slowly rotating three-color gradient using Remotion's `interpolate()` — no CSS animations.

```tsx
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";

interface AnimatedGradientBgProps {
  color1: string;
  color2: string;
  color3: string;
  speed?: number; // Full rotation duration in frames, default 600
}

export const AnimatedGradientBg: React.FC<AnimatedGradientBgProps> = ({
  color1,
  color2,
  color3,
  speed = 600,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const angle = interpolate(frame, [0, speed], [0, 360], {
    extrapolateRight: "wrap",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${angle}deg, ${color1}, ${color2}, ${color3})`,
      }}
    />
  );
};
```

**Usage:**
```tsx
<AnimatedGradientBg color1="#1a1a2e" color2="#0d1117" color3="#0a0a0f" speed={900} />
```

---

## 2. Grid & Dot Patterns

### `DotGridBg`

CSS `radial-gradient`-based dot pattern overlay.

```tsx
import { AbsoluteFill } from "remotion";

interface DotGridBgProps {
  dotColor?: string;  // Default: "rgba(255,255,255,0.15)"
  dotSize?: number;   // Dot radius in px, default 1
  spacing?: number;   // Grid cell size in px, default 24
}

export const DotGridBg: React.FC<DotGridBgProps> = ({
  dotColor = "rgba(255,255,255,0.15)",
  dotSize = 1,
  spacing = 24,
}) => {
  return (
    <AbsoluteFill
      style={{
        backgroundImage: `radial-gradient(circle, ${dotColor} ${dotSize}px, transparent ${dotSize}px)`,
        backgroundSize: `${spacing}px ${spacing}px`,
      }}
    />
  );
};
```

**Usage:**
```tsx
<DotGridBg dotColor="rgba(163,230,53,0.2)" dotSize={1.5} spacing={28} />
```

---

### `LineGridBg`

CSS `linear-gradient`-based line grid (horizontal and vertical lines).

```tsx
import { AbsoluteFill } from "remotion";

interface LineGridBgProps {
  lineColor?: string; // Default: "rgba(255,255,255,0.06)"
  spacing?: number;   // Grid cell size in px, default 40
}

export const LineGridBg: React.FC<LineGridBgProps> = ({
  lineColor = "rgba(255,255,255,0.06)",
  spacing = 40,
}) => {
  return (
    <AbsoluteFill
      style={{
        backgroundImage: [
          `linear-gradient(to right, ${lineColor} 1px, transparent 1px)`,
          `linear-gradient(to bottom, ${lineColor} 1px, transparent 1px)`,
        ].join(", "),
        backgroundSize: `${spacing}px ${spacing}px`,
      }}
    />
  );
};
```

**Usage:**
```tsx
<LineGridBg lineColor="rgba(139,92,246,0.12)" spacing={48} />
```

---

## 3. Decorative Elements

### `Vignette`

Radial gradient that darkens the edges of the frame, focusing attention to the center.

```tsx
import { AbsoluteFill } from "remotion";

interface VignetteProps {
  intensity?: number; // 0–1, default 0.6
  color?: string;     // Default: "black"
}

export const Vignette: React.FC<VignetteProps> = ({
  intensity = 0.6,
  color = "black",
}) => {
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at center, transparent 40%, ${color} 100%)`,
        opacity: intensity,
        pointerEvents: "none",
      }}
    />
  );
};
```

**Usage:**
```tsx
<Vignette intensity={0.5} />
```

---

### `NoiseOverlay`

Tiling noise texture for film-grain texture. Requires `public/noise.png` in your Remotion project.

```tsx
import { AbsoluteFill, staticFile } from "remotion";

interface NoiseOverlayProps {
  opacity?: number; // 0–1, default 0.08
}

export const NoiseOverlay: React.FC<NoiseOverlayProps> = ({
  opacity = 0.08,
}) => {
  return (
    <AbsoluteFill
      style={{
        backgroundImage: `url(${staticFile("noise.png")})`,
        backgroundRepeat: "repeat",
        backgroundSize: "256px 256px",
        opacity,
        mixBlendMode: "overlay",
        pointerEvents: "none",
      }}
    />
  );
};
```

> **Note:** Requires `public/noise.png` in your Remotion project. Generate one at [noisetexture.app](https://noisetexture.app) or use any seamless grayscale noise image.

**Usage:**
```tsx
<NoiseOverlay opacity={0.06} />
```

---

### `AccentGlow`

Large blurred colored circle for ambient light / color accent. Uses CSS `filter: blur()`.

```tsx
import { AbsoluteFill } from "remotion";

interface AccentGlowProps {
  color: string;    // Glow color, e.g. "#a3e635"
  x?: number;      // Horizontal position 0–100, default 50
  y?: number;      // Vertical position 0–100, default 50
  size?: number;   // Diameter in px, default 600
  blur?: number;   // Blur radius in px, default 120
  opacity?: number; // 0–1, default 0.35
}

export const AccentGlow: React.FC<AccentGlowProps> = ({
  color,
  x = 50,
  y = 50,
  size = 600,
  blur = 120,
  opacity = 0.35,
}) => {
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: `${x}%`,
          top: `${y}%`,
          width: size,
          height: size,
          transform: "translate(-50%, -50%)",
          borderRadius: "50%",
          background: color,
          filter: `blur(${blur}px)`,
          opacity,
        }}
      />
    </AbsoluteFill>
  );
};
```

**Usage:**
```tsx
<AccentGlow color="#a3e635" x={70} y={30} size={700} blur={150} opacity={0.3} />
```

---

## 4. Recommended Layering Guide

Stack components back-to-front in this order for best results:

```
1. Base gradient     — sets the overall color palette
2. Structural pattern — adds depth and texture (dots or grid)
3. Accent glow       — adds a focal point or color accent
4. Vignette          — frames the composition, darkens edges
5. Content           — your actual video content
```

### Complete JSX Example

```tsx
import { AbsoluteFill, Composition } from "remotion";
import {
  RadialGradientBg,
  DotGridBg,
  AccentGlow,
  Vignette,
  NoiseOverlay,
} from "./backgrounds";

export const MyScene: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Layer 1: Base gradient */}
      <RadialGradientBg
        color1="#1a1a2e"
        color2="#0a0a0f"
        centerX={50}
        centerY={40}
      />

      {/* Layer 2: Structural pattern */}
      <DotGridBg
        dotColor="rgba(163,230,53,0.15)"
        dotSize={1}
        spacing={24}
      />

      {/* Layer 3: Accent glow */}
      <AccentGlow
        color="#a3e635"
        x={65}
        y={25}
        size={600}
        blur={140}
        opacity={0.25}
      />

      {/* Layer 4: Vignette */}
      <Vignette intensity={0.55} />

      {/* Optional: noise for texture */}
      <NoiseOverlay opacity={0.05} />

      {/* Layer 5: Content */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <h1 style={{ color: "white", fontSize: 80 }}>Your Content Here</h1>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

---

## 5. Theme-Matched Presets

| Preset | Gradient | Pattern | Glow Color | Vibe |
|--------|----------|---------|------------|------|
| `tech-dark` | Radial `#1a1a2e` → `#0a0a0f` | DotGrid | Green `#a3e635` | Hacker, dev tools |
| `midnight` | Linear 160° `#0f172a` → `#020617` | LineGrid | Purple `#8b5cf6` | Deep, thoughtful |
| `warm-dark` | Radial `#1c1917` → `#0c0a09` | DotGrid | Orange `#fb923c` | Creative, warm |
| `clean-light` | Linear 180° `#f8fafc` → `#e2e8f0` | None | Blue `#3b82f6` | SaaS, product |

### Preset Implementations

**`tech-dark`**
```tsx
<RadialGradientBg color1="#1a1a2e" color2="#0a0a0f" />
<DotGridBg dotColor="rgba(163,230,53,0.18)" spacing={24} />
<AccentGlow color="#a3e635" x={70} y={20} size={700} opacity={0.25} />
<Vignette intensity={0.55} />
```

**`midnight`**
```tsx
<LinearGradientBg from="#0f172a" to="#020617" angle={160} />
<LineGridBg lineColor="rgba(139,92,246,0.1)" spacing={48} />
<AccentGlow color="#8b5cf6" x={30} y={70} size={800} opacity={0.2} />
<Vignette intensity={0.6} />
```

**`warm-dark`**
```tsx
<RadialGradientBg color1="#1c1917" color2="#0c0a09" centerX={45} centerY={40} />
<DotGridBg dotColor="rgba(251,146,60,0.15)" spacing={28} />
<AccentGlow color="#fb923c" x={60} y={30} size={650} opacity={0.22} />
<Vignette intensity={0.5} />
```

**`clean-light`**
```tsx
<LinearGradientBg from="#f8fafc" to="#e2e8f0" angle={180} />
<AccentGlow color="#3b82f6" x={80} y={10} size={500} blur={160} opacity={0.15} />
<Vignette intensity={0.15} color="#94a3b8" />
```
