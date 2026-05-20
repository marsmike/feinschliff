# Brand-pack iteration techniques — index

Patterns and lessons accumulated while iterating brand packs against
their original PowerPoint sources. Each file is one recurring diagnostic
pattern with a "Fix shape" + "For feinschliff:compile" section so the
technique can be applied by the compile scaffolder when generating a new
brand pack from a source `.pptx` or HTML deck.

Patterns are intended to be brand-agnostic. When a future brand-pack
iteration discovers a counter-example or a new pattern not covered here,
add or update technique files in place. The compile skill mounts this
folder as orientation hints on every scaffold run.

## Generator-side (toolkit / DSL)
- [theme-effect-bleed](theme-effect-bleed.md) — strip `<p:style>` on every primitive emitter (shapes AND connectors).
- [native-shape-over-decomposition](native-shape-over-decomposition.md) — prefer one MSO_SHAPE over multi-primitive composition; expose `adj1:` for skew/angle handles.
- [visible-placeholder-default](visible-placeholder-default.md) — empty `picture path:""` should emit a visible placeholder, not silently skip.
- [style-bundle-overrides](style-bundle-overrides.md) — per-brand `tokens.json::style` merge over canonical `STYLE_BUNDLES`.
- [brand-defined-new-styles](brand-defined-new-styles.md) — `resolve_style` should accept brand-defined NEW style names (not just overrides) so brands can vary one logical token across chrome regions.
- [layer2-unrolling](layer2-unrolling.md) — tabular content (gantt, table, pie-trio) needs compose-time array expansion, not hardcoded N rows.

## Brand-pack patterns
- [cover-split-pattern](cover-split-pattern.md) — default cover layouts to half-bleed split, not full-bleed.
- [source-overlay-pack](source-overlay-pack.md) — two-tier brand pack: production form (slot-based, ~5-10% diff floor) coexists with verification form (full-bleed source overlay, ~1-3%). Resolves the tension between authorability and 99%+ fidelity proof.

## Verifier-side
- [picture-slot-mask-verifier](picture-slot-mask-verifier.md) — verifier MUST mask picture slots, else photo-content drift swamps structural signal.
- [source-asset-extraction](source-asset-extraction.md) — crop source slides at each picture-slot bbox; works for photos AND chart/diagram regions.
- [structural-metric-coverage-bias](structural-metric-coverage-bias.md) — `struct_diff_ratio` is unreliable when picture coverage is high; cross-check with SSIM + absolute pixel count.
- [stroke-width-metric-trap](stroke-width-metric-trap.md) — thinning a stroke can improve the metric while making the render visually worse; positional drift hides as stroke-width "wins".
- [plateau-categories](plateau-categories.md) — once a layout plateaus, classify the residual drift: position / geometry / font-metric. Only categories (a) and (b) respond to iteration.

## How these get back into `feinschliff:compile`
Each technique's "For feinschliff:compile" section names a concrete
scaffolder change. The compile skill should read this index on every
`compile --from-pptx` run; the techniques become orientation hints for
the scaffolder, the same way autoresearch's `techniques/` are hints for
future mutators.

When adding a new technique here: keep it short, lead with the failure
pattern, name the fix shape concretely, finish with the compile-skill
implication. If you can't write the compile implication, the technique
isn't ready to ship.
