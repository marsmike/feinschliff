---
extends: feinschliff
version: alpha
name: Solarized Dark
description: Ethan Schoonover's classic precision-engineered palette — warm yellows on cool teal-black. Upstream ethanschoonover.com/solarized (MIT).
colors:
  accent: "#b58900"
  accent-hover: "#cb4b16"
  highlight: "#2aa198"
  black: "#002b36"
  ink: "#002b36"
  graphite: "#073642"
  steel: "#586e75"
  silver: "#839496"
  fog: "#eee8d5"
  paper: "#fdf6e3"
  paper-2: "#eee8d5"
  off-white: "#eee8d5"
  off-white-2: "#93a1a1"
  rule-dark: "#586e75"
  navy-800: "#002b36"
  navy-700: "#073642"
  navy-600: "#586e75"
  navy-500: "#657b83"
  navy-400: "#839496"
  navy-300: "#93a1a1"
  navy-200: "#839496"
  navy-100: "#eee8d5"
  white: "#fdf6e3"
typography:
  inherit: feinschliff
---

## Overview

Solarized Dark is Ethan Schoonover's precision-engineered 16-color palette
(2011, MIT). Designed around CIELAB color space for uniform perceptual
luminance — text remains readable across the warm/cool axis without
saturation shifts. The dark variant uses base03 (`#002b36`) as the canvas;
yellow (`#b58900`) is the warm signature accent.

## Colors

Yellow (`#b58900`) is the canonical Solarized accent — warm and unambiguous
against the cool teal-black surface. Orange (`#cb4b16`) provides the active
state. Cyan (`#2aa198`) plays the secondary-accent role.

The 8 base tones (`base03`/`02`/`01`/`00`/`0`/`1`/`2`/`3`) form a perceptually
uniform luminance ramp — feinschliff's `navy-800` through `navy-100` slots
map onto this ramp. Body text uses `base1` (`#93a1a1`) on dark; emphasized
display text uses `base2` (`#eee8d5`).

## Typography

Inherits feinschliff's typography unchanged — Solarized is a palette only.
