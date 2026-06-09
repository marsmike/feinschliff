# Extended Component Library

High-impact components that build on the core primitives in `components.md`. All use `spring()` or `interpolate()` for animation — never CSS transitions or keyframes.

All components use the theme from `src/theme.ts`. Import it:

```typescript
import { theme } from "../theme";
```

> **TerminalScene** — for embedding *real* CLI recordings (Claude Code, kubectl, npm, …) as composited React, see the dedicated reference at [`components-terminal-scene.md`](components-terminal-scene.md). The recording is produced by the [`cli-recorder`](../../../../cli-recorder/README.md) plugin and consumed here as cast + scene-index data.

---

## CountUp

Animated number counter that interpolates from one value to another with easing. Great for stats, metrics, and hero numbers.

```tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";
import { theme } from "../theme";

export const CountUp: React.FC<{
  from: number;
  to: number;
  delay: number;
  duration: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  fontSize?: number;
}> = ({ from, to, delay, duration, prefix = "", suffix = "", decimals = 0, fontSize = 80 }) => {
  const frame = useCurrentFrame();

  const value = interpolate(frame, [delay, delay + duration], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const formatted = value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return (
    <div
      style={{
        fontFamily: theme.fontSans,
        fontSize,
        fontWeight: 700,
        color: theme.text,
        lineHeight: 1,
        letterSpacing: "-0.02em",
      }}
    >
      {prefix}
      {formatted}
      {suffix}
    </div>
  );
};
```

Usage:
```tsx
// Count from 0 to 1,247,000 over 60 frames, starting at frame 30
<CountUp from={0} to={1247000} delay={30} duration={60} suffix=" users" />

// Percentage with decimals
<CountUp from={0} to={98.6} delay={0} duration={45} suffix="%" decimals={1} fontSize={120} />
```

---

## CodeBlock

Syntax-highlighted code display with line numbers and optional line-by-line reveal. Uses a dark surface with a left accent border.

```tsx
import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";
import { theme } from "../theme";

export const CodeBlock: React.FC<{
  code: string;
  language?: string;
  highlightLines?: number[];
  revealMode?: "all" | "line-by-line";
  revealDelay?: number;
  fontSize?: number;
}> = ({
  code,
  language = "typescript",
  highlightLines = [],
  revealMode = "all",
  revealDelay = 6,
  fontSize = 18,
}) => {
  const frame = useCurrentFrame();
  const lines = code.split("\n");

  const containerOpacity =
    revealMode === "all"
      ? interpolate(frame, [0, 20], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        })
      : 1;

  return (
    <div
      style={{
        opacity: containerOpacity,
        backgroundColor: theme.surface,
        borderRadius: theme.radius,
        borderLeft: `4px solid ${theme.green}`,
        overflow: "hidden",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 20px",
          borderBottom: `1px solid ${theme.surfaceBorder}`,
        }}
      >
        <span
          style={{
            fontFamily: theme.fontMono,
            fontSize: 13,
            color: theme.muted,
            textTransform: "lowercase",
          }}
        >
          {language}
        </span>
      </div>

      {/* Code lines */}
      <div style={{ padding: "16px 0" }}>
        {lines.map((line, i) => {
          const lineNumber = i + 1;
          const isHighlighted = highlightLines.includes(lineNumber);

          const lineOpacity =
            revealMode === "line-by-line"
              ? interpolate(frame, [i * revealDelay, i * revealDelay + 12], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.out(Easing.cubic),
                })
              : 1;

          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                opacity: lineOpacity,
                backgroundColor: isHighlighted ? `${theme.green}12` : "transparent",
                padding: "2px 20px",
              }}
            >
              {/* Line number */}
              <span
                style={{
                  fontFamily: theme.fontMono,
                  fontSize: fontSize * 0.78,
                  color: theme.muted,
                  minWidth: 32,
                  userSelect: "none",
                  flexShrink: 0,
                  paddingTop: 1,
                  opacity: 0.5,
                }}
              >
                {lineNumber}
              </span>

              {/* Code text */}
              <pre
                style={{
                  fontFamily: theme.fontMono,
                  fontSize,
                  color: isHighlighted ? theme.text : `${theme.text}dd`,
                  margin: 0,
                  whiteSpace: "pre",
                  lineHeight: 1.6,
                }}
              >
                {line || " "}
              </pre>
            </div>
          );
        })}
      </div>
    </div>
  );
};
```

