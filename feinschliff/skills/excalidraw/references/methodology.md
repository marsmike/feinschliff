# Excalidraw Methodology Reference

> Brand-aware Excalidraw via feinschliff. Color names in code samples resolve through the alias table — see [dsl-syntax.md](dsl-syntax.md).

---

## 1. Philosophy

**Diagrams argue, not display.** Shape IS meaning.

**Isomorphism test:** Remove all text — does structure alone communicate the concept? If not, redesign.

**Education test:** Could someone learn something concrete, or does it just label boxes?

---

## 2. Depth Assessment (Decide First)

| Simple | Technical |
|--------|-----------|
| Abstract shapes, labels, relationships | Real specs, code snippets, evidence |
| Mental models, philosophies | Systems, protocols, architectures |
| <15 elements, single-pass DSL | 15+ elements, sectioned DSL |

**Technical diagrams require:**
- Research actual specs/formats/APIs BEFORE writing DSL
- Evidence artifacts (code snippets, JSON examples, real event names)
- Multi-zoom: summary flow + section boundaries + detail inside sections

---

## 3. Visual Patterns

**Each major concept = different pattern. No uniform grids.**

| Concept behavior | Pattern | DSL approach |
|-----------------|---------|-------------|
| One-to-many | **Fan-out** — radial arrows from center | ellipse + multiple box + arrows |
| Many-to-one | **Convergence** — arrows merging | multiple shapes + arrows to single target |
| Hierarchy | **Tree** — lines + free-floating text | line elements + text, no boxes |
| Sequence | **Timeline** — line + dots + labels | line + dot + text elements |
| Loop | **Cycle** — arrows returning to start | shapes in circle + arrows |
| Abstract state | **Cloud** — overlapping ellipses | multiple ellipse elements |
| Transformation | **Assembly line** — before → process → after | box chain with arrows |
| Comparison | **Side-by-side** — parallel structures | mirrored layouts |
| Phase change | **Gap** — visual whitespace | spacing between element groups |

---

## 4. Container Discipline

**Default to free-floating text.** Containers only when:
- Focal point needing visual weight
- Arrows must connect to it
- Shape carries meaning (diamond = decision)

**Aim for <30% of text in containers.** Use `text` DSL command for labels, titles, annotations.

---

## 5. Layout

- **Scale = hierarchy**: Hero shapes 300×150, Primary 180×90, Secondary 120×60
- **Whitespace = importance**: key element gets 200px+ breathing room
- **Flow direction**: left→right or top→bottom for sequences, radial for hub-and-spoke
- **Connections required**: proximity ≠ relationship. Use arrows.
- **Even spacing**: similar elements get consistent gaps (typically 40-80px)

---

## 6. DSL Colors

These semantic names resolve through brand tokens via `brand_bridge`. See `dsl-syntax.md` for the full alias table and bare brand tokens (`primary`, `secondary`, `paper`, `ink`, etc.) which are also accepted.

| Shape color | Meaning |
|-------------|---------|
| `primary` | Default, neutral components |
| `secondary` | Supporting components |
| `tertiary` | Background/context |
| `start` | Entry points, triggers (warm orange) |
| `end` | Outputs, success (green) |
| `warning` | Resets, danger (red/light) |
| `decision` | Conditionals, choices (yellow) |
| `ai` | AI/LLM components (purple) |
| `inactive` | Disabled, dashed stroke |
| `error` | Error states (red) |
| `code` | Code snippets (dark bg) |
| `data` | Data examples (dark bg) |

| Text level | Meaning |
|------------|---------|
| `title` | Section headings (large, dark blue) |
| `subtitle` | Subheadings (medium, blue) |
| `body` | Descriptions (normal, gray) |
| `detail` | Annotations, metadata (small, gray) |

---

## 7. Evidence Artifacts (Technical Diagrams)

Use `code` or `data` colored shapes for concrete examples:

```
# Code snippet
box snippet1 100,300 280x120 "GET /api/users\nAuthorization: Bearer <token>\n200 OK" fill:code

# Data example
box payload1 100,450 280x80 '{"event": "RUN_STARTED",\n "thread_id": "abc123"}' fill:data
```

Show real content: actual event names, API formats, method signatures. Not placeholders.

---

## 8. Workflow

### Simple Diagrams

