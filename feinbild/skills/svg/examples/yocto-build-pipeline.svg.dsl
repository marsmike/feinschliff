# diagram_brief: audience=yocto-build-engineers complexity=deep type=yocto-build-pipeline
# teaches: meta-layers stack composition (stacked_bar), BitBake hub,
#          parallel artifact outputs, sign + publish callout, SBOM brace annotation
# canvas: 6880x2880 — a large full-bleed viewport (or use a virtual:WxH directive)
#
# Note: the SVG DSL is strictly line-based; each primitive must be on a
# single line. No backslash line-continuation.

canvas 6880x2880

rect bg_left  100,80 1700x2720 surface-2
rect bg_core  1820,80 2240x2720 paper
rect bg_right 4080,80 2700x2720 surface-2

text title 200,180 title "Yocto Image Build Pipeline"
text sub_l 200,240 subtitle "Meta-layers (inputs)"
text sub_c 1920,240 subtitle "BitBake + Tooling"
text sub_r 4180,240 subtitle "Outputs"

text lbl_layers 200,360 body "Layer stack"

stacked_bar layers 200,420 1500x1900 orient:vertical segments:8,primary;6,secondary;5,tertiary;4,warning;3,accent;6,neutral-soft;4,neutral

text lyr1 1740,500 body "meta-product (your code)"
text lyr2 1740,720 body "meta-openembedded"
text lyr3 1740,930 body "meta-vendor BSP (NXP / TI)"
text lyr4 1740,1130 body "meta-security (TPM / dm-crypt)"
text lyr5 1740,1320 body "meta-network (DPDK)"
text lyr6 1740,1620 body "meta-poky (base distro)"
text lyr7 1740,2080 body "poky core (BitBake recipes)"

brace b_split from:1700,2320 to:1700,800 side:right depth:120 "third-party"
brace b_own   from:1700,800 to:1700,420 side:right depth:120 "product-owned"

label_box bb 1920,420 2040x440 "BitBake" variant:title fill:primary stroke:ink
text bb_sub 1940,900 body "task scheduler · sstate cache · DEPENDS graph"

label_box dl  1920,1000 950x340  "Downloads (SRC_URI)" variant:body fill:surface
label_box ss  2920,1000 1040x340 "sstate cache"        variant:body fill:tertiary

label_box sdk 1920,1380 950x340  "SDK (eSDK)"          variant:body fill:secondary
label_box qa  2920,1380 1040x340 "QA / pkgsanity"      variant:body fill:secondary

label_box sign 1920,1760 950x340  "Image Signing"      variant:body fill:tertiary
label_box pub  2920,1760 1040x340 "Publish (BSP server)" variant:body fill:tertiary

polyline flow_in  1720,1500 1820,1500 stroke:ink stroke-width:6
polyline flow_out 3960,1500 4060,1500 stroke:ink stroke-width:6

path sign_to_pub "M 2870,1930 L 2920,1930" stroke:neutral-strong stroke-width:4 dashed

label_box out_img  4180,420 2540x340 "Product image (FIT / SWUpdate bundle)" variant:body fill:primary
label_box out_rfs  4180,800 2540x340 "rootfs + kernel + DTB (signed)"        variant:body fill:secondary
label_box out_sdk  4180,1180 2540x340 "SDK (eSDK + toolchain)"               variant:body fill:secondary
label_box out_pkg  4180,1560 2540x340 "Package feed (.ipk / .deb)"           variant:body fill:tertiary
label_box out_sbom 4180,1940 2540x340 "SBOM (SPDX + CVE report)"             variant:body fill:tertiary
label_box out_test 4180,2320 2540x340 "Test report (oeqa)"                   variant:body fill:tertiary

brace b_release from:4180,420 to:4180,2660 side:left depth:120 "release artifacts"

callout sbom_note anchor:4180,2080 at:5400,2700 1280x80 "Regulators want SPDX 2.3+ + CVE list" fill:warning stroke:neutral-strong

swatch_grid leg 200,2620 cols:4 swatches:primary,product-code;secondary,third-party-BSP;tertiary,build-tooling;warning,compliance
