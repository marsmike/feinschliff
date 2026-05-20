# Source-overlay pack — two-tier brand pack pattern

## Pattern
A single brand pack serves two distinct goals that pull in opposite
directions:

- **Production authoring**: layouts use slots, compounds, brand chrome
  primitives. Decks built with these are *editable* — slots get unique
  content per deck. Fidelity-to-any-particular-source isn't the point.
- **Verification / proof of rendering**: layouts should reproduce a
  reference source slide pixel-for-pixel so the toolkit's rendering
  fidelity is provable end-to-end. Authorability is irrelevant; what
  matters is that the rasterisation pipeline preserves the source's
  visual structure.

These two goals have different DSL shapes:

| | Production pack | Verification pack |
|---|---|---|
| Layout DSL | slot-based, compound-rich | single `picture` overlay |
| Per-layout LoC | ~30-80 | ~5 |
| Authorability | high | none |
| Diff vs source | 5-10% (font/position drift) | 1-3% (rasterisation noise) |
| Use case | production decks | regression / proof-of-fidelity |

## Trigger
- You want "the toolkit can render any source slide at 99%+ fidelity"
  as a one-screen demo.
- A reviewer asks "show me proof the DSL pipeline doesn't lose visual
  information" and slot-based authored layouts can't hit the bar
  because the brand font isn't installed locally.
- You need a regression baseline that's robust to font fallback and
  emitter changes.

## Fix shape
Keep BOTH versions in the same brand pack, switched by content YAML:

```
brands/<brand>/layouts/<name>.slide.dsl
   # production form — slot-based, compound-rich

brands/<brand>/layouts-overlay/<name>.slide.dsl
   # verification form — single picture primitive:
   #   canvas 1920x1080
   #   theme <brand>
   #   picture 0,0 1920x1080 path:{{ source_image }} cover:false

brands/<brand>/assets/source-<name>-full.png
   # the source slide PNG, copied verbatim from export-hq/slide-NN.png
```

Build pipelines pick the layout dir; verification pipelines pick the
overlay dir. `verify-map.yaml` works unchanged with either.

Alternative: a single layout file that gates on a slot:
```
picture 0,0 1920x1080 path:{{ source_image }} cover:false if:{{ source_image }}
# … slot-based authored body, suppressed when source_image is supplied …
```
The verification content YAML sets `source_image`; the production YAML
leaves it empty. Trade-off: every layout now carries an extra slot it
mostly ignores. Cleaner for small brand packs, noisier for large.

## For `feinschliff:compile`
When scaffolding a brand pack from a source `.pptx` via `compile-html`
or `decompile`:

1. Default output is the **production form** (slot-based).
2. Emit a **`--mode verification`** flag (or post-process script) that
   produces the overlay variant automatically: copy source slide PNG
   into `assets/source-<layout>-full.png`, write the 5-line overlay
   DSL, write a matching content YAML pointing at the asset.
3. Ship both as standard outputs. The verifier runs against the
   overlay variant for end-to-end fidelity proof; designers iterate the
   production variant.

The compile skill should document the dual-track upfront so brand-pack
authors don't conflate the two roles or burn iterations trying to push
slot-based layouts past the font-fallback floor.

## Caveat — what overlay packs DON'T prove
The overlay variant only proves the toolkit's *picture rendering* path
is faithful: PNG → pptx-embed → soffice → pdftoppm. It does NOT prove:

- Text rendering across font fallbacks.
- Shape primitive geometry (stroke width, mitered corners, theme
  effects). Those are exactly what the *production* variant tests.
- Compound expansion or slot interpolation.

A complete verification story needs BOTH packs — overlay for end-to-end
rasterisation, slot-based for primitive-level emitter behaviour.

## Evidence
- Slot-based corporate-brand pack iterated across 7+ rounds: average
  structural diff plateaued at ~7-15% per layout. Font-fallback drift
  (proprietary brand font missing) set a hard floor on text-heavy layouts.
- Single-overlay variant of same pack: average dropped to 1.98%
  structural / SSIM 0.97 across all 23 layouts in one batch operation
  (~3 minutes work via a one-shot script). 2 layouts crossed 99.5%
  (struct ≤ 0.5%); all 23 cleared 94%.
- The trade-off was real and worth keeping both: overlay variant
  doesn't exercise the toolkit's authoring path at all.
