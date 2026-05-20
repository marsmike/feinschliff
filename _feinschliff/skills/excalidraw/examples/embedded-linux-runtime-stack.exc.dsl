# diagram_brief: audience=linux-platform-engineers complexity=deep type=embedded-linux-runtime-stack
# teaches: boot chain at bottom, kernel/BSP, userspace platform, product services on top,
#          fleet/observability as external planes
# virtual canvas: 6880x2880

canvas 6880x2880

# ============================================================================
# Layered zones — boot at bottom, product services at top
# ============================================================================

zone z_fleet   100,40    5660x360 "Cloud / Fleet"           fill:surface
zone z_app     100,460   5660x460 "Product Services (userspace)"  fill:surface-2
zone z_plat    100,980   5660x500 "Platform Services (systemd)"   fill:surface-2
zone z_kern    100,1540  5660x500 "Kernel / BSP"            fill:surface-2
zone z_boot    100,2100  5660x340 "Boot Chain"              fill:surface
zone z_hw      100,2500  5660x320 "SoC / Board Hardware"    fill:surface

# ============================================================================
# Fleet
# ============================================================================
box fl_ingest  200,140 1400x220 "Telemetry Ingestion"      fill:primary
box fl_devmgmt 1680,140 1400x220 "Device Mgmt / OTA"        fill:secondary
box fl_obs     3160,140 1400x220 "Observability\n(Grafana / Loki)" fill:tertiary
box fl_artifact 4640,140 1120x220 "Artifact Store\n+ SBOMs"  fill:secondary

# ============================================================================
# Product services
# ============================================================================
box ps_gw      200,560 1500x340 "Gateway Service\n(gRPC + REST)" fill:primary
box ps_proto   1780,560 1500x340 "Protocol Adapter\n(Modbus / OPC UA)" fill:secondary
box ps_infer   3360,560 1500x340 "On-device Inference\n(ONNX runtime)" fill:tertiary
box ps_ui      4940,560 800x340  "Local UI"                 fill:tertiary

# ============================================================================
# Platform services
# ============================================================================
box pl_systemd 200,1080 1300x320 "systemd"                  fill:primary
box pl_dbus    1580,1080 1100x320 "D-Bus"                    fill:secondary
box pl_udev    2760,1080 1100x320 "udev /\nhotplug"          fill:secondary
box pl_log     3940,1080 1100x320 "journald\n+ rsyslog"      fill:tertiary
box pl_ota     5120,1080 620x320  "RAUC /\nMender"           fill:secondary
box pl_wdog    200,1340 5540x100  "Watchdog daemon · brownout reset · safe-state hook"  fill:warning

# ============================================================================
# Kernel / BSP
# ============================================================================
box kr_kernel  200,1640 1400x360 "Linux Kernel"            fill:primary
box kr_dt      1680,1640 1300x360 "Device Tree\n+ pinctrl"  fill:secondary
box kr_drivers 3060,1640 1300x360 "Drivers\n(net / storage / can)" fill:secondary
box kr_fs      4440,1640 1300x360 "Filesystems\n(ext4 / overlay)" fill:secondary

# ============================================================================
# Boot chain
# ============================================================================
box bc_rom     200,2160 800x240 "Boot ROM"             fill:ink
box bc_spl     1080,2160 800x240 "SPL / TF-A"          fill:primary
box bc_uboot   1960,2160 1100x240 "U-Boot\n(signed)"   fill:primary
box bc_initrd  3140,2160 1100x240 "initramfs"          fill:tertiary
box bc_systemd 4320,2160 1420x240 "systemd PID 1"      fill:primary

# ============================================================================
# Hardware
# ============================================================================
box hw_soc     200,2560 1400x220 "i.MX 8M\nCortex-A53"  fill:primary
box hw_mem     1680,2560 1100x220 "DDR4\n+ eMMC"        fill:surface-2
box hw_net     2860,2560 1100x220 "GbE + WiFi"          fill:surface-2
box hw_io      4040,2560 1100x220 "CAN + RS-485 + USB"  fill:surface-2
box hw_radio   5220,2560 520x220  "BLE 5"                fill:surface-2

# ============================================================================
# Arrows — boot sequence + runtime + telemetry + OTA
# ============================================================================

# Boot sequence (1-5)
arrow bc_rom:right   -> bc_spl:left      color:primary weight:primary label:"1"
arrow bc_spl:right   -> bc_uboot:left    color:primary weight:primary label:"2"
arrow bc_uboot:right -> bc_initrd:left   color:primary weight:primary label:"3 load"
arrow bc_initrd:right -> bc_systemd:left color:primary weight:primary label:"4 pivot"
arrow bc_systemd:top -> pl_systemd:bottom color:primary weight:primary route:elbow label:"5 PID 1"

# Kernel → platform (modules / drivers)
arrow kr_drivers:top -> pl_udev:bottom color:secondary route:elbow label:"hotplug"
arrow kr_fs:top      -> pl_systemd:bottom color:secondary route:elbow label:"mounts"

# Platform → product services
arrow pl_systemd:top -> ps_gw:bottom color:primary weight:primary route:elbow label:"unit start"
arrow pl_dbus:top    -> ps_proto:bottom color:secondary route:elbow label:"signal"
arrow pl_udev:top    -> ps_infer:bottom style:dashed color:secondary route:elbow label:"device"

# Product → fleet (telemetry / control)
arrow ps_gw:top      -> fl_ingest:bottom color:primary weight:primary route:elbow label:"MQTT"
arrow ps_gw:top      -> fl_devmgmt:bottom color:secondary route:elbow label:"control"
arrow pl_log:top     -> fl_obs:bottom style:dotted color:neutral route:elbow label:"logs"

# OTA path (dashed, top-down through layers)
arrow fl_artifact:bottom -> pl_ota:top color:secondary style:dashed route:elbow label:"bundle"
arrow pl_ota:bottom  -> kr_fs:top color:secondary style:dashed route:elbow label:"install"

# Hardware to kernel (drivers bind here)
arrow hw_soc:top     -> kr_kernel:bottom color:primary route:elbow label:"SoC pkt"
arrow hw_net:top     -> kr_drivers:bottom color:secondary route:elbow label:"net"
arrow hw_io:top      -> kr_drivers:bottom color:secondary route:elbow label:"can/uart"

# Safety: watchdog daemon (running in pl_wdog band) → systemd
arrow pl_wdog:top    -> pl_systemd:bottom color:danger weight:primary route:elbow label:"reboot req"
