# Slide Design Anti-Patterns

Six patterns the verify step (step 4) flags. Each one lists: detection, why-it-fails, and the fix.

## 1. claim-title (title is a topic, not a claim)

**Detection:** the title slot lacks a verb beyond copulas AND lacks a specific number with unit AND doesn't name an outcome / decision. See `slide-claim-test.md` for the full rubric.

**Why it fails:** Readers scanning a deck in skim-mode use titles as the summary. A topic-title is a placeholder, not a message — the reader has to read the whole slide to extract the point.

**Fix:** Rewrite the title using the body's claim. See rewrite patterns in `slide-claim-test.md`.

## 2. one-idea-violated (multiple points on one slide)

**Detection:**
- Body contains connectives suggesting a second thought: "and also", "furthermore", "additionally", "in addition", "on top of that".
- Multiple disjoint claim sentences in the same body slot.
- Two independent visuals (two charts, two diagrams) that don't compose.

**Why it fails:** Audiences process one idea at a time. A slide with two ideas gets half-remembered.

**Fix:** Split into two slides. If splitting creates excessive navigation, consider whether one of the ideas is actually the primary and the other is evidence — demote to a sub-point or move to the next slide.

## 3. bullet-dump (5+ peer-level bullets, no hierarchy)

**Detection:** 5 or more top-level bullets in the body slot, no visual nesting or grouping, no apparent synthesis.

**Why it fails:** A wall of bullets signals the author didn't decide what matters. Cognitive load spikes; rule-of-three violated; no visual hierarchy to guide the eye.

**Fix:** Three options:
- **Subordinate** — identify the one claim, make bullets sub-support of it. Shorten to 3.
- **Group** — introduce 2–3 categories, bullets nest under them (convert to two-column-cards or three-column).
- **Split** — if the bullets are genuinely 5+ ideas, that's one-idea-violated. Split across multiple slides.

## 4. audience-mismatch (jargon or abstraction level off)

**Detection:** per `audience-calibration.md` for the slide's audience:
- exec: any un-translated technical term; any content not expressible in money / time / risk.
- manager: deep implementation details without operational framing; pure vision without cost numbers.
- developer: pure business framing without technical grounding; hand-waving over mechanisms.
- peer: re-establishing shared context; business framing they don't need.

**Why it fails:** The slide is pitched at the wrong level. The audience either doesn't follow or feels condescended to.

**Fix:** Rewrite using the target audience's preferred framing. See `audience-calibration.md` — "what lands" section for each audience.

## 5. red-line-break (slide role doesn't match frame position)

**Detection:** the slide's `role` in `design_brief.json` is out of order for the chosen `frame`:
- SCQA: context → complication → recommendation → support/evidence → close.
- PSSR: complication → context → recommendation → evidence → close.
- Sparkline: alternating complication / recommendation pairs.
- Man-in-Hole: context → complication → complication → recommendation → evidence → close.

A slide's position in the deck should respect the frame's role order.

**Why it fails:** Breaks the narrative spine. The audience loses track of where they are in the argument.

**Fix:** Reorder slides, or re-role the slide, or re-frame the whole deck (if many slides break the order, the frame is wrong).

## 6. curse-of-knowledge (technical term without grounding for audience)

**Detection:** the slide uses a term that:
- is not defined in earlier slides,
- is not in the audience's assumed vocabulary per `audience-calibration.md`,
- is load-bearing for the slide's claim.

**Why it fails:** The audience doesn't share the background the author assumes. Elizabeth Newton's tapping experiment: the tapper hears a song; the listener hears random taps.

