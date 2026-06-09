# diagram_brief: audience=executives complexity=medium type=ota-rollout-risk-overview
# teaches: 3 zones (release / fleet / operations), risk/cost callouts,
#          medium complexity with named decision gates
# canvas: 3440x960 (wider canvas — narrow flow with breathing room)

canvas 3440x960

text title 100,40 "OTA Rollout: From Release to Rollback" size:title

zone z_rel 100,140 1100x720 "Release Engineering" fill:surface
zone z_flt 1240,140 1100x720 "Fleet Rollout"       fill:surface
zone z_ops 2380,140 960x720 "Operations"           fill:surface

box r_build 180,240 380x180 "Build\n+ Sign"           fill:primary
box r_test  600,240 540x180 "Test Gate\n(security + SBOM)" fill:tertiary
box r_pub   180,500 960x180 "Publish to Artifact Registry"  fill:secondary

box f_canary 1320,240 380x180 "Canary\n(1%)"          fill:warning
box f_phase  1740,240 380x180 "Phased\n(10/25/50%)"   fill:secondary
box f_full   1320,500 820x180 "Full Rollout"          fill:primary

box o_health 2460,240 380x180 "Health\nCheck"         fill:tertiary
box o_alarm  2880,240 380x180 "On-call /\nAlarms"     fill:error
box o_back   2460,500 820x180 "Auto-Rollback\nif health fails" fill:error

# Primary flow
arrow r_build -> r_test     label:"compile"
arrow r_test -> r_pub       label:"pass"
arrow r_pub -> f_canary     label:"deploy"
arrow f_canary -> f_phase   label:"OK"
arrow f_phase -> f_full     label:"OK"
arrow f_full -> o_health    label:"observe"

# Risk paths
arrow o_health -> o_alarm    color:danger weight:primary label:"fail"
arrow o_alarm -> o_back      color:danger weight:primary label:"trigger"
arrow o_back -> f_canary     color:danger style:dashed label:"revert to prev"

# Bottom callouts
text k_risk 180,820 "Risk: bad release reaches >1% fleet before health check fires" size:detail color:neutral-strong
text k_cost 1320,820 "Cost: rollback saves field-tech visits (~€800/device)" size:detail color:neutral-strong
text k_own  2460,820 "Ownership: Ops owns gate; Release owns artifacts" size:detail color:neutral-strong
