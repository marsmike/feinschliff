# Concept visualization — beats that teach, not restate

Run this pass FIRST over every explanation-heavy stretch, before the
[template-picker.md](template-picker.md) table fills in the connectives.
The picker reads the surface speech act (a number, a list, a quote); this
doc catches the moments where the speaker is TEACHING — the moments a text
card under-serves. Whether a moment deserves a beat at all stays with the
placement test in [editing-doctrine.md](editing-doctrine.md) §2; mechanics
and hard rules live in [SKILL.md](../SKILL.md).

## 1. The teach gate

Before any beat lands on an explanation, force a one-sentence answer to:

> **Name the thing a muted viewer understands after this visual that the
> audio could not have taught them.**

- Answer reads "they can see the line he just said" → a **text card**: the
  legitimate fallback for punchlines; on a teaching moment it adds volume,
  not understanding.
- Answer names something newly VISIBLE — a mechanism in motion, the inside
  of something, both ends of a change, a count too large for the ear — →
  a **concept visual**. Author that instead.

The meaning gate (doctrine §1) checks that a visual is honest; the teach
gate checks that it instructs. An explanation beat must pass both.

## 2. Detecting explanation beats

Walk `words.json` and flag every stretch where the speaker is trying to
install a model in the viewer's head, not just state a position. Tells:

| Speaker is… | Listen for | Visual? |
|---|---|---|
| narrating a process / causal chain | "step one", "then it", "once that finishes", "which means", "so the …" | yes |
| describing parts of a whole | "consists of", "three pieces", "inside it sits" | yes |
| contrasting two approaches | "rather than", "compared to", "we used to" | yes |
| stating change / proof | "went from", "doubled", "dropped to" | yes |
| counting within a set | "X of the Y", "out of twelve" | yes |
| reaching for a metaphor | "it's like a", "picture a", "essentially a" | yes |
| asserting an opinion / feeling | "I think", "frankly", "my take" | **no beat** (doctrine §2) |

Quotability is the trap here: a teaching line that sounds good pulls the
hand toward `quote_pull`/`word_pop`. The shape of the idea, not the polish
of the line, decides the kind — captions already carry the words; the
visual should carry the structure.

## 3. Shape of the idea → kind

Work out what shape the idea has — ignore its wording — then take the row:

| Shape | kind | Notes |
|---|---|---|
| ordered sequence / causal chain (A, then B, then C) | `vertical_timeline` | one step per stage; 3–6 steps; per-step `appear_sec` (§4) |
| X-of-Y count | `ratio_dots` | needs a spoken total; `mark_at` on the marking word |
| trend, or a stated shift ("went from 50 to 6") | `inline_chart` | `data` holds only numbers the speaker said — `[50, 6]` is a valid 2-point chart |
| single hero magnitude | `stat_punch` | only THE number; shifts and ratios outrank it (picker tie-breakers) |
| pointing at a real UI / artifact | `image_card` (speaker stays) or `static` (hero) | real screenshot first — SKILL.md Image discipline |
| concrete metaphor with no real referent | generated image via `feinbild imagine` | procedure below |
| the takeaway line | `quote_pull` | here the words ARE the idea; text is correct |
| genuinely just a strong line | `word_pop` | the fallback, never the default for explanations |

**Metaphor procedure:** (1) the metaphor's subject must pass the four-word
test (doctrine §1) — "a conveyor belt" passes; a multi-subject tableau
fails, so simplify or skip. (2) Check for a real referent first: an actual
screenshot beats an illustration of the analogy. (3) Generate via
`feinbild imagine` under SKILL.md Image discipline — brand-prefixed prompt,
ONE locked style per video (`style.txt`). (4) Show it as `image_card` so
the speaker keeps telling the analogy; `static` only when the metaphor IS
the moment.

**Not expressible yet — don't force it:**

| Shape | Honest move |
|---|---|
| network / topology (things connect; order irrelevant) | leave the speaker on screen, or render a diagram via `feinbild` (excalidraw/svg → PNG) and place it under Image discipline |
| side-by-side before/after of two real screens | no split kind yet — sequence two image beats (respect `IMAGE_BREATH`) or let the speaker carry it |

A forced mapping — a fake "timeline" of two unordered things — is worse
than no beat.

## 4. The build principle

A concept visual UNFOLDS with the voice. A frame that arrives complete is a
slide pasted onto a video; an edit assembles the viewer's understanding at
the same rate the sentence does.

- `vertical_timeline.steps[].appear_sec` and `word_pop.items[].appear_sec`:
  one timestamp per item, copied from `words.json` at the word that names
  it (SKILL.md hard rule 3). Never let every item share the beat's start.
- `ratio_dots.mark_at`: the dots take their marked state on the spoken
  word, not on entry.
- `stat_punch`, `quote_pull`, `inline_chart` animate internally from the
  anchor — the anchor IS their build; place it on the exact phrase.

A multi-item beat whose items all land at `start_sec` is authored wrong
even when lint stays quiet.

## 5. The quota

Every ~60 seconds of teaching-dense material owes the viewer **one genuine
concept visual** — a `vertical_timeline`, `ratio_dots`, `inline_chart`, or
image beat that passes the §1 gate. A stretch where every beat is typography
(`word_pop`, `stat_punch`, `quote_pull`) means the viewer was read to, not
shown — go back to §2 and look for the structure you skipped. The quota
changes WHICH kinds fill the density budget (doctrine §2 table), never the
budget itself.