Usage:
```tsx
const snippet = `const result = await agent.run({
  model: "claude-opus-4-5",
  tools: [searchTool, writeTool],
  maxSteps: 10,
});`;

// Reveal all at once
<CodeBlock code={snippet} language="typescript" highlightLines={[2, 3]} />

// Line-by-line reveal, one line every 8 frames
<CodeBlock code={snippet} language="typescript" revealMode="line-by-line" revealDelay={8} />
```

---

## NodeGraph

Network of connected nodes with animated edges that draw after nodes appear. Good for architecture diagrams, dependency graphs, and relationship visualizations.

```tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate, Easing } from "remotion";
import { theme } from "../theme";

interface GraphNode {
  id: string;
  label: string;
  icon?: string;
  x: number;
  y: number;
  color?: string;
}

interface GraphEdge {
  from: string;
  to: string;
  label?: string;
}

export const NodeGraph: React.FC<{
  nodes: GraphNode[];
  edges: GraphEdge[];
  staggerDelay?: number;
  delay?: number;
}> = ({ nodes, edges, staggerDelay = 8, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const nodePositions: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n) => {
    nodePositions[n.id] = { x: n.x, y: n.y };
  });

  // All nodes fully appeared by this frame
  const nodesSettleFrame = delay + nodes.length * staggerDelay + 20;

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {/* SVG layer for edges */}
      <svg
        style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", overflow: "visible" }}
      >
        {edges.map((edge, i) => {
          const fromPos = nodePositions[edge.from];
          const toPos = nodePositions[edge.to];
          if (!fromPos || !toPos) return null;

          const dx = toPos.x - fromPos.x;
          const dy = toPos.y - fromPos.y;
          const length = Math.sqrt(dx * dx + dy * dy);

          const edgeProgress = interpolate(
            frame,
            [nodesSettleFrame + i * 6, nodesSettleFrame + i * 6 + 20],
            [1, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            }
          );

          const labelOpacity = interpolate(
            frame,
            [nodesSettleFrame + i * 6 + 20, nodesSettleFrame + i * 6 + 30],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

          const midX = (fromPos.x + toPos.x) / 2;
          const midY = (fromPos.y + toPos.y) / 2;

          return (
            <g key={i}>
              <line
                x1={fromPos.x}
                y1={fromPos.y}
                x2={toPos.x}
                y2={toPos.y}
                stroke={theme.surfaceBorder}
                strokeWidth={2}
                strokeDasharray={length}
                strokeDashoffset={edgeProgress * length}
              />
              {edge.label && (
                <text
                  x={midX}
                  y={midY - 8}
                  textAnchor="middle"
                  fill={theme.muted}
                  fontSize={13}
                  fontFamily={theme.fontMono}
                  opacity={labelOpacity}
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Node cards */}
      {nodes.map((node, i) => {
        const progress = spring({
          frame,
          fps,
          delay: delay + i * staggerDelay,
          config: { damping: 18, stiffness: 120 },
        });

        const nodeColor = node.color || theme.purple;

        return (
          <div
            key={node.id}
            style={{
              position: "absolute",
              left: node.x,
              top: node.y,
              transform: `translate(-50%, -50%) scale(${progress})`,
              opacity: progress,
            }}
          >
            <div
              style={{
                backgroundColor: theme.surface,
                border: `1px solid ${nodeColor}60`,
                borderRadius: theme.radius,
                padding: "12px 16px",
                display: "flex",
                alignItems: "center",
                gap: 8,
                boxShadow: `0 0 16px ${nodeColor}30`,
                whiteSpace: "nowrap",
              }}
            >
              {node.icon && (
                <span style={{ fontSize: 20 }}>{node.icon}</span>
              )}
              <span
                style={{
                  fontFamily: theme.fontSans,
                  fontSize: 15,
                  fontWeight: 600,
                  color: theme.text,
                }}
              >
                {node.label}
              </span>
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
<NodeGraph
  nodes={[
    { id: "api", label: "API Gateway", icon: "🌐", x: 400, y: 100, color: theme.cyan },
    { id: "auth", label: "Auth Service", icon: "🔐", x: 200, y: 280, color: theme.purple },
    { id: "db",   label: "Database",    icon: "🗄️", x: 600, y: 280, color: theme.green },
  ]}
  edges={[
    { from: "api", to: "auth", label: "verify" },
    { from: "api", to: "db",   label: "query" },
  ]}
  delay={10}
  staggerDelay={10}
/>
```

