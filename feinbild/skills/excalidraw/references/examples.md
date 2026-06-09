# Excalidraw DSL Examples

These examples teach pattern variety and shape-as-meaning, not just syntax — use them as blueprints, not templates to clone linearly.

> **For deep architectural diagrams** (10-20+ nodes, zones, typed arrows on
> a large `canvas 6880x2880`), see
> [examples-deep.md](examples-deep.md) — full MCU firmware stacks,
> embedded Linux runtimes, OTA flows, and audience-contrast pairs.

## Simple — Fan-Out

Use when one source distributes the same event or payload to multiple independent consumers.

```
canvas 800x400
ellipse src 100,150 180x90 "Event Source" fill:start
box c1 400,50 150x70 "Consumer A" fill:primary
box c2 400,170 150x70 "Consumer B" fill:primary
box c3 400,290 150x70 "Consumer C" fill:primary
arrow src -> c1 label:"event"
arrow src -> c2 label:"event"
arrow src -> c3 label:"event"
```

Teaches: ellipse for origin nodes (shape-as-meaning), `fill:start` to mark entry-points, label arrows to name the payload.

## Medium — CI/CD Pipeline with Decision

Use when a workflow has a conditional gate that forks into a happy path and an error path.

```
canvas 1280x420
text ttl 350,15 "CI/CD Pipeline" size:title
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

Teaches: diamond for binary decisions, semantic color variety across a single flow (`start`/`decision`/`ai`/`error`/`end`), annotation `text` nodes for inline detail.

## Complex — Multi-zoom Architecture

Use when a system spans multiple architectural layers and the diagram must convey both structure (zones) and internal detail simultaneously.

```
canvas 1400x700

# ── Zone dividers ──────────────────────────────────────────────
line div1 460,40 460,660 dashed
line div2 920,40 920,660 dashed

# ── Zone headers ───────────────────────────────────────────────
text zh_edge 130,20 "Edge" size:title
text zh_app 570,20 "Application" size:title
text zh_data 1060,20 "Data" size:title

# ── Edge zone ──────────────────────────────────────────────────
box browser 60,120 200x80 "Browser" fill:primary
box cdn 60,260 200x80 "CDN" fill:secondary

# ── Application zone ───────────────────────────────────────────
diamond authgate 530,120 200x90 "Auth required?" fill:decision
box gateway 530,280 200x80 "API Gateway" fill:primary
box llm 530,430 200x80 "LLM Service" fill:ai
box worker 760,280 180x80 "Background Worker" fill:secondary

# ── Data zone ──────────────────────────────────────────────────
box pg 970,120 300x120 "Postgres\nSELECT * FROM events\nWHERE user_id = $1" fill:code
box redis 970,310 300x100 "Redis Cache\n{\"ttl\":300,\"hits\":14}" fill:data
box blob 970,470 300x80 "Object Storage" fill:neutral

# ── Arrows — zone-crossing ──────────────────────────────────────
arrow browser -> authgate label:"request"
arrow cdn -> gateway label:"static miss"
arrow authgate -> gateway label:"allowed"
arrow gateway -> pg label:"query"
arrow gateway -> redis label:"cache get"

# ── Arrows — intra-zone ─────────────────────────────────────────
arrow gateway -> llm label:"prompt"
arrow gateway -> worker label:"enqueue"
arrow llm -> redis label:"cache set"
arrow worker -> blob label:"write artifact"
```

Teaches: `line dashed` zone dividers for spatial structure, `size:title` free-floating headers to label regions, `fill:code` and `fill:data` boxes to embed literal content, arrows that cross zone boundaries to show coupling.
