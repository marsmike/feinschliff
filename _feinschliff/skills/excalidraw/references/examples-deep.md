# Excalidraw — Deep Architecture Examples

These examples target the `excalidraw-diagram-full` layout (full-slide,
1720×720 slot, virtual 6880×2880 canvas). They demonstrate the
zone/lane/arrow-routing primitives at scale and are designed for
**technical audiences** (firmware, embedded Linux, safety engineers)
who can use the implementation detail.

Source files live in `feinschliff/skills/excalidraw/examples/`.
Rendered PNGs land in `feinschliff/.debug/skills/excalidraw/examples/`
per the repo's `.debug/` mirror policy.

## Audience contrast chain — same topic, three depths

The OTA update story rendered at three audience levels demonstrates that
complexity should come from the audience, not from the topic.

### Simple — pupils (`ota-update-simple-pupil.exc.dsl`)

```
canvas 1720x480
ellipse cloud 80,180 280x160 "Cloud" fill:start
box check    480,180 280x160 "Device\nChecks" fill:primary
box install  880,180 280x160 "Device\nInstalls" fill:secondary
box restart  1280,180 320x160 "Device\nRestarts" fill:end

arrow cloud -> check    label:"sends update"
arrow check -> install  label:"OK"
arrow install -> restart label:"safely"
```

**Teaches:** 3-5 boxes, one main flow, big labels, metaphor language
("Device Checks") instead of implementation ("Signature Verify"). The
narrow `excalidraw-diagram` layout is the right slot — full-slide would
waste space and confuse the audience.

### Medium — executives (`ota-update-medium-executive.exc.dsl`)

Adds three zones (Release Engineering / Fleet Rollout / Operations), 9
named boxes, decision gates, and red callouts for the rollback path.
Canvas is 3440×960 (2× narrow virtual viewport) so labels stay readable
without overwhelming the slide. **Teaches:** zones for responsibility
boundaries, color for risk, and a one-line "Risk / Cost / Ownership"
callout strip at the bottom.

### Deep — embedded engineers (`secure-boot-ota-ab-flow.exc.dsl`)

Five zones (Build/Sign · Boot Chain · A/B Slots · Health/Rollback · Trust
Material), ~30 boxes, numbered boot sequence, anti-rollback fuses, audit
log dotted-line telemetry, and dashed rollback paths. Canvas is
6880×2880; needs `excalidraw-diagram-full` layout. **Teaches:** all the
arrow-discipline principles from `design-system.md` — typed arrows,
numbered primary flow, fault paths in red with weight:primary, dashed
config edges, dotted telemetry.

## Stack archetypes

### MCU firmware stack (`embedded-mcu-firmware-stack.exc.dsl`)

Six layered zones from Hardware (bottom) through HAL / RTOS / Drivers /
Middleware / Application (top). Right-edge `lane` for IRQ / DMA. The
classic Cortex-M + FreeRTOS layered architecture authors keep redrawing
from scratch.

**Teaches:**
- Bottom-up layered architecture using `zone` primitives.
- `lane orient:vertical` for the IRQ side-band crossing all layers.
- Typed arrows: `color:primary` for the sample-path control flow,
  `style:dotted color:neutral` for trace, `color:danger` for fault, and
  `style:dashed` for OTA / config movement.
- Watchdog and safety monitor as `fill:error` to communicate criticality.

### Heterogeneous Linux + MCU edge device (`linux-mcu-heterogeneous-device.exc.dsl`)

Splits the slide into Linux domain (left zone) and MCU domain (right
zone) with a vertical IPC bridge zone in the middle. Cloud sits above;
factory/service below. Real protocol names (RPMsg, Shared Memory, GPIO
IRQ, Console UART) on the bridge components.

**Teaches:** dual-domain architecture, explicit bridge primitives,
typed arrows for command vs telemetry vs fault, ownership visible at a
glance from the zone partition.

### Embedded Linux runtime stack (`embedded-linux-runtime-stack.exc.dsl`)

Six layered zones from Hardware (bottom) up through Boot Chain, Kernel/BSP,
Platform Services (systemd), Product Services, to Cloud/Fleet. Numbered
boot sequence at the bottom (ROM → SPL → U-Boot → initramfs → systemd).

**Teaches:** Linux/Yocto-aware runtime structure, the kernel/user
boundary as a zone divider, OTA bundle path dashed top-down across
multiple layers.

## What to avoid

| Bad version | Why it fails |
|---|---|
| 4-box "service → service → service → cloud" flow | Generic, no audience signal |
| Every node `fill:primary` | No hierarchy; the eye gets lost |
| 12 unlabeled arrows | Each arrow's meaning is ambiguous; reader gives up |
| Single arrow style for runtime + config + telemetry | Type erasure — can't tell control from observability |
| Arrows crossing through unrelated boxes | Implies relationships that don't exist |
| Diagonal arrows across all 6 layers | Visually chaotic; layer structure dissolves |

When you find yourself heading toward any of these, pause and check
`design-system.md` → Arrow discipline before continuing.
