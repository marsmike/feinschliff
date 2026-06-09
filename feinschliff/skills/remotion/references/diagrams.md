# Geometric Diagrams in Remotion

How to construct and animate custom geometric diagrams (V-Models,
pyramids, hexagons, networks, ladders) without the layout bugs that
plague ad-hoc implementations.

**When to use this reference:** any beat whose visualization-reasoning
landed on "Sequential Process", "Hierarchy / Structure", or "Composition"
with a custom shape, or any diagram more complex than a flat grid of
Cards.

## Core discipline

### SVG viewBox centering — always

Diagrams should render in an abstract coordinate space (a viewBox) and
center themselves inside their scene container. Never hardcode pixel
offsets relative to the canvas.

```tsx
// GOOD — self-centering, canvas-size independent
return (
  <div style={{
    position: "absolute",
    left: "50%",
    top: "50%",
    width: 1600,    // abstract-space width
    height: 900,    // abstract-space height
    transform: "translate(-50%, -50%)",
  }}>
    {/* all geometry in 1600×900 coords */}
  </div>
);

// BAD — breaks when the scene container changes size or the diagram moves
return (
  <div style={{ position: "absolute", left: 160, top: 80 }}>
    {/* hardcoded offsets, 320 px empty margin on 1920 canvas */}
  </div>
);
```

If the diagram needs to scale to fit, derive scale factors from the
component's `width` and `height` props:

```tsx
const sx = width / 1600;
const sy = height / 900;
const s = (x: number, y: number) => ({ x: x * sx, y: y * sy });
```

Then map every coordinate through `s()` before rendering.

### Keep-out zones

Every hub node (apex, junction, grid center) has a keep-out radius. No
other node may enter that radius. Encode this in data, not eyeballing:

```tsx
const NODES = [
  { id: "apex", x: 800, y: 680, keepOut: 100 },
  { id: "agent-1", x: 740, y: 780, keepOut: 60 },
  { id: "agent-2", x: 860, y: 780, keepOut: 60 },
];

// Dev-time assertion (run once during component development):
function checkNoOverlap(nodes: typeof NODES) {
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x;
      const dy = nodes[i].y - nodes[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const minDist = nodes[i].keepOut + nodes[j].keepOut;
      if (dist < minDist) {
        throw new Error(`Overlap: ${nodes[i].id} and ${nodes[j].id}`);
      }
    }
  }
}
```

### Label safe-zones

Text on top of lines is illegible. Enforce margins:

- Horizontal line labels: ≥ 20 px above or below the line
- Vertical gate markers: ≥ 16 px horizontal offset
- Phase node descriptions: ≥ 8 px below the node ring

Mid-line mini-labels (like "Verification" sitting on a horizontal
traceability line) are an anti-pattern. If you need to name the line's
semantic, use color coding or a legend, not inline text.

### Avoid inline HTML divs on top of SVG for positioned content

`VModelDiagram.tsx` uses a hybrid — SVG for path lines, absolutely-
positioned HTML `<div>`s for node labels. This works but requires the
outer container to be the same size as the SVG viewBox coords. A purer
approach: render everything in SVG with `<foreignObject>` for HTML
content inside SVG. Pick one and stick with it. Don't mix positioning
systems within the same diagram.

## Shape primitives

### Animated line (draw-on)

```tsx
const pathLength = 2400;
const visibleLength = pathLength * drawProgress;

<line
  x1={x1} y1={y1} x2={x2} y2={y2}
  stroke={color} strokeWidth={4}
  strokeDasharray={pathLength}
  strokeDashoffset={pathLength - visibleLength}
  strokeLinecap="round"
/>
```

### Polygon (e.g. hexagon)