---

## QuoteCard

Large pull-quote with attribution. Uses a left accent border and decorative opening quote mark.

```tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";

export const QuoteCard: React.FC<{
  quote: string;
  author: string;
  role?: string;
  accentColor?: string;
}> = ({ quote, author, role, accentColor = theme.purple }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  const authorProgress = spring({
    frame,
    fps,
    delay: 18,
    config: { damping: 200 },
  });

  return (
    <div
      style={{
        opacity: progress,
        transform: `translateX(${(1 - progress) * -30}px)`,
        borderLeft: `4px solid ${accentColor}`,
        paddingLeft: 32,
        maxWidth: 900,
        position: "relative",
      }}
    >
      {/* Decorative opening quote mark */}
      <div
        style={{
          position: "absolute",
          top: -20,
          left: 20,
          fontFamily: theme.fontSans,
          fontSize: 120,
          color: `${accentColor}20`,
          lineHeight: 1,
          userSelect: "none",
          pointerEvents: "none",
        }}
      >
        "
      </div>

      {/* Quote text */}
      <div
        style={{
          fontFamily: theme.fontSans,
          fontSize: 36,
          fontWeight: 600,
          color: theme.text,
          lineHeight: 1.4,
          marginBottom: 24,
          position: "relative",
        }}
      >
        {quote}
      </div>

      {/* Attribution */}
      <div
        style={{
          opacity: authorProgress,
          transform: `translateY(${(1 - authorProgress) * 10}px)`,
        }}
      >
        <div
          style={{
            fontFamily: theme.fontSans,
            fontSize: 18,
            fontWeight: 700,
            color: theme.text,
          }}
        >
          {author}
        </div>
        {role && (
          <div
            style={{
              fontFamily: theme.fontSans,
              fontSize: 14,
              color: theme.muted,
              marginTop: 4,
            }}
          >
            {role}
          </div>
        )}
      </div>
    </div>
  );
};
```

Usage:
```tsx
<QuoteCard
  quote="The best way to predict the future is to build it."
  author="Alan Kay"
  role="Computer Scientist"
  accentColor={theme.cyan}
/>
```

---

## SplitScreen

Side-by-side comparison layout with spring entrance animation. Left side slides in from left, right from right.

```tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";

export const SplitScreen: React.FC<{
  left: React.ReactNode;
  right: React.ReactNode;
  splitRatio?: number;
  dividerColor?: string;
  leftLabel?: string;
  rightLabel?: string;
}> = ({
  left,
  right,
  splitRatio = 0.5,
  dividerColor = theme.surfaceBorder,
  leftLabel,
  rightLabel,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const leftProgress = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 100 },
  });

  const rightProgress = spring({
    frame,
    fps,
    delay: 6,
    config: { damping: 18, stiffness: 100 },
  });

  const labelStyle: React.CSSProperties = {
    fontFamily: theme.fontMono,
    fontSize: 13,
    fontWeight: 600,
    color: theme.muted,
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    marginBottom: 16,
  };

  return (
    <div style={{ display: "flex", width: "100%", height: "100%", overflow: "hidden" }}>
      {/* Left pane */}
      <div
        style={{
          flex: splitRatio,
          opacity: leftProgress,
          transform: `translateX(${(1 - leftProgress) * -60}px)`,
          display: "flex",
          flexDirection: "column",
          padding: 40,
          overflow: "hidden",
        }}
      >
        {leftLabel && <div style={labelStyle}>{leftLabel}</div>}
        <div style={{ flex: 1 }}>{left}</div>
      </div>

      {/* Divider */}
      <div
        style={{
          width: 1,
          backgroundColor: dividerColor,
          flexShrink: 0,
          alignSelf: "stretch",
          margin: "40px 0",
          opacity: Math.min(leftProgress, rightProgress),
        }}
      />

      {/* Right pane */}
      <div
        style={{
          flex: 1 - splitRatio,
          opacity: rightProgress,
          transform: `translateX(${(1 - rightProgress) * 60}px)`,
          display: "flex",
          flexDirection: "column",
          padding: 40,
          overflow: "hidden",
        }}
      >
        {rightLabel && <div style={labelStyle}>{rightLabel}</div>}
        <div style={{ flex: 1 }}>{right}</div>
      </div>
    </div>
  );
};
```

