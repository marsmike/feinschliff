# Audience Calibration

Four buckets. Step 1 infers the audience from brief cues. Step 2 adjusts slide claim wording. Step 4 checks audience-mismatch (jargon density, detail level).

## exec

**Who:** C-level, VPs, board members. Time-poor, outcomes-driven, pattern-matchers.

**What lands:**
- Impact in money, time, or risk terms (€, hrs, % risk reduced).
- One takeaway per slide, one per deck.
- Comparisons against alternatives (including doing nothing).
- Visual hierarchy: big number, minimal chrome.

**What loses them:**
- Any slide that doesn't answer "so what?" within 5 seconds.
- Architecture diagrams without a business frame.
- >3 bullet points anywhere.
- Jargon not translated (vector embedding, CRDT, BGP).
- Step-by-step walkthroughs.

**Jargon tolerance:** none. Every technical term gets translated or skipped.

**Preferred frame:** SCQA. Close second: Sparkline for change proposals.

**Slide count:** 5–10 content slides (+ cover + close). More than 10 signals scope creep; cut or appendix.

**Inference cues:** brief mentions "board", "exec", "leadership", "C-level", "for decision"; 5–15 min time budget; one-sentence brief with business framing.

## manager

**Who:** directors, team leads, engineering managers. Tactical, resource-aware, shipping-focused.

**What lands:**
- Team productivity framing (hrs saved, throughput, cycle time).
- Integration story — "how does this plug into what we have?"
- Cost: adoption effort, training, maintenance FTE.
- Risk framing — "what's the worst case?"

**What loses them:**
- Pure vision without operational detail.
- Abstract architecture without a "how does my team use this" beat.
- Comparisons only against academic alternatives.

**Jargon tolerance:** moderate. Common engineering terms are fine (CI/CD, observability, SLO); deep technical terms still need translation.

**Preferred frame:** PSSR. Second: SCQA for decision proposals.

**Slide count:** 10–20 content slides. Include appendix slides for detailed implementation; reference them from the main deck.

**Inference cues:** brief mentions "team", "pipeline", "adoption", "operations", "cost-of-ownership"; 15–30 min time budget.

## developer

**Who:** ICs, solution architects, platform engineers. Curious, skeptical, want the details.

**What lands:**
- Architecture and mechanism explained honestly.
- Tradeoffs named, including the downsides of your choice.
- Working code or demos > slides about code.
- Comparisons against alternatives with specific technical differentiators.

**What loses them:**
- Business impact stats without technical grounding.
- Pure vision or "disruption" language.
- Hand-waving over the hard parts.

**Jargon tolerance:** high. Assume they know the standard stack of their domain. Don't translate common terms; define novel ones.

**Preferred frame:** PSSR (for solutions) or Man-in-Hole (for incident stories). SCQA works but feels thin.

**Slide count:** 15–30 content slides. Detail and appendix depth is expected; slides can be denser.

**Inference cues:** brief mentions "architecture", "implementation", "performance", "design decision", "library"; 30–60 min time budget.

## peer

**Who:** other senior engineers or domain experts at your level. Already share the technical context.

**What lands:**
- The novel insight — what you learned that they don't already know.
- Tradeoffs against alternatives they've also considered.
- Code, data, or architecture at full fidelity.
- Questions and open problems.

**What loses them:**
- Re-establishing shared context you know they have.
- Business framing they don't need.

**Jargon tolerance:** very high. You can skip most definitions.

**Preferred frame:** SCQA (if pitching an answer) or Man-in-Hole (for war stories).

**Slide count:** open — structure follows the argument, not a target count. A 5-slide RFC and a 40-slide architecture deep-dive are both valid.

**Inference cues:** brief mentions "deep dive", "RFC", "design review", "architecture discussion", "peers"; open-ended time budget.

## Defaulting

If audience cannot be inferred, default to **manager** (broadest-compatible framing — works for exec if not too verbose, works for developer if not too abstract).

Always record the inferred audience + a one-sentence `audience_notes` explaining the inference in `design_brief.json`. User can override at step-1b.
