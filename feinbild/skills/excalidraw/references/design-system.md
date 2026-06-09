# Visual-argument Methodology

Diagrams should **argue**, not just **display**. Pick complexity from
*audience capability*, not from a universal "simpler is better" rule.

## Good diagrams

- Show **causality** (A causes B, not just A and B).
- Show **flow** (where attention should land first, what follows).
- Show **relationship** (X is part of Y, X depends on Y, X competes with Y).

## Anti-patterns

- A grid of unrelated boxes with no edges — that's a list, not a diagram.
- Every box the same color and size — no hierarchy.
- Generic 4-box "service → service → service → cloud" flow for an audience
  that could handle real subsystems.
- A 20-node architecture diagram for an audience that cares about outcomes,
  not internals.

## Audience-calibrated complexity

| Audience | Best complexity | What to preserve | What to simplify |
|---|---|---|---|
| Pupils / beginners | Simple | One causal idea, concrete metaphor, 3-5 labeled parts | Protocol names, nested subsystems, implementation details |
| General public / non-technical | Simple–Medium | Human-visible outcome, before/after, high-level flow | Kernel/user split, build pipelines, scheduling |
| Executives | Simple–Medium | Risk, cost, ownership, operational dependency, decision points | Low-level components unless they affect risk or cost |
| Product / project managers | Medium | Responsibilities, interfaces, timeline, dependencies, failure points | Raw code/API details |
| Technical managers / architects | Medium–Deep | Boundaries, ownership, integration surfaces, deploy/runtime split | Incidental implementation detail |
| Firmware / embedded engineers | Deep | HW/SW boundaries, bus protocols, drivers, RTOS tasks, boot/update | Marketing abstractions |
| Linux / platform engineers | Deep | Boot chain, BSP, kernel/user split, Yocto layers, services, observability | Business-only framing |
| Safety / QA / manufacturing | Deep | HIL loop, fault paths, watchdogs, rollback, test evidence | Unrelated app internals |

## Complexity tiers

### Simple (3-5 nodes, narrow canvas)

One main flow, big labels, metaphor over implementation. One canvas teaches
one idea. Good for pupils, beginners, intros. Declare a narrow canvas such
as `canvas 1720x480`.

### Medium (6-10 nodes, 2-4 zones, narrow-to-wide canvas)

Labeled interfaces, one or two secondary flows, callouts for risk or
ownership. Good for managers, mixed audiences, technical overviews.
Declare a wider canvas such as `canvas 3440x960` for breathing room.

### Deep (10-20+ nodes, large virtual canvas)

Full diagram, multiple lanes/zones/layers, typed arrows for different
flows, real artifacts / protocols / tasks / drivers, callouts for timing
or safety. Good for embedded / platform / safety / architecture audiences.

**At deep complexity, declare a large `canvas 6880x2880` (16× the pixel
area of a narrow canvas). Use coordinates in that range. Use larger fonts
(48-64 for body, 96-128 for titles).**

### Choosing the tier

Before drafting DSL, write a one-line decision:

```
Audience: embedded firmware engineers
Decision: deep diagram — preserve buses, ISR/task boundaries, update flow,
          safety mechanisms.
```

If the audience is mixed, create two diagrams: overview first (simple/medium
on a narrow canvas), deep appendix second (large `canvas 6880x2880`).

## Visual vocabulary

Stable shape/color/placement conventions for technical diagrams so the same
concept reads the same across decks:

| Concept | Shape / style | Typical placement |
|---|---|---|
| MCU / real-time controller | `box`, strong outline | Right or lower device domain |
| Linux SoC / application processor | `box` fill:primary | Left or central device domain |
| Sensor / actuator | `ellipse` fill:surface-2 | Hardware bottom band |
| Bus / interface | `lane` orient:horizontal | Between domains |
| Queue / broker | `box` fill:tertiary | Between producers/consumers |
| Database / storage | `box` fill:data | Data/storage lane |
| Safety / fault component | `box` fill:error or fill:warning | Edge / side lane |
| Build / release artifact | `box` fill:surface | Build-time lane |
| Cloud / fleet service | `zone` "Cloud" containing inner boxes | Top / right external |
| Factory / HIL rig | `zone` fill:neutral-soft | Bottom / left external |

## Arrow discipline

Most bad diagrams fail at arrows, not boxes. Ten principles, in order
of importance:

1. **Arrows are for meaningful movement / dependency**: request, event,
   command, data, interrupt, update, config, telemetry, fault. Not "is
   near" or "related to" — use grouping/boundaries for those.
2. **Primary flow first**: one dominant path, drawn clearly; secondary
   paths fewer, thinner, muted, or in a side lane.
3. **Avoid all-to-all meshes**: introduce a bus, broker, gateway, event
   stream, or boundary instead of every pairwise edge.
4. **Arrows do not cross boxes**: if they would, route around with `via:`
   or move the boxes.
5. **Minimize crossings**: zero is ideal; 1-2 acceptable in a deep diagram
   if they're separated and labeled; more = layout is wrong.
6. **Label only what isn't obvious**: `SPI`, `MQTT`, `interrupt`, `OTA
   image` — useful. `uses`, `calls`, `data` — usually too vague.
7. **Different styles for different flows**:
   - `style:solid color:ink` = runtime request/command/control
   - `style:dashed color:neutral-strong` = config / update / deployment
   - `style:dotted color:neutral` = telemetry / logging / monitoring
   - `color:danger` = fault / safety path
   - `weight:primary` = happy path emphasis
8. **Use ports**: `arrow a:right -> b:left` makes intent explicit and
   keeps layout predictable.
9. **Lane-to-lane flow over diagonal spaghetti**: place components in
   `lane`s or `zone`s; arrows run mostly horizontal or vertical.
10. **When in doubt, remove arrows**: 8 boxes and 5 excellent arrows beats
    8 boxes and 20 mediocre arrows.

## When to use Excalidraw vs SVG

- **Excalidraw** — boxes-and-arrows, conceptual flows, architectures.
- **SVG** — quantitative data (bars, axes, trend lines), custom infographics.