```tsx
function hexPoints(cx: number, cy: number, r: number): string {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i;
    pts.push(`${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`);
  }
  return pts.join(" ");
}

<polygon points={hexPoints(800, 540, 100)} fill={accent} stroke={border} />
```

### V-shape path

```tsx
function vPath(topLeft: {x:number,y:number}, apex: {x:number,y:number}, topRight: {x:number,y:number}) {
  return `M ${topLeft.x},${topLeft.y} L ${apex.x},${apex.y} L ${topRight.x},${topRight.y}`;
}
```

### Stepped/terraced V

For corporate explainers that want horizontal bars stepped in a V:

```tsx
function terracedVBars(centerX: number, topY: number, stepHeight: number, barWidth: number, stepCount: number) {
  const bars = [];
  for (let i = 0; i < stepCount; i++) {
    const leftX = centerX - barWidth - i * (barWidth / stepCount);
    const rightX = centerX + i * (barWidth / stepCount);
    const y = topY + i * stepHeight;
    bars.push({ side: "left", x: leftX, y, w: barWidth });
    bars.push({ side: "right", x: rightX, y, w: barWidth });
  }
  return bars;
}
```

### Rounded rectangle with animated border

```tsx
<rect
  x={x} y={y} width={w} height={h} rx={12} ry={12}
  fill="transparent"
  stroke={accent}
  strokeWidth={3}
  strokeDasharray={2 * (w + h)}
  strokeDashoffset={2 * (w + h) * (1 - drawProgress)}
/>
```

### Arc / curve

```tsx
// Quarter-circle arc from (x1,y1) to (x2,y2) with radius r
<path d={`M ${x1},${y1} A ${r},${r} 0 0 1 ${x2},${y2}`} fill="none" stroke={color} />
```

## Archetype recipes

### Sharp V (classic software V-Model)

```tsx
const PHASES = {
  left:  [{short:"REQ", x:140, y:80}, {short:"SYS", x:340, y:240}, {short:"ARCH", x:540, y:400}],
  right: [{short:"I-TEST", x:1060, y:400}, {short:"S-TEST", x:1260, y:240}, {short:"ACC", x:1460, y:80}],
  apex:  {short:"INT", x:800, y:680},
};
const pairings = [[0,2], [1,1], [2,0]];  // REQ↔ACC, SYS↔S-TEST, ARCH↔I-TEST

// Render: draw the V path, then phase nodes, then horizontal traceability lines between pairings.
```

### Terraced V (easier to animate, corporate style)

Horizontal bars stepped down/up. All text horizontal, no rotated labels.
Easier assembly animations (bars slide in). Use when the "V" silhouette
isn't critical but the left=design / right=verification semantics are.

### Network with 5 nodes + agent edges

Five hub nodes placed at data-driven coordinates; edges between them
drawn as animated lines. Useful for "5 agents activate in parallel" shots.

```tsx
const AGENTS = [
  { id: "flow-monitor",   x: 800, y: 110, icon: "👁" },
  { id: "impact-scanner", x: 800, y: 240, icon: "📡" },
  // ...
];

// For each agent: render icon circle at (x,y), label below at (x, y+40).
// For each agent-edge: animated line between two agent positions.
```

## Derive-from-reference-image protocol

Given a reference image (screenshot, corporate diagram, slide) that the
video needs to replicate:

1. **Identify the skeleton.** Name the geometric anchors — V apex, grid
   cells, axis endpoints. Pixel-measure in the reference (use the macOS
   screenshot ruler or DevTools if it's a web page).

2. **Normalize to viewBox coords.** Pick a viewBox (1600×900 for 16:9 is
   a good default). Rescale the measurements. Aim for "nice" numbers
   (round to multiples of 10 or 20) — the reference probably wasn't
   produced to pixel-perfect precision anyway.

3. **Extract the typed data.** Define a TypeScript data structure that
   names each element: phases, pairings, layers, axes. Render from this
   data. Never inline coordinates inside render functions.

   ```tsx
   interface Phase { short: string; label: string; x: number; y: number }
   interface Pairing { leftIndex: number; rightIndex: number; semantic: string }
   interface Diagram { phases: Phase[]; pairings: Pairing[]; apex: Phase }
   ```

4. **Run the keep-out assertion.** Confirm no nodes overlap before
   rendering a single frame.

5. **Render a still, compare.** Use `npx remotion still` and place the
   output next to the reference. Iterate on the data, not on the render
   function.

This protocol is what the YouTube skill does for videos (read → extract
scene structure → reconstruct), applied to geometric diagrams: read the
reference, extract semantics as data, render from semantics. It prevents
"stylization drift" where the implementer improvises coordinates and
ends up with a diagram that's visually close but structurally wrong.

## Animation patterns

### Assemble (parts fly in to seats)

Use for the first appearance of a diagram.

```tsx
// Arm draws first, phase nodes settle, then traceability lines
const armProgress = interpolate(frame, [0, 30], [0, 1], { extrapolateLeft:"clamp", extrapolateRight:"clamp" });
const phasesVisible = frame >= 20;
const tracesVisible = frame >= 50;
```

### Transform (state morph)

Use for "red problem → orange solution" transitions. Color-interpolate
on existing nodes instead of removing and re-adding them.

```tsx
const color = interpolateColors(progress, [0, 1], [theme.danger, theme.accent]);
```

### Alive (breathe + glow-pulse)

Use for steady-state "living system" shots.

```tsx
const breatheScale = 1 + Math.sin(frame * 0.04) * 0.008;
const glowRadius = 10 + Math.sin(frame * 0.05) * 6;
```

### Decompose (reverse of assemble)

Parts fade or fly out. Useful for scene transitions.

```tsx
const exitProgress = interpolate(frame, [durationFrames - 20, durationFrames], [0, 1], { extrapolateLeft:"clamp", extrapolateRight:"clamp" });
// Then scale nodes by (1 - exitProgress) and fade their opacity.
```

## Anti-patterns

- **Hardcoded pixel offsets** relative to the scene container — breaks at
  every size other than the one you tested.
- **Labels on top of lines** without a ≥ 20 px margin — illegible.
- **Eyeballing node positions** instead of deriving from data — every
  future fix becomes a "nudge until it looks right" exercise.
- **Mixing scales** between the diagram and its surrounding UI — if the
  diagram uses a 1600×900 viewBox but the title card uses pixel
  positioning, they won't agree at any resolution other than 1920×1080.
- **Mid-line micro-labels** that compete with indicator markers — pick
  one semantic channel per location.
- **Animating every element** simultaneously — stagger or the viewer's
  eye has nowhere to land.

## Case study: VA-Model V-Model (v1 bugs and v2 fixes)

v1 shipped with a sharp-V diagram that had five layout bugs:

| Bug | Cause | Fix |
|-----|-------|-----|
| V shifted left | 1600-wide diagram in 1920-wide container, no centering | Centered wrapper, `translate(-50%,-50%)` |
| Agent nodes overlapping apex | PR Analyzer at `(660,565)` adjacent to INT at `(800,590)` | Moved agents to `(740,780)` / `(860,780)`, well below the apex |
| SW Dev block crashing into left arm | Block at `(340,440)` under ARCH at `(540,400)` | Moved block to `(1050,720)`, right of apex |
| Mid-arm mini-labels colliding with gap markers | "Verification"/"Testing" text at traceability line midpoints | Removed the text; horizontal line color alone conveys the semantic |
| Top blind-spot overrunning REQ↔ACC line | Flow Monitor at `y=80` exactly on the line | Moved to `y=110`, 30 px below line |

All five bugs had the same root cause: ad-hoc coordinates without a
data-driven layout check. v2 adopted the discipline in this reference:
viewBox centering, keep-out assertions, safe-zone margins.
