# diagram_brief: audience=pupils complexity=simple type=ota-update-overview
# teaches: 4-box linear flow with a single causal idea; metaphor over implementation
# canvas: 1720x480 (narrow canvas — no virtual viewport)

canvas 1720x480

text title 100,40 "How a Device Gets Updated" size:title

ellipse cloud 80,180 280x160 "Cloud" fill:start
box check    480,180 280x160 "Device\nChecks" fill:primary
box install  880,180 280x160 "Device\nInstalls" fill:secondary
box restart  1280,180 320x160 "Device\nRestarts" fill:end

arrow cloud -> check    label:"sends update"
arrow check -> install  label:"OK"
arrow install -> restart label:"safely"
