---
extends: feinschliff
version: alpha
name: Nord
description: Arctic, north-bluish color palette designed for clear and minimal interfaces. Upstream nordtheme/nord (MIT).
colors:
  accent: "#88c0d0"
  accent-hover: "#81a1c1"
  highlight: "#5e81ac"
  black: "#2e3440"
  ink: "#2e3440"
  graphite: "#3b4252"
  steel: "#4c566a"
  silver: "#4c566a"
  fog: "#3b4252"
  paper: "#2e3440"
  paper-2: "#3b4252"
  off-white: "#eceff4"
  off-white-2: "#d8dee9"
  rule-dark: "#3b4252"
  navy-800: "#2e3440"
  navy-700: "#3b4252"
  navy-600: "#434c5e"
  navy-500: "#4c566a"
  navy-400: "#4c566a"
  navy-300: "#d8dee9"
  navy-200: "#4c566a"
  navy-100: "#d8dee9"
  white: "#eceff4"
typography:
  inherit: feinschliff
---

## Overview

Nord is Arctic Ice Studio's 16-color arctic palette (2016, MIT) — designed
for clear, minimal, north-bluish interfaces. The four-tone Polar Night
ramp (`nord0`–`nord3`) supplies the dark canvas; Snow Storm
(`nord4`–`nord6`) holds the light surfaces and on-dark text. Frost
(`nord7`–`nord10`) is the cool blue accent family; Aurora (`nord11`–`nord15`)
is the semantic-color family (red, orange, yellow, green, purple).

## Colors

Frost cyan (`#88c0d0`, `nord8`) is the canonical Nord primary accent —
clean and unsaturated against the Polar Night canvas. Frost steel-blue
(`#81a1c1`, `nord9`) takes the active state. Frost dark (`#5e81ac`,
`nord10`) plays the secondary-accent role.

The Polar Night canvas (`nord0` `#2e3440`) is the page surface;
`nord1`–`nord3` graduate up through raised-card surfaces and hairlines.
Body text reads as Snow Storm `nord4` (`#d8dee9`).

## Typography

Inherits feinschliff's typography unchanged — Nord is a palette only.