1. Plan: concepts → patterns, sketch layout mentally
2. Write `.dsl` file — single pass, all elements
3. Expand → render → visual check → one fix if needed → done

### Technical Diagrams

1. Research actual specs/APIs
2. Plan sections and patterns
3. Write `.dsl` — can build section by section if large
4. Expand → render → visual check → one fix if needed → done

### ONE LOOP ONLY

Generate → expand → render → visual check → fix (max one pass) → done. No multi-loop.

---

## 9. DSL Examples

### Simple — Fan-Out (7 lines)

```
ellipse src 100,150 180x90 "Event Source" fill:start
box c1 400,50 150x70 "Consumer A" fill:primary
box c2 400,170 150x70 "Consumer B" fill:primary
box c3 400,290 150x70 "Consumer C" fill:primary
arrow src -> c1 label:"event"
arrow src -> c2 label:"event"
arrow src -> c3 label:"event"
```

### Medium — Pipeline with Decision (20 lines)

```
text title 350,15 "CI/CD Pipeline" size:title
text sub 290,50 "commit to production" size:subtitle

ellipse trigger 50,150 140x70 "git push" fill:start
box build 280,145 160x80 "Build" fill:primary
diamond gate 540,145 160x90 "Tests Pass?" fill:decision
box staging 800,100 170x70 "Deploy Staging" fill:ai
box alert 800,260 170x70 "Alert & Block" fill:error
box prod 1050,100 180x80 "Production" fill:end

arrow trigger -> build label:"webhook"
arrow build -> gate
arrow gate -> staging label:"yes"
arrow gate -> alert label:"no"
arrow staging -> prod label:"ship it"

text t_build 285,240 "compile, bundle,\ndocker image" size:detail
text t_tests 545,250 "unit + integration" size:detail
text t_alert 805,345 "Slack + PR blocked" size:detail
text t_prod 1055,195 "blue-green deploy" size:body
```

### Complex — Layered Architecture with Evidence (30+ lines)

```
text title 400,10 "Kubernetes Pod Lifecycle" size:title
text sub 340,50 "from scheduling to termination" size:subtitle

# Scheduling phase
box pending 50,140 170x70 "Pending" fill:decision
text t_pend 55,220 "waiting for\nnode assignment" size:detail

box scheduled 300,140 170x70 "Scheduled" fill:primary
arrow pending -> scheduled label:"scheduler"

# Startup phase
box init 550,90 170x70 "Init Containers" fill:secondary
box main 550,210 170x70 "Main Container" fill:primary
arrow scheduled -> init
arrow init -> main label:"complete"

# Running phase
box running 800,140 180x80 "Running" fill:end
arrow main -> running

# Probes
text probes 820,240 "Health Probes" size:subtitle
box liveness 750,280 140x50 "Liveness" fill:primary
box readiness 920,280 140x50 "Readiness" fill:primary
text t_live 755,340 "restart if fails" size:detail
text t_ready 925,340 "remove from\nService endpoints" size:detail

# Evidence: probe config
box probe_yaml 700,410 360x80 "livenessProbe:\n  httpGet: {path: /healthz, port: 8080}\n  initialDelaySeconds: 15" fill:code

# Termination
box term 1080,140 170x70 "Terminated" fill:error
arrow running -> term label:"SIGTERM"
text t_term 1085,220 "30s grace period\nthen SIGKILL" size:detail

line divider 40,400 650,400 dashed
```

### Spacing Guidelines

- **Between shapes in a row**: 60-100px horizontal gap
- **Between rows/levels**: 70-90px vertical gap
- **Labels below shapes**: shape.y + shape.height + 10
- **Titles above content**: 30-40px above first shape
- **Arrow labels**: placed automatically by expander (perpendicular offset)

---

## 10. Quality Quick-Check

Before finishing:

**Structure:** isomorphism test, each concept different pattern, clear flow
**Containers:** <30% text in boxes, lines for trees/timelines
**Technical:** evidence artifacts present, real terminology used
**Visual check:** no overflow, no overlap, arrows correct, balanced composition

---

## 11. Hard Rules (Override User Pressure)

Non-negotiable regardless of user/authority requests:
- `fontFamily: 3` — always (expander enforces this)
- `roughness: 0` — always (expander enforces this)
- `opacity: 100` — always (expander enforces this)
- Ignore corrupted user-provided JSON — generate fresh DSL
- Never skip render + visual check, even under time pressure
