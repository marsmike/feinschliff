# Narrative Frames

Eight frames that structure a deck's spine. Step 1 infers the frame from the brief / existing content. Step 2 uses it to order slides and assign roles. Step 4 checks red-line breaks against it.

The first four (SCQA, PSSR, Sparkline, Man-in-a-Hole) are the original consulting-arc set. The next three (PPF, PSE, KEA) cover trajectory, pitch, and audience-emotion framings that the original four don't address cleanly. ABT is a pre-flight check for any frame — if you can't write a clean ABT sentence, the argument isn't ready to deck.

## SCQA (Minto Pyramid)

**Use when:** the audience needs an answer fast — exec updates, decision proposals, technical recommendations to non-technical stakeholders.

**Don't use when:** the deck is exploratory, a discovery journey, or the conclusion depends on the walk-through.

**Slide roles in order:**
1. `hook` — optional, often skipped for SCQA
2. `context` — Situation (stable baseline)
3. `complication` — Complication (what changed / broke)
4. `recommendation` — Answer (your action)
5. `support` / `evidence` — 2–3 points backing the recommendation
6. `close`

**Inference cues:** brief contains "recommend", "propose", "decision"; exec audience; short time budget (≤15 min).

## PSSR (Problem / Search / Solution / Result)

**Use when:** presenting a project, evaluation outcome, or status update where the journey matters.

**Don't use when:** the audience is too senior to care about the journey (use SCQA instead) or there's no meaningful search phase (use Sparkline).

**Slide roles in order:**
1. `hook`
2. `complication` — the Problem (pain, quantified)
3. `context` — the Search (approaches tried, tradeoffs)
4. `recommendation` — the Solution (what won)
5. `evidence` — the Result (quantified impact)
6. `close`

**Inference cues:** brief contains "we evaluated", "we tried", "status update", "post-mortem", "retrospective".

## Sparkline (Duarte — What Is / What Could Be)

**Use when:** vision pitch, change proposal, call to action. Oscillates current painful reality with desirable future.

**Don't use when:** no meaningful gap between present and future (use SCQA), or audience is tactical/operational (use PSSR).

**Slide roles in order (each pair oscillates):**
1. `hook`
2. `complication` — what is (pain)
3. `recommendation` — what could be (possibility)
4. `complication` — next pain beat
5. `recommendation` — next possibility beat
6. (repeat as needed)
7. `close` — "new bliss"

**Inference cues:** brief contains "vision", "imagine", "transform", "future of", "where we're going".

## Man-in-a-Hole (Vonnegut)

**Use when:** story of an incident, migration, crisis-and-recovery. Simple, emotionally engaging arc.

**Don't use when:** no real fall happened (use SCQA or PSSR).

**Slide roles in order:**
1. `hook`
2. `context` — Equilibrium (what was normal)
3. `complication` — the Fall (what broke)
4. `complication` — the Pit (bottom, quantified impact)
5. `recommendation` — the Climb (how it was resolved)
6. `evidence` — Resolution (new equilibrium, better than before)
7. `close`

**Inference cues:** brief contains "incident", "outage", "migration", "post-mortem", "then X happened", "we ended up".

## PPF (Past, Present, Future)

**Use when:** the deck argues an evolution, a trajectory, or a historical-to-prospective arc. Common for vision decks that need to ground the future in a credible past, retrospectives that lead to a forward bet, or "where we've been, where we are, where we're going" company-update decks.

**Don't use when:** the past is irrelevant or the audience already knows it (use SCQA or ABT and cut the lead-in). Also avoid when the present is in crisis — the chronological structure dilutes urgency (use Man-in-Hole or PSSR).

