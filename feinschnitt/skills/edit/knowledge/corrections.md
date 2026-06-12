# Corrections — one-off fixes become permanent memory

Three classes of defect surface when a rendered video is reviewed; each has
exactly one durable fix. The common law: never patch the artifact — patch
the system that produced it, so the NEXT video is born fixed.

## 1. Transcription mishearings → a table row

Whisper's mistakes are systematic — the same brand name fails the same way
in every video — and `words.json` is derived: a hand-edit evaporates on
the next transcribe and helps no future video. The durable fix is a row in
`src/feinschnitt/edit/corrections.py` (SKILL.md hard rule 9):

- `BRAND_WORDS` — a single misheard token; the replacement case-matches the
  heard token ("Cloud" → "Claude"; an all-lowercase "cloud" becomes "claude").
- `PHRASE_CORRECTIONS` — multi-token runs ("fine schnitt" → "feinschnitt";
  the run's timing span is preserved across the replacement) AND
  single-token tuples for stylized-lowercase brands, where the canonical
  token must be emitted verbatim with no case-matching.

**Worked example (PR #69, 2026-06-12):** the first real-voice run showed
Whisper (small) hearing the brand names as single fused tokens —
"fineschnitt", "fineschmieder" — not the two-token splits the table
anticipated. Fix: single-token tuples appended to `PHRASE_CORRECTIONS`
(`("fineschnitt",) → ("feinschnitt",)` etc.), dated in a comment. The
transcription cache key includes `corrections.fingerprint()`
(`transcribe.py`), so adding a row invalidates cached transcripts and the
next `transcribe` re-applies the table — no manual cache busting.

List longer phrases before any entry that is their prefix (first match
wins). Tell the user every time you add a row.

## 2. Taste rejections → a dated rule (+ lint where expressible)

When the user rejects a rendered choice ("never do X again"), re-rendering
fixes one video. The durable fix is BOTH:

1. a dated rule appended to the relevant knowledge doc
   ([editing-doctrine](editing-doctrine.md), [template-picker](template-picker.md),
   [concept-visualization](concept-visualization.md)), and
2. a check in `src/feinschnitt/edit/lint.py` whenever the rejection
   reduces to something measurable. Precedent: lint's existing floors are
   frozen taste decisions — `TEXT_VERTICAL_FLOOR` (text never over the
   face), `IMAGE_BREATH` (no slideshow), `HOOK_DEADLINE`,
   `FIRST_TAKEOVER_FLOOR`.

Rule format, verbatim:

> **YYYY-MM-DD** — rejected: <what rendered and why it failed>.
> Rule: <one sentence, brand-agnostic>. Enforced: <lint constant> | prose-only.

"Prose-only" is legitimate when the judgment can't be made deterministic
("too clever a metaphor") — but reach for lint first: a warning the machine
raises outlives any sentence an agent must remember to read.

## 3. The per-round feedback audit

After every review round on a real video, write `feedback-<YYYY-MM-DD>.md`
in the vault project folder (`02_Projects/feinschliff/`), one entry per
defect:

| Field | Content |
|---|---|
| defect | timestamp in the video + what the user saw |
| plan fix | the concrete `edit_plan.json` change for THIS video |
| doctrine rule | the §2 rule added (or the existing rule violated) |
| lint check | constant name, or "prose-only" + why |

The audit is the bridge from feedback to doctrine: a defect whose row ends
with neither a doctrine rule nor a lint check is a defect you have agreed
to ship again.