**Fix:** Three options:
- **Translate** to plain English (per the audience's tolerance).
- **Define inline** in 5–10 words, parenthetically.
- **Demote** — move the jargon to a supporting detail and lead with the value.

Cross-reference: `audience-calibration.md` for jargon tolerances per bucket.

## 7. redundancy-overload (slide text duplicates speech)

**Detection:** the slide body contains full sentences or paragraphs that restate exactly what a presenter would say aloud — the slide reads like a transcript, not a visual aid. Typical tells: complete paragraphs in body slots, bullet points that mirror the talk track verbatim, no visual evidence at all.

**Why it fails:** Text and spoken word compete for the same cognitive channel. When the audience reads the slide, they stop listening; when they listen, they stop reading. The result is split attention and reduced retention for both. A slide that duplicates speech adds zero information and doubles cognitive load (the Redundancy Effect).

**Fix:** Strip the body to the minimum needed to support the visual claim without speech. If the slide has no visual evidence, replace at least one text block with a chart, diagram, or image. The goal: someone walking past the screen understands the claim from the title + visual alone; the presenter's words add colour and nuance, not content.

## 8. truncated-y-axis (chart baseline above zero)

**Detection:** a bar or column chart whose Y-axis does not start at zero, causing the visual difference between bars to appear larger than the underlying data supports.

**Why it fails:** The eye reads bar height as magnitude. A 2% difference plotted from a baseline of 94% looks like a 50% swing. This misleads the audience — whether intentionally or not — and destroys credibility when spotted.

**Fix:** Start bar/column chart Y-axes at zero. If the range of variation is genuinely too small to see at zero (e.g., bond yields), switch to a line chart (which can use a non-zero baseline by convention) or annotate the axis break explicitly with a zigzag break symbol.

## 9. missing-baseline (number without context)

**Detection:** a statistic presented without a comparative reference point — no prior period, no benchmark, no denominator. Examples: "We processed 4.2M requests" (vs. what?), "Error rate is 0.3%" (is that good or bad?).

**Why it fails:** Isolated numbers don't communicate direction, scale, or significance. The audience either invents context (usually wrong) or disengages because they can't evaluate the claim.

**Fix:** Every key metric needs at least one anchor: a prior period ("vs. 2.1M last quarter"), a target ("vs. 5M goal"), a benchmark ("vs. 1.2% industry average"), or a denominator ("0.3% of 4.2M = 12,600 errors"). If no anchor exists, don't lead with the number — lead with the qualitative trend and use the number as support.

## 10. filler-word (diluting intensifiers in the so_what slot)

**Detection:** the `so_what` slot on a data/chart slide contains ≥2 meaningless intensifiers — "very", "really", "quite", "rather", "somewhat", "basically", "actually", "generally", "essentially", "literally", "truly", "incredibly", "extremely", "highly", "absolutely". These words add syllables without adding information.

**Why it fails:** A data slide's `so_what` is the one sentence the audience should remember. Every word must earn its place. Intensifiers do the opposite — they signal that the author reached for emphasis without locating a specific fact. "Revenue very significantly grew" conveys less precision than "Revenue grew 12%". Filler words also make the slide feel unconfident: if the data is strong enough, it doesn't need amplification.

**Fix:** Delete every filler and read the sentence again. It will almost always be stronger. If it isn't, the problem is with the underlying claim, not the missing intensifier — rewrite the claim with a specific metric and magnitude instead.

## 11. layout-monotony (same layout on 3+ consecutive slides)

**Detection:** three or more adjacent content slides in the deck use the same layout. Structural slides (title slides, chapter openers, agenda, end) are exempt — they don't rotate. The layout picker's `layout_history` signal prevents most monotony at plan time; this check catches edge cases.

**Why it fails:** Visual repetition conditions the audience to stop paying attention. When every slide looks the same, the brain pattern-matches to the previous slide and stops actively processing. A change of visual structure signals "new idea" — the same layout signal says "same type of content as before, keep your head down."

**Fix:** Three options:
- **Insert a chapter opener** between runs of the same layout — even one structural break resets the eye.
- **Switch to an alternate layout** for the same data type: `bar-chart` → `line-chart` or `stacked-bar` → `waterfall` when the data permits it.
- **Consolidate slides**: if three consecutive bar-chart slides all live under the same claim, that's one-idea-violated three times over — merge them into one richer chart slide.

## 12. image-slide-fit (image attractive but poor presentation material)

**Detection:** A slide contains an image asset that passes a generic "good photo" test but fails as a slide element. Three failure modes:
- **Crop failure**: the image's subject is partially obscured or cuts off awkwardly at the picture frame boundary (face cut at the chin, skyline horizon splits the frame dead-centre, landscape squeezed into a portrait slot).
- **Title dominance**: the image is so busy, bright, or large that the action title is hard to read at a glance. Applying the 3-second billboard test: if a viewer can't find and read the headline in 3 seconds, the image is competing.
- **Brand clash**: the image's dominant colours are strongly discordant with the brand palette (e.g., a warm-red hero photo in a cool-blue brand deck) — reducing perceived coherence even if the individual elements are each "good."

**Why it fails:** A photorealistic or illustrative image that crops badly, overwhelms the headline, or fights the brand palette undermines both the message and the brand. "Good image" ≠ "good slide image." The audience's attention is a zero-sum resource — a dominant visual that doesn't serve the claim is subtracting from comprehension, not adding to it.

**Fix:** Three options:
- **Swap the image** for one with better crop alignment to the picture frame, lower visual complexity in the headline zone, or dominant tones that complement rather than clash with the brand palette.
- **Apply an overlay** — a semi-transparent brand-coloured overlay on the picture frame reduces clash and creates sufficient contrast for the action title to read at WCAG AA (4.5:1 for body text, 3:1 for large text).
- **Reframe the layout** — if the slide's purpose is primarily textual, move from a full-bleed or text-over-image layout to a `text-picture` layout with a dedicated side panel; the image becomes supporting context rather than the canvas.

Cross-reference: `iteration-loop.md` defect #28 (image-slide-fit) and #29 (image-consistency).

## 14. fabricated-skip-reason (wrong or invented reason for skipping a step)

**Definition:** the orchestrator declares a step skipped with a fabricated or incorrect reason (e.g., "builder missing", "gate not available on this install"). The correct behavior on any crash is to surface the actual stderr.

**Example:**
> Incorrect: "Skipped verify-aspect because feinschliff-builder is not installed."
> Correct: surface the actual error from `feinschliff deck verify-aspect`; all verify-aspect subcommands ship in feinschliff core.

## 15. missing-artifact-clean-verdict (declaring done without the verify artifact on disk)

**Definition:** the orchestrator prints `Verdict: clean` to the user without first writing `out/verify_report.md` containing that verdict line. Declaring done without the artifact is not verification.

**Example:**
> Incorrect: print "Verdict: clean — deck looks great!" without writing `out/verify_report.md`.
> Correct: write `out/verify_report.md` with the `Verdict: clean` line in the header, then report done.

## 16. no-image-deck (image-capable deck with zero image-bearing slides)

**Definition:** a deck has zero slides with image-bearing layouts despite the brief being image-friendly. The default-on policy is "any slide that can carry an image SHOULD carry one." Only exceptions: pure data decks (`visual_style: data-dense`) or explicit `image_style: none` in deck_brief.yaml.

**Example:**
> Incorrect: all 10 slides use text-only layouts for a customer story deck.
> Correct: slides carrying a customer story, team intro, or hero metric use `content-with-visual`, `kpi-photo`, `text-picture`, or similar image-bearing layouts.

## 13. image-consistency (mixed visual styles across the deck)

**Detection:** The deck's image assets span two or more distinct visual style categories. Examples: slide 3 uses a photorealistic stock photo of people in an office; slide 7 uses a flat-vector illustration; slide 10 uses an abstract gradient background. The deck's `design_brief.json` has an `image_style` field — any image that contradicts the declared style is a violation.

**Why it fails:** Visual style is a non-verbal cue the audience reads without conscious effort. A consistent style signals "authored intentionally"; a mixed style signals "stitched together from separate sources." The inconsistency doesn't have to be extreme — one illustration among five photos is enough to register as an anomaly and break immersion. This is particularly acute in high-stakes decks (exec, client-facing, board materials) where polish is table-stakes.

**Fix:** Two options:
- **Standardise the style**: replace divergent images with assets matching the deck's `image_style`. For brands with an in-system illustration library (e.g., Catppuccin's icon set), prefer those over ad-hoc stock imagery.
- **Declare a hybrid style explicitly**: if the deck intentionally mixes photorealistic evidence (real screenshots, product photos) with diagrammatic or illustrative explanatory slides, document this in `design_brief.json` and ensure the two style categories are used consistently for distinct *purposes* (not randomly) — e.g., photorealistic for "real-world evidence" slides, illustration for "concept explanation" slides.
