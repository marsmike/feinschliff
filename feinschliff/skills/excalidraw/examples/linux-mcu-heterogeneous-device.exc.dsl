# diagram_brief: audience=embedded-engineers complexity=deep type=heterogeneous-edge-device
# teaches: dual-domain split (Linux SoC vs MCU RTOS), shared IPC bridge,
#          typed arrows for command vs telemetry vs fault, cloud + factory at edges
# virtual canvas: 6880x2880

canvas 6880x2880

# ============================================================================
# Zones — Cloud (top), Linux + MCU domains (middle), Factory (bottom)
# ============================================================================

zone z_cloud   100,40    5660x420 "Cloud / Fleet Backend"     fill:surface
zone z_linux   100,520   2780x1640 "Linux Application Processor"  fill:surface-2
zone z_bridge  2920,520  720x1640 "IPC Bridge"                fill:warning
zone z_mcu     3680,520  2080x1640 "MCU Real-time Controller" fill:surface-2
zone z_hw      100,2220  5660x300 "Board Hardware"            fill:surface
zone z_fact    100,2560  5660x260 "Factory / Service"         fill:surface

# ============================================================================
# Cloud / fleet
# ============================================================================
box cl_ingest  200,140 1300x240 "Telemetry\nIngestion"   fill:primary
box cl_devmgmt 1580,140 1300x240 "Device Mgmt /\nOTA Rollout" fill:secondary
box cl_dt      2960,140 1300x240 "Digital Twin\n/ Diagnostics" fill:tertiary
box cl_alarms  4340,140 1420x240 "Alarms / Pager"          fill:error

# ============================================================================
# Linux side
# ============================================================================
box lx_gw    200,640 1100x340  "Gateway\nService"          fill:primary
box lx_upd   1380,640 1100x340 "Update Manager"            fill:secondary
box lx_db    200,1040 1100x340 "Local DB\n(SQLite)"        fill:data
box lx_log   1380,1040 1100x340 "Logging /\nMetrics"       fill:tertiary
box lx_net   200,1440 1100x340  "Network\nMgmt"            fill:secondary
box lx_ui    1380,1440 1100x340 "Local UI /\nKiosk"        fill:tertiary
box lx_sec   200,1840 2380x240  "Secure Boot + LUKS + systemd"     fill:tertiary

# ============================================================================
# IPC bridge (vertical column)
# ============================================================================
box bg_rpmsg   3000,640 580x340  "RPMsg\n/ MailBox"         fill:warning
box bg_sharedm 3000,1040 580x340 "Shared\nMemory"           fill:warning
box bg_gpio    3000,1440 580x340 "GPIO IRQ\nlines"          fill:warning
box bg_uart    3000,1840 580x240 "Console UART\n(debug)"    fill:surface-2

# ============================================================================
# MCU side
# ============================================================================
box mc_ctrl   3760,640 1100x340 "Control Task\n1 kHz"      fill:primary
box mc_acq    4940,640 800x340  "Sensor Acq\nDMA"          fill:secondary
box mc_safety 3760,1040 1100x340 "Safety Monitor\n+ Watchdog"  fill:error
box mc_motor  4940,1040 800x340 "Motor /\nPWM"             fill:secondary
box mc_log    3760,1440 1100x340 "Trace / Log\nBuffer"     fill:tertiary
box mc_ota    4940,1440 800x340 "MCU OTA\nAgent"           fill:secondary
box mc_isr    3760,1840 1980x240 "ISR vector + RTOS scheduler"   fill:warning

# ============================================================================
# Hardware
# ============================================================================
box hw_sensors 200,2300 1400x180  "Sensors (IMU, temp, current)" fill:surface-2
box hw_motors  1680,2300 1400x180 "Actuators / Motors"           fill:surface-2
box hw_radios  3160,2300 1400x180 "Radios (BLE / WiFi)"          fill:surface-2
box hw_pmic    4640,2300 1120x180 "PMIC / Power"                 fill:surface-2

# ============================================================================
# Factory / Service
# ============================================================================
box fa_flash    200,2620 1300x180 "Flash + Provision"       fill:primary
box fa_calib    1580,2620 1300x180 "Calibration Bench"      fill:secondary
box fa_test     2960,2620 1300x180 "End-of-Line Test"       fill:tertiary
box fa_service  4340,2620 1420x180 "Field Service Tool"     fill:secondary

# ============================================================================
# Arrows — typed by flow kind
# ============================================================================

# Sensor → MCU acquisition → control → Linux gateway → cloud (primary)
arrow hw_sensors:top  -> mc_acq:bottom    color:primary weight:primary route:elbow label:"DMA"
arrow mc_acq:left    -> mc_ctrl:right    color:primary weight:primary label:"queue"
arrow mc_ctrl:left   -> bg_rpmsg:right   color:primary weight:primary label:"telemetry"
arrow bg_rpmsg:left  -> lx_gw:right      color:primary weight:primary label:"frame"
arrow lx_gw:top      -> cl_ingest:bottom color:primary weight:primary route:elbow label:"MQTT"

# Cloud → Linux → MCU command (control plane)
arrow cl_devmgmt:bottom -> lx_upd:top color:secondary style:dashed route:elbow label:"OTA cmd"
arrow lx_upd:right     -> bg_sharedm:left color:secondary style:dashed label:"image"
arrow bg_sharedm:right -> mc_ota:left  color:secondary style:dashed label:"image block"

# Motor control loop (intra-MCU)
arrow mc_ctrl:right -> mc_motor:left color:primary weight:primary label:"setpoint"
arrow mc_motor:bottom -> hw_motors:top color:primary route:elbow label:"PWM"

# Safety fault path (red)
arrow mc_safety:left  -> bg_gpio:right color:danger weight:primary label:"fault"
arrow bg_gpio:left   -> lx_gw:right    color:danger weight:primary via:2950,1610;1300,1610 label:"alert"
arrow lx_gw:top      -> cl_alarms:bottom color:danger weight:primary route:elbow via:5050,500 label:"page"

# Diagnostics (dotted)
arrow mc_log:left   -> bg_uart:right color:neutral style:dotted label:"trace"
arrow bg_uart:left  -> lx_log:right  color:neutral style:dotted label:"forward"
arrow lx_log:top    -> cl_dt:bottom  color:neutral style:dotted route:elbow label:"metrics"

# Factory provisioning at boot time
arrow fa_flash:top   -> lx_sec:bottom color:tertiary style:dashed route:elbow label:"image + keys"
arrow fa_calib:top   -> mc_safety:bottom color:tertiary style:dashed via:1900,2470;3850,2470;3850,1380 label:"calib data"
arrow fa_test:top    -> mc_isr:bottom color:tertiary style:dashed route:elbow label:"self-test"
