# Scene Templates

Pre-built, complete scene compositions that layer backgrounds, components, and animations. Each template is a full-scene component ready to copy, paste, and customize. All use `spring()` or `interpolate()` — never CSS animations.

**Import paths assume components live in `src/components/` and backgrounds in `src/backgrounds/`.**

---

## 1. IntroScene

**Background stack:** `RadialGradientBg` + `DotGridBg` + `AccentGlow` + `Vignette`
**Content:** Centered `ColorText` title with spring entrance, subtitle fade after delay, optional `Badge` tagline

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";
import { RadialGradientBg } from "../backgrounds/RadialGradientBg";
import { DotGridBg } from "../backgrounds/DotGridBg";
import { AccentGlow } from "../backgrounds/AccentGlow";
import { Vignette } from "../backgrounds/Vignette";
import { ColorText } from "../components/ColorText";
import { Badge } from "../components/Badge";

type TextSegment = string | { text: string; color: string };

interface IntroSceneProps {
  segments: TextSegment[];
  subtitle?: string;
  badge?: string;
  accentColor?: string;
}

export const IntroScene: React.FC<IntroSceneProps> = ({
  segments,
  subtitle,
  badge,
  accentColor = theme.green,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animation: slide-up — title spring entrance
  const titleProgress = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 100 },
  });

  // Animation: fade-in — badge appears first as context
  const badgeProgress = spring({
    frame,
    fps,
    delay: Math.round(fps * 0.2),
    config: { damping: 200 },
  });

  // Animation: fade-in — subtitle fades after title settles
  const subtitleProgress = spring({
    frame,
    fps,
    delay: Math.round(fps * 0.8),
    config: { damping: 200 },
  });

  return (
    <AbsoluteFill>
      {/* Layer 1: Base gradient */}
      <RadialGradientBg color1="#1a1a2e" color2="#0a0a0f" centerX={50} centerY={40} />

      {/* Layer 2: Dot pattern */}
      <DotGridBg
        dotColor={`${accentColor}22`}
        dotSize={1}
        spacing={24}
      />

      {/* Layer 3: Accent glow behind title */}
      <AccentGlow color={accentColor} x={50} y={45} size={700} blur={160} opacity={0.2} />

      {/* Layer 4: Vignette to frame composition */}
      <Vignette intensity={0.55} />

      {/* Layer 5: Content */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: theme.safeZones.landscape.titleSafe,
        }}
      >
        <div style={{ textAlign: "center", maxWidth: theme.safeZones.landscape.maxContentWidth }}>
          {/* Optional badge tagline above title */}
          {badge && (
            <div
              style={{
                marginBottom: theme.spacing.lg,
                opacity: badgeProgress,
                transform: `translateY(${(1 - badgeProgress) * -10}px)`,
              }}
            >
              <Badge label={badge} color={accentColor} />
            </div>
          )}

          {/* Title — typography.h1 */}
          {/* Animation: slide-up */}
          <div
            style={{
              opacity: titleProgress,
              transform: `translateY(${(1 - titleProgress) * 30}px)`,
            }}
          >
            <ColorText
              segments={segments}
              fontSize={theme.typography.h1.fontSize}
              fontFamily={theme.typography.h1.fontFamily}
            />
          </div>

          {/* Subtitle — typography.body */}
          {/* Animation: fade-in */}
          {subtitle && (
            <div
              style={{
                ...theme.typography.body,
                color: theme.muted,
                marginTop: theme.spacing.lg,
                opacity: subtitleProgress,
                transform: `translateY(${(1 - subtitleProgress) * 10}px)`,
              }}
            >
              {subtitle}
            </div>
          )}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

**Usage:**
```tsx
<IntroScene
  segments={[
    "Ship ",
    { text: "10x faster", color: theme.green },
    " with AI agents",
  ]}
  subtitle="A practical guide to building production-ready pipelines"
  badge="New in 2026"
  accentColor={theme.green}
/>
```

---

## 2. DataScene