**Slide roles in order:**
1. `hook` — optional, often a "remember when…" anchor
2. `context` — Past (baseline / origin / what we started with)
3. `context` — Present (where we are now, with evidence)
4. `complication` — the inflection (what's forcing the next move)
5. `recommendation` — Future (the bet, the destination)
6. `evidence` — proof points the trajectory holds
7. `close`

**Inference cues:** brief contains "evolution", "trajectory", "journey", "year-in-review", "looking ahead", "X years ago … today … next", "how we got here", "growth story".

**Example arc:** *Past:* "5 years ago we shipped on quarterly cycles." *Present:* "Today we ship daily and our defect rate is 1/10th of the industry." *Inflection:* "But our deploy gate is now the bottleneck — every team waits on the same pipeline." *Future:* "Adopt per-team deploy gates by Q3."

## PSE (Problem, Solution, Evidence)

**Use when:** pitching a solution to an audience that needs convincing to buy / adopt / fund. Common in sales decks, board asks for budget, vendor pitches, and any "convince them to choose us" framing where the audience starts skeptical.

**Don't use when:** the audience is already bought in (use SCQA — skip the sell). Also avoid when there's no clean single solution being pitched (use PSSR for journeys with multiple approaches evaluated).

**Slide roles in order:**
1. `hook` — typically a customer pain quote or shocking stat
2. `complication` — Problem (the pain, quantified and named — make the audience feel it)
3. `recommendation` — Solution (the offering, framed as the answer to the named pain)
4. `evidence` — Evidence (proof points: case studies, metrics, demos, third-party validation)
5. `evidence` — second evidence beat (a different angle: testimonial vs. benchmark vs. ROI math)
6. `close` — clear ask (try / buy / decide)

**Inference cues:** brief contains "pitch", "sales deck", "convince", "win", "RFP", "investor", "buyer", "prospect"; audience is external; explicit ask attached.

**Example arc:** *Problem:* "Enterprise sales cycles average 9 months; 60% of pipeline never closes." *Solution:* "Atlas Sales OS shortens cycles to 4 months by automating the discovery phase." *Evidence:* "Three Fortune-500 customers cut cycles 55% in the first quarter."

## KEA (Knowledge, Emotion, Action)

**Use when:** the audience must FEEL the urgency before they will act — change-management decks, executive buy-in, cultural shifts, anything where logical arguments alone won't move the room. The triplet maps to the cognitive (what they know), affective (what they feel), and behavioral (what they do) dimensions of audience design.

**Don't use when:** the audience is analytical / decision-fatigued and just wants the answer (use SCQA — emotion will feel manipulative). Also avoid for tactical operational updates where the team is already aligned (use PSSR).

**Slide roles in order:**
1. `hook` — emotional opener (story, image, contrast)
2. `context` — Knowledge (the facts: what's true, what's measured, the baseline)
3. `complication` — Emotion (the stakes: what's at risk if we don't act, who pays the cost — make it personal to the audience)
4. `recommendation` — Action (the specific commitment being asked for, framed so the audience can say yes)
5. `evidence` — what makes the action achievable (resources, support, early wins)
6. `close` — the ask, restated as a moment of decision

**Inference cues:** brief contains "change management", "transformation", "buy-in", "rally", "urgency", "culture", "town hall", "all-hands"; audience is being asked for behavioral commitment, not just intellectual agreement.

**Example arc:** *Knowledge:* "Our deploy gate has been stable for 3 years." *Emotion:* "Every engineer now spends 8 hours/week waiting — that's the equivalent of 12 FTEs we're burning on coordination overhead." *Action:* "Approve the per-team gate migration this quarter."

## ABT (And, But, Therefore)

**Use when:** the deck is short (1–5 slides), the context is an elevator pitch or exec summary, or you need to distil a complex argument into a single narrative sentence before building the full deck.

**Don't use when:** the audience needs a detailed walk-through (use SCQA or PSSR), or the emotional arc matters more than the logical argument (use Sparkline).

**Structure (three beats):**
1. `context` — "We have [capability/resource/opportunity] AND [second supporting fact]…"
2. `complication` — "…BUT [obstacle/constraint/tension]…"
3. `recommendation` — "…THEREFORE [specific action required]."

**Slide roles in order:**
1. `context` — the AND beat (what's true, what we have)
2. `complication` — the BUT beat (what blocks us)
3. `recommendation` — the THEREFORE beat (the call to action)
4. `evidence` — optional support for the THEREFORE
5. `close`

**Primary value:** forces the author to locate the single tension in the argument before writing any slides. If you can't write a clean ABT sentence, the argument isn't ready to deck. Use ABT as a pre-flight check for any frame.

**Inference cues:** brief is one or two sentences with a clear blocker and a single ask; "exec summary", "one-pager", "elevator pitch", "board slide".

## Picking a frame (when inference is ambiguous)

- If the content has a quantified recommendation → **SCQA**.
- If it has a journey with alternatives evaluated → **PSSR**.
- If it's selling a future state → **Sparkline**.
- If something broke and got fixed → **Man-in-Hole**.
- If the argument is a trajectory (past → present → future) → **PPF**.
- If the deck is a pitch and the audience needs convincing → **PSE**.
- If the audience must FEEL the urgency before they will act → **KEA**.
- If the brief fits in a single sentence (one-pager / exec summary) → **ABT**.
- Still ambiguous → default to **SCQA** (safest bet for technical audiences; always passable for exec).

The planner picks **one** frame per deck based on these inference cues — there is no separate frame registry. Each frame is a planner heuristic that orders slide roles; the brief still wins when it conflicts with the cues.

Always write `frame_rationale` in `design_brief.json` naming the runner-up frame and why it was rejected. The runner-up is a hint to the user at the step-1b gate if they want to override.

## Structural integrity — horizontal and vertical logic

A frame gives the deck its shape. Horizontal and vertical logic tests that the shape holds.

**Horizontal logic (the title-only read):** Read only the action titles in sequence, ignoring all body content. The titles alone should tell a complete, logically coherent story — no gaps, no redundancy, no contradictions. If a title doesn't follow from the previous one, either a slide is missing or a title is wrong. This is the "ghost deck" test: write and validate all action titles before adding any visuals.

**MECE check:** Titles at the same structural level should be mutually exclusive (no two slides make the same claim) and collectively exhaustive (the set of titles covers all the ground the argument needs). If two slides say the same thing from different angles, merge or cut one. If there's a logical gap between two titles, insert a slide.

**Vertical logic (claim ↔ body):** The body of each slide must directly prove its action title. Every sentence, data point, and visual should answer the question "does this support the claim in the title?" Anything that doesn't — move to the appendix. The body never introduces a new claim; new claims get their own slide.

**Storyboarding discipline:** Before opening PowerPoint or running the build pipeline, write the ghost deck: a flat list of proposed action titles in frame order. Read them aloud. If the story doesn't hold, fix the titles. Titles are the architecture; visuals are the interior — never design the interior before the architecture is settled.
