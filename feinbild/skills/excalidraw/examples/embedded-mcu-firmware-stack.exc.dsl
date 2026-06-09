# diagram_brief: audience=embedded-firmware-engineers complexity=deep type=mcu-firmware-stack
# teaches: hardware-bottom-up layering, ISR side-lane, typed arrows for fault vs control,
#          watchdog and safety monitor at the boundary
# virtual canvas: 6880x2880 — large high-resolution canvas

canvas 6880x2880

# ============================================================================
# Zones — layered architecture from hardware (bottom) to application (top).
# Rendered behind foreground primitives so arrows can cross zone boundaries.
# ============================================================================

zone z_hw   100,2360 5660x460 "Hardware"           fill:surface-2
zone z_hal  100,1880 5660x440 "HAL / CMSIS"        fill:surface
zone z_rtos 100,1400 5660x440 "RTOS (FreeRTOS)"    fill:surface
zone z_drv  100,920  5660x440 "Drivers"            fill:surface
zone z_mw   100,440  5660x440 "Middleware"         fill:surface
zone z_app  100,40   5660x360 "Application Tasks"  fill:surface

# Right side: interrupt / DMA lane spanning the full stack.
lane l_irq  5840,40 940x2780 "IRQ / DMA path" orient:vertical fill:warning

# ============================================================================
# Hardware
# ============================================================================
box hw_core   200,2480 900x280  "Cortex-M4F\nCore"            fill:primary
box hw_flash  1180,2480 700x280 "Flash\n2 MB"                 fill:surface-2
box hw_sram   1960,2480 700x280 "SRAM\n256 KB"                fill:surface-2
box hw_dma    2740,2480 700x280 "DMA\nController"             fill:tertiary
box hw_tmr    3520,2480 700x280 "Timers / PWM"                fill:surface-2
box hw_adc    4300,2480 700x280 "ADC / Sensors\n12-bit"       fill:surface-2
box hw_wdg    5080,2480 660x280 "Independent\nWatchdog"       fill:error

# ============================================================================
# HAL / CMSIS
# ============================================================================
box hal_vendor 200,2000 1200x280 "Vendor HAL\n(STM32 LL)" fill:primary
box hal_cmsis  1480,2000 1200x280 "CMSIS-Core"            fill:primary
box hal_pinmux 2760,2000 1200x280 "Pinmux / Clocks"       fill:secondary
box hal_lpm    4040,2000 1200x280 "Low-Power Modes"       fill:secondary
box hal_crypto 5320,2000 420x280  "Crypto"                fill:tertiary

# ============================================================================
# RTOS
# ============================================================================
box rtos_sched 200,1520 1400x280  "Scheduler\n(preemptive)" fill:primary
box rtos_q     1680,1520 1100x280 "Queues / Mailboxes"      fill:tertiary
box rtos_sem   2860,1520 1100x280 "Semaphores / Mutex"      fill:tertiary
box rtos_tim   4040,1520 1100x280 "Software Timers"         fill:tertiary
box rtos_isr   5220,1520 520x280  "ISR-to-Task\nBridge"     fill:warning

# ============================================================================
# Drivers
# ============================================================================
box drv_imu    200,1040 1100x280  "IMU Driver\n(SPI)"   fill:secondary
box drv_uart   1380,1040 1100x280 "UART Driver"         fill:secondary
box drv_can    2560,1040 1100x280 "CAN Driver"          fill:secondary
box drv_flash  3740,1040 1100x280 "Flash Storage"       fill:secondary
box drv_motor  4920,1040 820x280  "Motor / PWM\nDriver" fill:secondary

# ============================================================================
# Middleware
# ============================================================================
box mw_proto   200,560 1500x280  "MQTT Client" fill:primary
box mw_log     1780,560 1100x280 "Logging / Tracing"        fill:tertiary
box mw_ota     2960,560 1500x280 "OTA Update Agent"        fill:secondary
box mw_diag    4540,560 1200x280 "Diagnostics / DTC"       fill:tertiary

# ============================================================================
# Application tasks
# ============================================================================
box app_ctrl   200,120 1500x260   "Control Loop Task\n10 ms tick"     fill:primary
box app_comms  1780,120 1500x260  "Comms Task\nuplink + downlink"     fill:secondary
box app_safety 3360,120 1500x260  "Safety Monitor\nwatchdog-petting"  fill:error
box app_ui     4940,120 800x260   "UI / Display"                       fill:tertiary

# ============================================================================
# Arrows — primary flow, secondary flows, fault path.
# ============================================================================

# Sensor sample path: ADC -> DMA -> ISR -> queue -> control task. Primary.
arrow hw_adc:top  -> hw_dma:bottom  color:primary weight:primary label:"sample"
arrow hw_dma:top  -> rtos_isr:bottom color:primary weight:primary route:elbow label:"DMA cplt IRQ"
arrow rtos_isr:left -> rtos_q:right color:primary weight:primary label:"queue msg"
arrow rtos_q:top  -> app_ctrl:bottom color:primary weight:primary route:elbow label:"sensor data"

# Control output: control task -> motor driver -> hw timers/PWM
arrow app_ctrl:bottom -> drv_motor:top color:primary weight:primary route:elbow label:"setpoint"
arrow drv_motor:bottom -> hw_tmr:top color:primary route:elbow label:"PWM duty"

# Communications path: comms task -> MQTT -> UART driver -> hw
arrow app_comms:bottom -> mw_proto:top color:secondary route:elbow label:"publish"
arrow mw_proto:bottom -> drv_uart:top color:secondary route:elbow label:"frame"
arrow drv_uart:bottom -> hw_tmr:top style:dotted color:neutral-strong route:elbow label:"baud-rate timer"

# OTA path (config / update, dashed): OTA agent -> flash driver -> hw flash
arrow mw_ota:bottom -> drv_flash:top style:dashed color:neutral-strong route:elbow label:"image block"
arrow drv_flash:bottom -> hw_flash:top style:dashed color:neutral-strong route:elbow label:"sector write"

# Telemetry (dotted): logging -> UART
arrow mw_log:bottom -> drv_uart:top style:dotted color:neutral route:elbow label:"trace"

# Safety / fault path (red): watchdog -> safety monitor; brownout
# interrupts also raised over the IRQ side-lane (rendered visually
# behind these arrows by the `lane` primitive).
arrow hw_wdg:top -> app_safety:bottom color:danger weight:primary route:elbow label:"WDG reset"

# Watchdog pet: safety monitor down to wdg via dotted; obligation, not data
arrow app_safety:bottom -> hw_wdg:top style:dashed color:warning route:elbow via:5400,420;5400,2200 label:"pet"