**Background stack:** `RadialGradientBg` + `DotGridBg`
**Content:** `StatHero` or `CountUp` as hero element centered, supporting `BarChart` or `ProgressBar` below

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";
import { RadialGradientBg } from "../backgrounds/RadialGradientBg";
import { DotGridBg } from "../backgrounds/DotGridBg";
import { StatHero } from "../components/StatHero";
import { CountUp } from "../components/CountUp";
import { BarChart } from "../components/BarChart";
import { ProgressBar } from "../components/ProgressBar";

interface BarData {
  label: string;
  value: number;
  color?: string;
}

interface DataSceneProps {
  value: number;
  label: string;
  prefix?: string;
  suffix?: string;
  /** Use StatHero for formatted values, CountUp for animated counting */
  heroMode?: "stat" | "countup";
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  supportingData?: BarData[];
  /** Show progress bars instead of a bar chart */
  progressBars?: { label: string; progress: number }[];
  accentColor?: string;
}

export const DataScene: React.FC<DataSceneProps> = ({
  value,
  label,
  prefix = "",
  suffix = "",
  heroMode = "stat",
  trend,
  trendValue,
  supportingData,
  progressBars,
  accentColor = theme.green,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animation: spring-in — hero number scale entrance
  const heroProgress = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 100 },
  });

  // Animation: stagger-up — supporting elements appear after hero settles
  const supportDelay = Math.round(fps * 0.8);

  const formattedValue = `${prefix}${value.toLocaleString("en-US")}${suffix}`;

  return (
    <AbsoluteFill>
      {/* Layer 1: Base gradient */}
      <RadialGradientBg color1="#1a1a2e" color2="#0a0a0f" centerX={50} centerY={40} />

      {/* Layer 2: Dot pattern */}
      <DotGridBg dotColor={`${accentColor}18`} dotSize={1} spacing={24} />

      {/* Layer 5: Content */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: theme.spacing["2xl"],
          padding: theme.safeZones.landscape.titleSafe,
        }}
      >
        {/* Hero element — animation: spring-in */}
        <div
          style={{
            opacity: heroProgress,
            transform: `scale(${0.8 + heroProgress * 0.2})`,
            textAlign: "center",
          }}
        >
          {heroMode === "stat" ? (
            <StatHero
              value={formattedValue}
              label={label}
              trend={trend}
              trendValue={trendValue}
              color={accentColor}
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: theme.spacing.md }}>
              {/* Animation: count-up */}
              <CountUp
                from={0}
                to={value}
                delay={0}
                duration={Math.round(fps * 1.2)}
                prefix={prefix}
                suffix={suffix}
                fontSize={96}
              />
              <div style={{ ...theme.typography.body, color: theme.muted }}>
                {label}
              </div>
            </div>
          )}
        </div>

        {/* Supporting data — animation: stagger-up */}
        {supportingData && supportingData.length > 0 && (
          <BarChart
            data={supportingData.map((d) => ({ ...d, color: d.color || accentColor }))}
            width={900}
            height={280}
            delay={supportDelay}
            staggerDelay={8}
          />
        )}

        {progressBars && progressBars.length > 0 && (
          <div style={{ width: 800, display: "flex", flexDirection: "column", gap: theme.spacing.md }}>
            {progressBars.map((bar, i) => {
              // Animation: stagger-up for each bar
              const barProgress = spring({
                frame,
                fps,
                delay: supportDelay + i * 8,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{ opacity: barProgress, transform: `translateY(${(1 - barProgress) * 20}px)` }}
                >
                  <ProgressBar
                    progress={bar.progress}
                    label={bar.label}
                    color={accentColor}
                    width="100%"
                  />
                </div>
              );
            })}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

**Usage:**
```tsx
// With StatHero + BarChart
<DataScene
  value={4200000}
  label="Annual Recurring Revenue"
  prefix="$"
  heroMode="stat"
  trend="up"
  trendValue="+34% YoY"
  accentColor={theme.green}
  supportingData={[
    { label: "Q1", value: 900000 },
    { label: "Q2", value: 1050000 },
    { label: "Q3", value: 1100000, color: theme.cyan },
    { label: "Q4", value: 1150000, color: theme.green },
  ]}
/>

// With CountUp + progress bars
<DataScene
  value={98.6}
  label="Uptime (90 days)"
  suffix="%"
  heroMode="countup"
  accentColor={theme.cyan}
  progressBars={[
    { label: "API Gateway", progress: 0.99 },
    { label: "Database", progress: 0.987 },
    { label: "Worker Queue", progress: 0.972 },
  ]}
/>
```

---

## 3. ComparisonScene

**Background stack:** `LinearGradientBg` + `Vignette`
**Content:** `SplitScreen` with `Card` content on each side, labels at top, optional centered title

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";
import { LinearGradientBg } from "../backgrounds/LinearGradientBg";
import { Vignette } from "../backgrounds/Vignette";
import { SplitScreen } from "../components/SplitScreen";
import { ColorText } from "../components/ColorText";

type TextSegment = string | { text: string; color: string };

interface ComparisonSceneProps {
  leftContent: React.ReactNode;
  rightContent: React.ReactNode;
  leftLabel: string;
  rightLabel: string;
  title?: string | TextSegment[];
}

export const ComparisonScene: React.FC<ComparisonSceneProps> = ({
  leftContent,
  rightContent,
  leftLabel,
  rightLabel,
  title,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animation: fade-in — title appears before split
  const titleProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  const titleSegments: TextSegment[] =
    typeof title === "string" ? [title] : title ?? [];

  return (
    <AbsoluteFill>
      {/* Layer 1: Linear gradient — minimal, lets content breathe */}
      <LinearGradientBg from="#0f172a" to="#020617" angle={160} />

      {/* Layer 2: Vignette to frame the comparison */}
      <Vignette intensity={0.5} />

      {/* Layer 5: Content */}
      <AbsoluteFill
        style={{
          flexDirection: "column",
          padding: theme.safeZones.landscape.titleSafe,
          gap: theme.spacing.xl,
        }}
      >
        {/* Optional centered title — animation: fade-in */}
        {title && (
          <div
            style={{
              textAlign: "center",
              opacity: titleProgress,
              transform: `translateY(${(1 - titleProgress) * -12}px)`,
              flexShrink: 0,
            }}
          >
            <ColorText
              segments={titleSegments}
              fontSize={theme.typography.h2.fontSize}
              fontFamily={theme.typography.h2.fontFamily}
            />
          </div>
        )}

        {/* Split screen — animation: slide-left (left pane) + slide-right (right pane) */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <SplitScreen
            leftLabel={leftLabel}
            rightLabel={rightLabel}
            left={leftContent}
            right={rightContent}
            splitRatio={0.5}
            dividerColor={theme.surfaceBorder}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

**Usage:**
```tsx
<ComparisonScene
  title={["Before", " vs ", { text: "After", color: theme.green }]}
  leftLabel="Manual Process"
  rightLabel="With AI Agents"
  leftContent={
    <Card accent={theme.error}>
      <div style={{ ...theme.typography.h3, color: theme.text }}>3 days</div>
      <div style={{ ...theme.typography.body, color: theme.muted, marginTop: theme.spacing.sm }}>
        Average turnaround time
      </div>
    </Card>
  }
  rightContent={
    <Card accent={theme.green} glow>
      <div style={{ ...theme.typography.h3, color: theme.green }}>4 minutes</div>
      <div style={{ ...theme.typography.body, color: theme.muted, marginTop: theme.spacing.sm }}>
        Average turnaround time
      </div>
    </Card>
  }
/>
```

---

## 4. CodeDemoScene

**Background stack:** `RadialGradientBg` (dark) + `DotGridBg`
**Content:** `CodeBlock` as main element, optional `Badge` for language tag, optional terminal output using `Typewriter`

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";
import { RadialGradientBg } from "../backgrounds/RadialGradientBg";
import { DotGridBg } from "../backgrounds/DotGridBg";
import { CodeBlock } from "../components/CodeBlock";
import { Badge } from "../components/Badge";
import { Typewriter } from "../components/Typewriter";

interface CodeDemoSceneProps {
  code: string;
  language?: string;
  title?: string;
  terminalOutput?: string;
  /** Delay (frames) before terminal output starts typing */
  terminalDelay?: number;
  highlightLines?: number[];
  revealMode?: "all" | "line-by-line";
}

export const CodeDemoScene: React.FC<CodeDemoSceneProps> = ({
  code,
  language = "typescript",
  title,
  terminalOutput,
  terminalDelay,
  highlightLines = [],
  revealMode = "all",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Default terminal delay: after the code finishes revealing
  const codeLines = code.split("\n").length;
  const computedTerminalDelay =
    terminalDelay ?? (revealMode === "line-by-line" ? codeLines * 6 + 20 : 30);

  // Animation: slide-up — title/badge entrance
  const headerProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  // Animation: fade-in — code block entrance
  const codeProgress = spring({
    frame,
    fps,
    delay: 10,
    config: { damping: 200 },
  });

  // Animation: fade-in — terminal panel
  const terminalProgress = spring({
    frame,
    fps,
    delay: computedTerminalDelay,
    config: { damping: 200 },
  });

  return (
    <AbsoluteFill>
      {/* Layer 1: Dark radial gradient — creates depth behind code */}
      <RadialGradientBg color1="#12121e" color2="#0a0a0f" centerX={50} centerY={35} />

      {/* Layer 2: Subtle dot grid for texture */}
      <DotGridBg dotColor="rgba(139,92,246,0.12)" dotSize={1} spacing={28} />

      {/* Layer 5: Content */}
      <AbsoluteFill
        style={{
          flexDirection: "column",
          justifyContent: "center",
          gap: theme.spacing.lg,
          padding: theme.safeZones.landscape.titleSafe,
        }}
      >
        {/* Header: title + language badge — animation: slide-up */}
        {(title || language) && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: theme.spacing.md,
              opacity: headerProgress,
              transform: `translateY(${(1 - headerProgress) * -12}px)`,
            }}
          >
            {title && (
              <div style={{ ...theme.typography.h2, color: theme.text }}>
                {title}
              </div>
            )}
            {/* Language badge — animation: fade-in */}
            <Badge label={language ?? ""} color={theme.purple} />
          </div>
        )}

        {/* Main code block — animation: fade-in or code-reveal */}
        <div
          style={{
            opacity: codeProgress,
            transform: `translateY(${(1 - codeProgress) * 16}px)`,
          }}
        >
          <CodeBlock
            code={code}
            language={language}
            highlightLines={highlightLines}
            revealMode={revealMode}
            revealDelay={6}
            fontSize={18}
          />
        </div>

        {/* Optional terminal output panel — animation: typewriter */}
        {terminalOutput && (
          <div
            style={{
              opacity: terminalProgress,
              backgroundColor: "#0d0d14",
              borderRadius: theme.radius,
              border: `1px solid ${theme.surfaceBorder}`,
              padding: `${theme.spacing.md}px ${theme.spacing.lg}px`,
            }}
          >
            <div
              style={{
                ...theme.typography.caption,
                color: theme.muted,
                marginBottom: theme.spacing.sm,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Terminal
            </div>
            {/* Animation: typewriter */}
            <Typewriter
              text={terminalOutput}
              delay={computedTerminalDelay}
              framesPerChar={2}
              fontSize={theme.typography.code.fontSize}
              color={theme.green}
            />
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

**Usage:**
```tsx
const snippet = `const agent = new Agent({
  model: "claude-opus-4-5",
  tools: [searchTool, writeTool],
  maxSteps: 10,
});

const result = await agent.run(userPrompt);`;

<CodeDemoScene
  code={snippet}
  language="typescript"
  title="Agent Setup"
  highlightLines={[2, 3]}
  revealMode="line-by-line"
  terminalOutput="✓ Agent initialized · tools: 2 · maxSteps: 10"
/>
```

---

## 5. QuoteScene

**Background stack:** `LinearGradientBg` only (minimal — no grid)
**Content:** `QuoteCard` centered with `breathe` continuous animation

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate } from "remotion";
import { theme } from "../theme";
import { LinearGradientBg } from "../backgrounds/LinearGradientBg";
import { QuoteCard } from "../components/QuoteCard";

interface QuoteSceneProps {
  quote: string;
  author: string;
  role?: string;
  accentColor?: string;
}

export const QuoteScene: React.FC<QuoteSceneProps> = ({
  quote,
  author,
  role,
  accentColor = theme.purple,
}) => {
  const frame = useCurrentFrame();

  // Animation: breathe — subtle continuous scale oscillation on the quote card
  // breathe: scale oscillates between 0.99 and 1.01 over ~90 frames
  const breatheScale = interpolate(
    Math.sin((frame / 90) * Math.PI * 2),
    [-1, 1],
    [0.99, 1.01]
  );

  return (
    <AbsoluteFill>
      {/* Layer 1: Linear gradient only — minimal backdrop, keeps focus on quote */}
      <LinearGradientBg from="#0f172a" to="#020617" angle={160} />

      {/* Layer 5: Content */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: theme.safeZones.landscape.titleSafe,
        }}
      >
        {/* Animation: breathe — gentle continuous scale on wrapper */}
        <div
          style={{
            transform: `scale(${breatheScale})`,
            maxWidth: 1000,
            width: "100%",
          }}
        >
          {/* QuoteCard handles its own slide-left entrance animation internally */}
          <QuoteCard
            quote={quote}
            author={author}
            role={role}
            accentColor={accentColor}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

**Usage:**
```tsx
<QuoteScene
  quote="The best way to predict the future is to build it."
  author="Alan Kay"
  role="Computer Scientist"
  accentColor={theme.purple}
/>

// With a longer quote and different accent
<QuoteScene
  quote="Programs must be written for people to read, and only incidentally for machines to execute."
  author="Harold Abelson"
  role="MIT, Structure and Interpretation of Computer Programs"
  accentColor={theme.cyan}
/>
```

---

## 6. FlowScene

**Background stack:** `RadialGradientBg` + `LineGridBg` + `AccentGlow`
**Content:** Title at top, `PipelineFlow` (when `steps` provided) or `NodeGraph` (when `nodes`/`edges` provided)

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { theme } from "../theme";
import { RadialGradientBg } from "../backgrounds/RadialGradientBg";
import { LineGridBg } from "../backgrounds/LineGridBg";
import { AccentGlow } from "../backgrounds/AccentGlow";
import { ColorText } from "../components/ColorText";
import { PipelineFlow, PipelineStep } from "../components/PipelineFlow";
import { NodeGraph } from "../components/NodeGraph";

type TextSegment = string | { text: string; color: string };

interface NodeData {
  id: string;
  label: string;
  icon?: string;
  x: number;
  y: number;
  color?: string;
}

interface EdgeData {
  from: string;
  to: string;
  label?: string;
}

interface FlowSceneProps {
  title: string | TextSegment[];
  steps?: PipelineStep[];
  nodes?: NodeData[];
  edges?: EdgeData[];
  accentColor?: string;
}

export const FlowScene: React.FC<FlowSceneProps> = ({
  title,
  steps,
  nodes,
  edges,
  accentColor = theme.purple,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSegments: TextSegment[] =
    typeof title === "string" ? [title] : title;

  const usePipeline = steps && steps.length > 0;
  const useGraph = !usePipeline && nodes && nodes.length > 0;

  // Animation: fade-in — title entrance
  const titleProgress = spring({
    frame,
    fps,
    config: { damping: 200 },
  });

  // Flow content starts after title settles
  const contentDelay = Math.round(fps * 0.5);

  return (
    <AbsoluteFill>
      {/* Layer 1: Base gradient */}
      <RadialGradientBg color1="#1a1228" color2="#0a0a0f" centerX={50} centerY={40} />

      {/* Layer 2: Line grid — structural, suits flow/graph content */}
      <LineGridBg lineColor={`${accentColor}10`} spacing={48} />

      {/* Layer 3: Accent glow at center-top where title lives */}
      <AccentGlow color={accentColor} x={50} y={20} size={600} blur={140} opacity={0.18} />

      {/* Layer 5: Content */}
      <AbsoluteFill
        style={{
          flexDirection: "column",
          padding: theme.safeZones.landscape.titleSafe,
          gap: theme.spacing.xl,
        }}
      >
        {/* Title — animation: fade-in */}
        <div
          style={{
            textAlign: "center",
            opacity: titleProgress,
            transform: `translateY(${(1 - titleProgress) * -16}px)`,
            flexShrink: 0,
          }}
        >
          <ColorText
            segments={titleSegments}
            fontSize={theme.typography.h1.fontSize}
            fontFamily={theme.typography.h1.fontFamily}
          />
        </div>

        {/* Flow content */}
        <div style={{ flex: 1, minHeight: 0, display: "flex", alignItems: "center" }}>
          {/* Use PipelineFlow when steps is provided — animation: stagger-up */}
          {usePipeline && (
            <PipelineFlow
              steps={steps!}
              direction="row"
              delay={contentDelay}
              staggerDelay={12}
            />
          )}

          {/* Use NodeGraph when nodes/edges are provided — animation: spring-in + draw-line */}
          {useGraph && (
            <NodeGraph
              nodes={nodes!}
              edges={edges ?? []}
              delay={contentDelay}
              staggerDelay={10}
            />
          )}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

**Usage:**
```tsx
// Pipeline variant (steps)
<FlowScene
  title={["The ", { text: "Agent Loop", color: theme.purple }]}
  accentColor={theme.purple}
  steps={[
    { icon: "📥", title: "Receive", description: "User prompt arrives", color: theme.cyan },
    { icon: "🧠", title: "Plan", description: "Break into sub-tasks", color: theme.purple },
    { icon: "🛠", title: "Execute", description: "Call tools in parallel", color: theme.green },
    { icon: "✅", title: "Respond", description: "Synthesize and reply", color: theme.orange },
  ]}
/>

// NodeGraph variant (nodes + edges)
<FlowScene
  title="Service Architecture"
  accentColor={theme.cyan}
  nodes={[
    { id: "gw",   label: "API Gateway",   icon: "🌐", x: 840, y: 120, color: theme.cyan },
    { id: "auth", label: "Auth Service",  icon: "🔐", x: 400, y: 340, color: theme.purple },
    { id: "db",   label: "Database",      icon: "🗄️", x: 840, y: 560, color: theme.green },
    { id: "cache",label: "Cache",         icon: "⚡", x: 1280, y: 340, color: theme.orange },
  ]}
  edges={[
    { from: "gw", to: "auth",  label: "verify" },
    { from: "gw", to: "db",    label: "query" },
    { from: "gw", to: "cache", label: "read" },
  ]}
/>
```

---

## 7. OutroScene

**Background stack:** `RadialGradientBg` + `Vignette`
**Content:** CTA text centered, optional URL/social handles; scale-down exit animation at end

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate, Easing } from "remotion";
import { theme } from "../theme";
import { RadialGradientBg } from "../backgrounds/RadialGradientBg";
import { Vignette } from "../backgrounds/Vignette";
import { AccentGlow } from "../backgrounds/AccentGlow";
import { ColorText } from "../components/ColorText";
import { Badge } from "../components/Badge";

type TextSegment = string | { text: string; color: string };

interface OutroSceneProps {
  cta: string | TextSegment[];
  url?: string;
  socials?: string[];
  accentColor?: string;
  /** Frame at which exit animation begins (default: 20 frames before composition end) */
  exitStartFrame?: number;
}

export const OutroScene: React.FC<OutroSceneProps> = ({
  cta,
  url,
  socials,
  accentColor = theme.green,
  exitStartFrame,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const ctaSegments: TextSegment[] =
    typeof cta === "string" ? [cta] : cta;

  // Default exit starts 22 frames before end
  const exitStart = exitStartFrame ?? durationInFrames - 22;

  // Animation: spring-in — CTA entrance
  const ctaProgress = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 100 },
  });

  // Animation: fade-in — URL/socials stagger after CTA
  const urlProgress = spring({
    frame,
    fps,
    delay: Math.round(fps * 0.6),
    config: { damping: 200 },
  });

  const socialsProgress = spring({
    frame,
    fps,
    delay: Math.round(fps * 0.9),
    config: { damping: 200 },
  });

  // Animation: scale-down — exit animation at end of scene
  const exitProgress = interpolate(
    frame,
    [exitStart, durationInFrames],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.in(Easing.cubic),
    }
  );

  const contentScale = interpolate(exitProgress, [0, 1], [1, 0.92]);
  const contentOpacity = interpolate(exitProgress, [0, 1], [1, 0]);

  return (
    <AbsoluteFill>
      {/* Layer 1: Base gradient — warm radial center */}
      <RadialGradientBg color1="#1a1a2e" color2="#0a0a0f" centerX={50} centerY={50} />

      {/* Accent glow centered for visual warmth */}
      <AccentGlow color={accentColor} x={50} y={50} size={800} blur={180} opacity={0.18} />

      {/* Layer 2: Vignette to draw eyes to center */}
      <Vignette intensity={0.65} />

      {/* Layer 5: Content — wrapped in exit animation container */}
      {/* Animation: scale-down (exit) */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: theme.spacing["2xl"],
          padding: theme.safeZones.landscape.titleSafe,
          opacity: contentOpacity,
          transform: `scale(${contentScale})`,
        }}
      >
        {/* CTA — animation: spring-in */}
        <div
          style={{
            textAlign: "center",
            opacity: ctaProgress,
            transform: `translateY(${(1 - ctaProgress) * 24}px)`,
          }}
        >
          <ColorText
            segments={ctaSegments}
            fontSize={theme.typography.h1.fontSize}
            fontFamily={theme.typography.h1.fontFamily}
          />
        </div>

        {/* URL — animation: fade-in */}
        {url && (
          <div
            style={{
              ...theme.typography.body,
              color: accentColor,
              fontFamily: theme.typography.label.fontFamily,
              letterSpacing: "0.04em",
              opacity: urlProgress,
              transform: `translateY(${(1 - urlProgress) * 10}px)`,
            }}
          >
            {url}
          </div>
        )}

        {/* Social handles — animation: stagger-up */}
        {socials && socials.length > 0 && (
          <div
            style={{
              display: "flex",
              gap: theme.spacing.xl,
              opacity: socialsProgress,
              transform: `translateY(${(1 - socialsProgress) * 10}px)`,
            }}
          >
            {socials.map((handle, i) => (
              <Badge key={i} label={handle} color={accentColor} />
            ))}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

**Usage:**
```tsx
<OutroScene
  cta={["Start building ", { text: "today", color: theme.green }]}
  url="docs.anthropic.com/agents"
  socials={["@anthropic", "github.com/anthropics"]}
  accentColor={theme.green}
/>

// Minimal CTA with just a URL
<OutroScene
  cta="Subscribe for more"
  url="youtube.com/@myChannel"
  accentColor={theme.cyan}
/>
```

---

## Template Selection Guide

| Scene type | Template | Key props |
|------------|----------|-----------|
| Video opening / brand intro | `IntroScene` | `segments`, `subtitle`, `badge` |
| Metric spotlight / stat reveal | `DataScene` | `value`, `label`, `heroMode`, `supportingData` |
| Before/after, A/B, side-by-side | `ComparisonScene` | `leftContent`, `rightContent`, `title` |
| Code walkthrough / demo | `CodeDemoScene` | `code`, `language`, `terminalOutput` |
| Testimonial / key insight | `QuoteScene` | `quote`, `author`, `role` |
| Architecture / process diagram | `FlowScene` | `steps` OR `nodes`+`edges` |
| Video closing / CTA | `OutroScene` | `cta`, `url`, `socials` |

## Customization Checklist

When adapting a template:
- [ ] Replace placeholder colors with `accentColor` prop or `theme.*` tokens
- [ ] Verify font sizes use `theme.typography.*` (not raw px values)
- [ ] Verify spacing uses `theme.spacing.*` tokens
- [ ] Adjust `delay` and `staggerDelay` values to match your VO timing from `src/timing.ts`
- [ ] Set `exitStartFrame` on `OutroScene` to `durationInFrames - exitDurationFrames`
- [ ] Run the visual feedback loop: render stills at frame 0, mid-scene, and last frame before checking in
