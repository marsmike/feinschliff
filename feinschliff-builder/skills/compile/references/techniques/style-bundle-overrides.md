# Per-brand `style` overrides in `tokens.json`

## Pattern
The toolkit ships canonical `STYLE_BUNDLES` (title, body, eyebrow,
wordmark, pgmeta, footer, kpi-value, kpi-key, etc.) with default font
weights, sizes, transforms, letter-spacings. Most brands want to override
SOME keys per token without re-authoring the whole bundle.

## Fix shape
`lib/dsl/tokens.py::resolve_style` merges a per-brand `style` map from
`tokens.json` on top of the canonical `STYLE_BUNDLES`. Brand can override
any subset of:
- `font`
- `size`
- `weight`
- `color`
- `transform` (set to `null` to clear a canonical transform)
- `letter_spacing`
- `line_height`
- `opacity`

Brand `tokens.json::style.title` → merged over `STYLE_BUNDLES["title"]`.
Three unit tests in `tests/feinschliff/test_dsl_tokens.py` (repo root) lock the behavior.

## For `feinschliff:compile`
When scaffolding a new brand pack, look at the source's typography choices
slide-by-slide. Common overrides observed in prior iterations:
- `title` → weight `light` + tight letter-spacing (canonical is heavier).
- `eyebrow` → cleared transform (no uppercase), body font, graphite color.
- `wordmark` → bold, larger size.
- `pgmeta` → cleared transform, body font, opacity 1.0.
- `kpi-value` → weight regular (canonical heavier).
- `kpi-key` → body font + 5% letter-spacing.

These are NOT layout-level overrides — they're brand-level, written once
in `tokens.json::style`, applied across every layout that uses the
bundle. Compile should detect typography deltas from the source thumbnail
analysis and emit `tokens.json::style` patches automatically.

## Evidence
- Wordmark with canonical `pgmeta` style: tiny, wrong weight.
- After `tokens.json::style.wordmark = {weight: bold, size: wordmark}`:
  matches source.
- Pattern observed across ~7 tokens per typical corporate brand. Without
  the override mechanism, hand-authored variants would spread across
  every layout (N layouts × M tokens = N·M places).