Usage:
```tsx
<SplitScreen
  leftLabel="Before"
  rightLabel="After"
  splitRatio={0.5}
  left={<CodeBlock code={oldCode} language="typescript" />}
  right={<CodeBlock code={newCode} language="typescript" />}
/>
```

---

## BrowserMockup

Wraps content in a realistic browser chrome frame with traffic light dots and a URL bar.

```tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";

export const BrowserMockup: React.FC<{
  url?: string;
  children: React.ReactNode;
  variant?: "light" | "dark";
}> = ({ url = "localhost:3000", children, variant = "dark" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  const chromeBg = variant === "dark" ? "#1e1e2e" : "#f0f0f5";
  const urlBarBg = variant === "dark" ? "#2a2a3e" : "#ffffff";
  const urlTextColor = variant === "dark" ? theme.muted : "#666";
  const borderColor = variant === "dark" ? "#3a3a4e" : "#d0d0d8";

  return (
    <div
      style={{
        opacity: progress,
        transform: `scale(${0.95 + progress * 0.05})`,
        borderRadius: theme.radius,
        border: `1px solid ${borderColor}`,
        overflow: "hidden",
        boxShadow: "0 24px 64px rgba(0,0,0,0.5)",
      }}
    >
      {/* Browser chrome bar */}
      <div
        style={{
          backgroundColor: chromeBg,
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          borderBottom: `1px solid ${borderColor}`,
        }}
      >
        {/* Traffic light dots */}
        <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
          <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#ff5f57" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#febc2e" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#28c840" }} />
        </div>

        {/* URL bar */}
        <div
          style={{
            flex: 1,
            backgroundColor: urlBarBg,
            borderRadius: 6,
            padding: "5px 12px",
            fontFamily: theme.fontMono,
            fontSize: 13,
            color: urlTextColor,
            border: `1px solid ${borderColor}`,
          }}
        >
          {url}
        </div>
      </div>

      {/* Content area */}
      <div style={{ overflow: "hidden" }}>
        {children}
      </div>
    </div>
  );
};
```

Usage:
```tsx
<BrowserMockup url="https://myapp.com/dashboard" variant="dark">
  <div style={{ backgroundColor: theme.bg, padding: 40, minHeight: 400 }}>
    {/* Your content here */}
    <MetricCard title="Revenue" progress={0.72} progressLabel="$720K of $1M" />
  </div>
</BrowserMockup>
```

---

## AnimatedChecklist

Sequential checklist where each item slides in and then a checkmark draws via SVG path animation.

```tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate, Easing } from "remotion";
import { theme } from "../theme";

const AnimatedCheck: React.FC<{ progress: number; color: string; size: number }> = ({
  progress,
  color,
  size,
}) => {
  // Checkmark path: short left stroke then long right stroke
  const totalLength = 28;
  const dashOffset = interpolate(progress, [0, 1], [totalLength, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      style={{ flexShrink: 0 }}
    >
      <circle
        cx={12}
        cy={12}
        r={10}
        fill={`${color}20`}
        stroke={color}
        strokeWidth={1.5}
        opacity={progress}
      />
      <polyline
        points="7,12 10,15 17,9"
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={totalLength}
        strokeDashoffset={dashOffset}
      />
    </svg>
  );
};

export const AnimatedChecklist: React.FC<{
  items: string[];
  staggerDelay?: number;
  checkColor?: string;
  delay?: number;
}> = ({ items, staggerDelay = 12, checkColor = theme.green, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {items.map((item, i) => {
        const itemFrame = delay + i * staggerDelay;

        // Item slides in
        const slideProgress = spring({
          frame,
          fps,
          delay: itemFrame,
          config: { damping: 200 },
        });

        // Check draws after item appears (offset by 8 frames)
        const checkProgress = interpolate(
          frame,
          [itemFrame + 8, itemFrame + 24],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.out(Easing.cubic),
          }
        );

        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              opacity: slideProgress,
              transform: `translateX(${(1 - slideProgress) * -24}px)`,
            }}
          >
            <AnimatedCheck progress={checkProgress} color={checkColor} size={28} />
            <span
              style={{
                fontFamily: theme.fontSans,
                fontSize: 20,
                color: theme.text,
                lineHeight: 1.4,
              }}
            >
              {item}
            </span>
          </div>
        );
      })}
    </div>
  );
};
```

Usage:
```tsx
<AnimatedChecklist
  items={[
    "Define agent goals and constraints",
    "Choose tools and integrations",
    "Set up memory and context window",
    "Test with edge cases",
    "Deploy and monitor",
  ]}
  staggerDelay={15}
  checkColor={theme.green}
  delay={20}
/>
```

---

## StatHero

Big number with a label and optional trend indicator. Spring entrance animation.

```tsx
import React from "react";
import { useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";

export const StatHero: React.FC<{
  value: string | number;
  label: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  color?: string;
}> = ({ value, label, trend, trendValue, color = theme.green }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 100 },
  });

  const labelProgress = spring({
    frame,
    fps,
    delay: 10,
    config: { damping: 200 },
  });

  const trendProgress = spring({
    frame,
    fps,
    delay: 20,
    config: { damping: 200 },
  });

  const trendArrow = trend === "up" ? "▲" : trend === "down" ? "▼" : "—";
  const trendColor =
    trend === "up" ? "#22c55e" :
    trend === "down" ? "#ef4444" :
    theme.muted;

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "flex-start", gap: 8 }}>
      {/* Big value */}
      <div
        style={{
          fontFamily: theme.fontSans,
          fontSize: 96,
          fontWeight: 700,
          color,
          lineHeight: 1,
          letterSpacing: "-0.03em",
          opacity: progress,
          transform: `scale(${0.8 + progress * 0.2})`,
          transformOrigin: "left center",
        }}
      >
        {value}
      </div>

      {/* Label */}
      <div
        style={{
          fontFamily: theme.fontSans,
          fontSize: 20,
          color: theme.muted,
          opacity: labelProgress,
          transform: `translateY(${(1 - labelProgress) * 8}px)`,
        }}
      >
        {label}
      </div>

      {/* Trend indicator */}
      {trend && trendValue && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            opacity: trendProgress,
            transform: `translateY(${(1 - trendProgress) * 8}px)`,
          }}
        >
          <span
            style={{
              fontFamily: theme.fontMono,
              fontSize: 14,
              color: trendColor,
              fontWeight: 700,
            }}
          >
            {trendArrow}
          </span>
          <span
            style={{
              fontFamily: theme.fontSans,
              fontSize: 14,
              color: trendColor,
            }}
          >
            {trendValue}
          </span>
        </div>
      )}
    </div>
  );
};
```

Usage:
```tsx
// Positive metric
<StatHero
  value="$4.2M"
  label="Annual Recurring Revenue"
  trend="up"
  trendValue="+34% YoY"
  color={theme.green}
/>

// Negative metric
<StatHero
  value="142ms"
  label="P99 Latency"
  trend="down"
  trendValue="-58% vs last month"
  color={theme.cyan}
/>

// Neutral / no trend
<StatHero value="99.97%" label="Uptime (90 days)" color={theme.purple} />
```
