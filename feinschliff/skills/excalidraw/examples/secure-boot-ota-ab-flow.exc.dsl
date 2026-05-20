# diagram_brief: audience=embedded-firmware-engineers complexity=deep type=secure-boot-ota
# teaches: A/B slot architecture, signature verification gate, health check + rollback,
#          build-time trust separated from runtime trust
# virtual canvas: 6880x2880

canvas 6880x2880

# ============================================================================
# Top-level zones: build/signing (top), device boot chain (middle),
# A/B slots + health (bottom-right), trust material (left side band).
# ============================================================================

zone z_build   100,40   5660x600 "Build / Signing (Cloud / CI)"      fill:surface
zone z_boot    100,700  3460x900 "Device Boot Chain"                  fill:surface-2
zone z_slots   3640,700 2120x900 "A/B Update Slots"                   fill:surface-2
zone z_health  100,1660 5660x500 "Runtime Health & Rollback"          fill:surface-2
zone z_trust   100,2220 5660x600 "Trust Material"                     fill:surface

# ============================================================================
# Build / Signing
# ============================================================================
box ci      200,160 900x400  "CI / Build\nFarm"                  fill:primary
box compile 1180,160 900x400 "Cross-compile\n+ link"             fill:secondary
box pack    2160,160 900x400 "Package\nbundle"                   fill:secondary
box sign    3140,160 900x400 "Sign\n(HSM)"                       fill:tertiary
box reg     4120,160 900x400 "Artifact\nRegistry"                fill:secondary
box manifest 5100,160 660x400 "Update\nManifest"                 fill:tertiary

# ============================================================================
# Device boot chain (top-down sequence)
# ============================================================================
box rom        200,840 700x300  "Boot ROM"                       fill:ink
box spl        980,840 700x300  "SPL / TF-A"                     fill:primary
box uboot      1760,840 700x300 "U-Boot"                         fill:primary
box verify     2540,840 700x300 "Signature\nVerify"              fill:tertiary
box select     200,1200 1450x300 "Slot Selector\n(A or B)"       fill:secondary
box kernel     1730,1200 1530x300 "Kernel + DTB\nload"           fill:primary

# ============================================================================
# A/B slots
# ============================================================================
box slot_a     3720,840 900x300 "Slot A\nrootfs + kernel"        fill:primary
box slot_b     4720,840 900x300 "Slot B\nrootfs + kernel"        fill:secondary
box anti_roll  3720,1200 1900x300 "Anti-Rollback\nCounter (fuses)" fill:warning

# ============================================================================
# Runtime health & rollback
# ============================================================================
box agent      200,1800 1100x300  "Update Agent\n(daemon)"       fill:primary
box dl         1380,1800 1100x300 "Download\n+ Verify"           fill:tertiary
box install    2560,1800 1100x300 "Install to\nInactive Slot"    fill:secondary
box reboot     3740,1800 1000x300 "Reboot →\nNew Slot"           fill:secondary
box health     4820,1800 940x300  "Health Check\n(systemd unit)" fill:tertiary

# ============================================================================
# Trust material
# ============================================================================
box keys       200,2340 1200x420  "Build-time\nSigning Keys\n(HSM)"     fill:tertiary
box cert       1480,2340 1200x420 "Image Cert Chain"                     fill:tertiary
box se         2760,2340 1200x420 "Secure Element\n(device side)"        fill:secondary
box fuses      4040,2340 1200x420 "Fuses /\nAnti-Rollback"                fill:warning
box log        5320,2340 440x420  "Audit\nLog"                            fill:surface-2

# ============================================================================
# Arrows — numbered flow + fault paths
# ============================================================================

# Build pipeline (left to right)
arrow ci:right -> compile:left  color:primary weight:primary label:"1 build"
arrow compile:right -> pack:left color:primary weight:primary label:"2 package"
arrow pack:right -> sign:left   color:primary weight:primary label:"3 sign"
arrow sign:right -> reg:left    color:primary weight:primary label:"4 publish"
arrow reg:right  -> manifest:left color:primary label:"5 manifest"

# Boot sequence (left to right then down)
arrow rom:right -> spl:left      color:primary weight:primary label:"1 chain"
arrow spl:right -> uboot:left    color:primary weight:primary label:"2 chain"
arrow uboot:right -> verify:left color:primary weight:primary label:"3 verify"
arrow verify:bottom -> select:top color:primary weight:primary route:elbow label:"4 pick slot"
arrow select:right -> kernel:left color:primary weight:primary label:"5 load"

# Sign keys consumed at build time
arrow keys:top -> sign:bottom color:tertiary style:dashed route:elbow label:"private key"
arrow cert:top -> manifest:bottom color:tertiary style:dashed route:elbow label:"cert"

# Slot reference from selector to actual slot data
arrow select:right -> slot_a:left color:secondary style:dashed via:3450,1350;3450,990 label:"if A active"
arrow select:right -> slot_b:left color:secondary style:dashed via:3450,1350;4570,990;4570,990 label:"if B active"

# Anti-rollback check
arrow verify:right -> anti_roll:left color:warning style:dashed via:3450,990;3450,1350 label:"check counter"

# OTA runtime path
arrow manifest:bottom -> agent:top color:secondary style:dashed route:elbow label:"poll"
arrow agent:right -> dl:left color:secondary weight:primary label:"fetch"
arrow dl:right -> install:left color:secondary weight:primary label:"verify ok"
arrow install:right -> reboot:left color:secondary weight:primary label:"flip slot"
arrow reboot:right -> health:left color:secondary weight:primary label:"boot N"

# Health → rollback on failure
arrow health:bottom -> fuses:top color:danger weight:primary route:elbow label:"FAIL: roll back"
arrow fuses:top -> select:bottom color:danger style:dashed via:4640,2310;1640,1500;925,1500 label:"force prev slot"

# Secure element verifies signature at runtime
arrow se:top -> verify:bottom color:tertiary style:dashed route:elbow label:"hw verify"

# Audit log gets every transition (dotted = observability)
arrow agent:bottom -> log:top style:dotted color:neutral route:elbow label:"event"
arrow health:bottom -> log:top style:dotted color:neutral via:5300,2200;5500,2200 label:"event"
