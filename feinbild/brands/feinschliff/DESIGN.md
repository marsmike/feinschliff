---
version: alpha
name: Feinschliff
colors:
  accent: "#c9a24a"  # Primary gold — the only accent. Use sparingly.
  accent-hover: "#8a6f2e"  # Pressed / printed gold.
  highlight: "#e4c27a"  # Hover / on-dark accent gold.
  black: "#0b1a33"  # Navy-900 — deepest.
  ink: "#0b1a33"  # Body ink on light = navy-900.
  chapter-slab: "#0b1a33"
  graphite: "#2d3a52"  # Secondary text.
  steel: "#5a6478"  # Tertiary / muted labels.
  silver: "#a9bcd6"  # Muted text on dark / soft labels.
  fog: "#d6d1c2"  # Warm hairlines on light.
  paper: "#faf8f3"  # Warm paper — page on light.
  paper-2: "#f4f1e8"  # Raised surface on light.
  off-white: "#f0ece4"  # Body text on dark.
  off-white-2: "#d9d3c5"  # Muted text on dark.
  rule-dark: "#1f3056"  # Hairlines on dark.
  navy-800: "#0f2040"  # Surface on dark.
  navy-700: "#162a4a"  # Raised surface on dark.
  navy-600: "#1e3258"  # Gem mid-facet.
  navy-500: "#2d4770"  # Gem upper-facet.
  navy-400: "#3a5b8c"  # Gem highlight.
  navy-300: "#6e8bb6"  # Lifted on dark.
  navy-200: "#a9bcd6"  # Muted on dark.
  navy-100: "#d6e0ee"  # Soft divider on light.
  white: "#ffffff"
  severity-low: "#3f8553"
  severity-medium: "#c9a24a"  # Risk severity / status: medium — reuses accent gold.
  severity-high: "#a8442a"
  status-done: "#3f8553"  # Status: done — same green as severity-low.
  status-current: "#c9a24a"  # Status: in progress — accent gold.
  status-next: "#5a6478"  # Status: not yet started — steel grey.
---

## Overview

Feinschliff. — eponymous default brand pack. Navy ramp + warm paper + single gold accent. Bauhaus register. Noto Sans. MIT.

## Colors

- `chapter-slab` (`#0b1a33`) — Deepest contrast band for chapter dividers. In light brands = ink; in dark brands override to the brand's canvas-deeper neutral.
- `severity-low` (`#3f8553`) — Risk severity / status: low — restful green, harmonized with the navy ramp.
- `severity-high` (`#a8442a`) — Risk severity / status: high — desaturated rust, not pure red.

## Typography

Defined in tokens.json (`font-family`, `font-weight`, `font-size`).
Inherits from this brand's tokens for now; future revisions may move
typography tokens into DESIGN.md frontmatter.
