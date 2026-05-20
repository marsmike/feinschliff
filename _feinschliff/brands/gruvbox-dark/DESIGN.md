---
extends: feinschliff
version: alpha
name: Gruvbox Dark
description: Retro groove warm palette — soft brown surfaces and muted earthtone accents. Upstream morhetz/gruvbox (MIT).
colors:
  accent: "#fabd2f"
  accent-hover: "#fe8019"
  highlight: "#d79921"
  black: "#282828"
  ink: "#282828"
  graphite: "#3c3836"
  steel: "#504945"
  silver: "#928374"
  fog: "#3c3836"
  paper: "#282828"
  paper-2: "#3c3836"
  off-white: "#ebdbb2"
  off-white-2: "#928374"
  rule-dark: "#504945"
  navy-800: "#1d2021"
  navy-700: "#282828"
  navy-600: "#3c3836"
  navy-500: "#504945"
  navy-400: "#665c54"
  navy-300: "#928374"
  navy-200: "#928374"
  navy-100: "#d5c4a1"
  white: "#fbf1c7"
typography:
  inherit: feinschliff
---

## Overview

Gruvbox is Pavel Pertsev's retro-groove palette (2013, MIT) — warm
brown surfaces and earthtone accents that read as the analog cousin to
the cool blue families like Nord and Solarized. The dark variant uses
`bg` (`#282828`) as the canvas; warm mustard (`#fabd2f`) is the
signature accent.

## Colors

Yellow (`#fabd2f`) is the canonical Gruvbox Dark accent — warm and
saturated against the cool brown canvas. Orange (`#fe8019`) takes the
active/hover state. Faded yellow (`#d79921`) is the muted variant for
secondary highlights.

The canvas stack is `bg0_h` (`#1d2021`, hardest), `bg` (`#282828`,
canvas), `bg1`–`bg4` graduating up through raised surfaces. Body text
reads as `fg` (`#ebdbb2`), the warm cream that's Gruvbox's defining
on-dark text color. Gray (`#928374`) supplies the muted/comment register.

## Typography

Inherits feinschliff's typography unchanged — Gruvbox is a palette only.
