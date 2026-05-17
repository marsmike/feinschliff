---
extends: feinschliff
version: alpha
name: Feinschliff Dark
description: Inverted-canvas variant of Feinschliff — navy-900 surface with warm paper as body ink.
colors:
  accent: "#e4c27a"
  accent-hover: "#c9a24a"
  highlight: "#fbe6b3"
  black: "#0b1a33"
  ink: "#0b1a33"
  graphite: "#1f3056"
  steel: "#2d4770"
  silver: "#6e8bb6"
  fog: "#1f3056"
  paper: "#0b1a33"
  paper-2: "#0f2040"
  off-white: "#faf8f3"
  off-white-2: "#a9bcd6"
  rule-dark: "#1f3056"
  navy-800: "#070f1f"
  navy-700: "#0b1a33"
  navy-600: "#0f2040"
  navy-500: "#162a4a"
  navy-400: "#1e3258"
  navy-300: "#2d4770"
  navy-200: "#6e8bb6"
  navy-100: "#d6e0ee"
  white: "#faf8f3"
typography:
  inherit: feinschliff
---

## Overview

Feinschliff Dark inverts the canonical brand: navy-900 (`#0b1a33`) becomes
the canvas; warm paper (`#faf8f3`) becomes the body ink. The single gold
accent shifts from `#C9A24A` to `#e4c27a` (the lighter "highlight gold")
because the warmer pale gold reads more legibly on dark. The navy ramp
extends one step deeper (`navy-800` = `#070f1f`) for emphasized chapter
dividers.

## Colors

Accent (`#e4c27a`) is the on-dark gold — Feinschliff's `highlight` slot
promoted to primary. Pressed state falls back to canonical `#c9a24a`.
Body text reads as warm paper (`#faf8f3`); secondary text uses `navy-100`
(`#d6e0ee`) for the soft on-dark muted register.

## Typography

Inherits feinschliff's typography unchanged.
