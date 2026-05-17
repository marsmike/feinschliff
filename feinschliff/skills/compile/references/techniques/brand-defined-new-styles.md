# Brand-defined new styles (not just overrides)

## Pattern
Per-brand `tokens.json::style` can override canonical `STYLE_BUNDLES`
keys (see `style-bundle-overrides.md`), but the original `resolve_style`
only ACCEPTED override keys that matched an existing canonical bundle.
Brands couldn't define entirely NEW style names.

This bit us when a corporate brand's wordmark needed to be ~60px on
covers but ~16px in the footer. A single canonical `wordmark` style can't carry
both. We needed a new `wordmark-footer` style — which the resolver
rejected with `KeyError: "unknown style 'wordmark-footer'"`.

## Trigger
Brand uses the same logical token (wordmark, eyebrow, KPI value) at
visibly different sizes/weights in different chrome regions. Cover vs.
footer is the canonical case. Hero KPI vs. dashboard KPI is another.

## Fix shape
Extend `resolve_style` to accept brand-defined styles that aren't in
the canonical `STYLE_BUNDLES`, provided the brand's `style` entry
carries the four required keys (`font`, `size`, `weight`, `color`)
itself. Partial overrides on existing canonical names continue to work
as before.

```python
# lib/dsl/tokens.py::resolve_style
bundle = STYLE_BUNDLES.get(name)
override = self.raw.get("style", {}).get(name) or {}
if bundle is None:
    required = {"font", "size", "weight", "color"}
    missing = required - override.keys()
    if missing:
        raise KeyError(f"unknown style '{name}' (brand override missing {sorted(missing)})")
    bundle = override     # full-bundle from brand alone
bundle = {**bundle, **override}
```

## For `feinschliff:compile`
When scaffolding a brand pack and detecting size deltas in the same
logical token across regions: emit a NEW brand-defined style entry
rather than picking the larger size globally. The footer can stay at
the canonical size while the cover gets a `wordmark-cover` (or
`wordmark-large`) style.

## Evidence
- Corporate brand needed 60px wordmark on covers (source measurement)
  but the footer compound used the same `style:wordmark` at a small
  fixed-width slot (122px). Bumping wordmark size token to 60px caused all 16
  layouts with footers to fail rendering (text overflowed the slot).
- Added `wordmark-footer` brand-defined style at size=footer (16px),
  bold weight, display font. Updated footer compound to use it. All
  layouts render correctly; cover wordmark remains at 60px.
