# Visualization Reasoning Guide

How to determine the best visual type for a given concept. Use this reasoning per beat in the storyboard.

**For custom geometric shapes** (V-Model, pyramid, hexagon grid, network diagram), see [diagrams.md](diagrams.md). That reference covers the layout discipline and animation patterns specific to hand-drawn diagrams.

## The Process

For each beat:
1. Identify the **concept type** (process, comparison, hierarchy, etc.)
2. Look up the **recommended visual types** below
3. Choose the best fit considering context and narrative flow
4. Explain your reasoning in the storyboard

## Concept → Visual Type Mapping

### Sequential Process
**Concepts:** workflows, pipelines, step-by-step procedures, request/response flows
**Best visuals:** Flowchart, Sequence Diagram, StepList
**Remotion components:** NodeGraph, StepList, animated arrows
**Why:** Sequential order is the core information — flowcharts and sequence diagrams make order explicit

### Comparison
**Concepts:** before/after, pros/cons, feature comparisons, option evaluation
**Best visuals:** Side-by-side cards, split screen, comparison table
**Remotion components:** Two Card components, Badge for labels, ProgressBar for metrics
**Why:** Spatial proximity enables direct comparison — placing items side by side lets viewers evaluate differences instantly

### Hierarchy / Structure
**Concepts:** org charts, system architectures, inheritance, containment
**Best visuals:** Tree diagram, nested boxes, layered diagram
**Remotion components:** NodeGraph with parent-child arrows, nested Card components
**Why:** Vertical/nested layout maps directly to hierarchical relationships

### Composition / Parts of a Whole
**Concepts:** system components, feature breakdowns, module structures
**Best visuals:** Exploded diagram, labeled parts, feature grid
**Remotion components:** Card grid, IconBadge for each part, Badge labels
**Why:** Spatial arrangement shows how parts relate to the whole

### Change Over Time
**Concepts:** evolution, growth, trends, historical progression
**Best visuals:** Timeline, animated chart, progression bar
**Remotion components:** StepList with timestamps, Timeline with animated markers, BarChart with animated values, ProgressBar, CountUp
**Why:** Horizontal time axis is universally understood — left is past, right is future

### Quantity / Metrics
**Concepts:** performance data, statistics, measurements, scores
**Best visuals:** Bar chart, metric cards, progress indicators
**Remotion components:** BarChart, MetricCard, ProgressBar
**Why:** Visual size encoding makes quantities immediately comparable

### State Changes
**Concepts:** status transitions, mode switches, lifecycle stages
**Best visuals:** State diagram, highlighted node changes, color transitions
**Remotion components:** NodeGraph with state highlighting, Badge status changes
**Why:** Color and visual emphasis draw attention to what changed

### Interaction / Communication
**Concepts:** API calls, message passing, client-server, pub-sub
**Best visuals:** Sequence diagram, animated message arrows
**Remotion components:** NodeGraph, PipelineFlow with animated edges, `draw-line` animation, NodeGraph with bidirectional arrows
**Why:** Arrows between actors make communication patterns visible

### Conceptual / Abstract
**Concepts:** trust, security, speed, reliability, innovation
**Best visuals:** Metaphorical visualization (bridge for connection, shield for security, layers for depth)
**Remotion components:** IconBadge with large icons, Card with bold text, CodeBlock, CountUp for numeric concepts, custom SVG/illustrations for complex metaphors
**Why:** Abstract concepts need concrete metaphors to become graspable

### Introduction / Hook
**Concepts:** title, topic introduction, attention grab
**Best visuals:** Title slide with highlighted keywords
**Remotion components:** TitleSlide, WordHighlight, Typewriter
**Why:** Simple, focused text directs attention to the topic

### Summary / Takeaway
**Concepts:** key points, benefits list, conclusion
**Best visuals:** Feature list, checklist, summary cards
**Remotion components:** StepList with checkmarks, Card grid, Badge labels
**Why:** Discrete items in a list are easy to scan and remember

## Animation Principles

Match animation style to concept:

| Concept Type | Animation Vocabulary Name | Why |
|-------------|--------------------------|-----|
| Sequential | `stagger-up` or `stagger-left` | Reinforces order |
| Comparison | `slide-left` + `slide-right` simultaneously | Enables comparison |
| Hierarchy | `fade-in` top-down with stagger delay | Matches structural direction |
| Growth/Change | `count-up` or ProgressBar with `fade-in` | Shows increase visually |
| State change | `glow-pulse` or `breathe` on highlighted node | Draws attention to change |
| Communication | `draw-line` between actors | Shows direction and flow |
| Summary | `stagger-up` with `spring-in` | Adds energy to static list |

## Anti-Patterns

- **Don't use a pie chart** — they're hard to read and compare. Use bar charts instead.
- **Don't use a table for comparison** — tables are for data, not storytelling. Use side-by-side cards.
- **Don't visualize everything** — some beats just need clear text on screen. A title slide is a valid visualization.
- **Don't mix metaphors** — if you started with a "building blocks" metaphor, don't switch to "flowing water" mid-video.
- **Don't animate everything simultaneously** — stagger reveals so the viewer can follow along.
