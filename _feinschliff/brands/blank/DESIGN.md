---
version: "1.0"
name: Blank
colors:
  accent: "#1a1a1a"       # neutral near-black — child brand should override with its hue
  accent-hover: "#0a0a0a"
  highlight: "#555555"
  black: "#000000"
  ink: "#111111"          # body ink on paper, 19.34:1 on #FFFFFF
  chapter-slab: "#ffffff" # no inherited dark band — child opts in if it wants one
  graphite: "#444444"
  steel: "#7a7a7a"
  silver: "#b5b5b5"
  fog: "#e5e5e5"
  paper: "#ffffff"        # pure white canvas
  paper-2: "#f5f5f5"
  off-white: "#efefef"
  off-white-2: "#cfcfcf"
  rule-dark: "#1f1f1f"
  white: "#ffffff"
  severity-low: "#4a8753"
  severity-medium: "#c09030"
  severity-high: "#a04532"
  status-done: "#4a8753"
  status-current: "#c09030"
  status-next: "#6b6b6b"
---

# Blank — neutral white super-design

Pure grayscale token bundle with the same key surface as `feinschliff`,
intended as the `extends:` parent for any white-label / customer brand
pack that wants its own visual identity to dominate instead of inheriting
feinschliff's gold-on-navy register.

## Why this brand exists

`feinschliff` is the toolkit's eponymous brand and its tokens carry a
specific design point of view — gold accent, navy ramp, warm paper.
When a customer brand `extends: feinschliff`, every layout that touches
`accent`, `chapter-slab`, `ink`, or the navy-ramp tokens picks up those
hues unless explicitly overridden. For brands with their own strong
identity (corporate red, blue, etc.) the result is a render that mixes
the customer's accent with feinschliff's gold chapter slabs — visibly
off-brand.

`blank` solves this by collapsing every chromatic token to grayscale
while keeping the full key surface intact:

- `accent` / `accent-hover` → near-black
- `chapter-slab` → pure white (no inherited dark band)
- `ink` → near-black (#111111)
- `paper` / `paper-2` / `off-white*` → whites and light grays
- `navy-100..navy-800` ramp → `#E5E5E5..#2A2A2A` neutral ramp
- severity / status colors → kept semantic (a status-done check must
  still read as green; collapsing those to gray destroys affordance)
- `font-family.display` / `body` → generic Helvetica fallback stack
  (no Noto Sans pin), so the child brand's font is the one that wins

## Usage

```yaml
# brands/<your-brand>/DESIGN.md
---
extends: blank
---
```

Then in your brand's `tokens.json` override only the slots you care
about — typically `accent`, `accent-hover`, `font-family.display`,
maybe `chapter-slab` if you want a chapter band. Everything else stays
neutral and your identity dominates.

## Not a brand for end-deliverables

`blank` is intentionally non-opinionated. Building a deck directly
against `--brand blank` produces a perfectly readable but visually
flat render — there's no design point of view to lean on. Use it as
inheritance only.
