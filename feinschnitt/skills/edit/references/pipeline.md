# Pipeline — edit

## Steps

1. **Probe** — `ffprobe` aspect + duration.
   - Portrait + ≤30 s → short mode.
   - Landscape or >60 s → longform mode.

2. **Transcribe** — `feinschnitt edit transcribe <video>` → `words.json` in the
   workdir (`feinschnitt edit workdir <video>`). This is the timing source of truth.

3. **Author the plan** — write `edit_plan.json` next to the video.
   Schema: `skills/edit/schema/edit-plan.schema.json`.
   For every explanation-heavy stretch run the concept pass first
   (`knowledge/concept-visualization.md`), then fill connectives via the template
   picker (`knowledge/template-picker.md`).

4. **Lint** — `feinschnitt edit lint <video> <plan>`. Fix every error; read every
   warning.

5. **Preview render** — `feinschnitt edit render <video> <plan>` (preview quality is
   the default). Report the output path to the user and STOP.

6. **Final render** — ONLY after the user approves the preview:
   `feinschnitt edit render <video> <plan> --quality final --brand <brand-dir>`.

## Beat catalog

| kind | class | required fields | use for / NOT for |
|---|---|---|---|
| `hook_title` | overlay | `title` | Cold-open lockup at 0.0 s / never mid-video |
| `word_pop` | overlay | `items[text+appear_sec]` | Enumerations + emphasis lines / not card-styled lists |
| `stat_punch` | takeover | `value, caption` | The hero number / not for every number mentioned |
| `quote_pull` | takeover | `quote_text` | The takeaway line; anchor covers the spoken quote (cps + 2 s dwell computed) / not passing remarks |
| `static` | takeover, image | `image_path` | Hero screenshots/photos full-frame (contain, never cropped) / not the b-roll default |
| `image_card` | overlay, image | `image_path` | DEFAULT for b-roll — speaker stays visible / not for text-heavy screenshots needing full-frame |
| `vertical_timeline` | takeover, sequence | `steps[heading+appear_sec]` | 3–6 ordered steps narrated one by one (rail reveals each on its word) / not unordered lists |
| `ratio_dots` | overlay | `total, marked, polarity, mark_at` | Any spoken "X of Y" (≤25 dots reads best) / not percentages of unstated totals |
| `inline_chart` | overlay | `title, data` | Trends/distributions the speaker describes / not single numbers |

## Knowledge docs

| Doc | When to read it |
|---|---|
| `knowledge/editing-doctrine.md` | Before authoring ANY plan — density budget, meaning gate, hook/endings |
| `knowledge/template-picker.md` | During step 3, per candidate moment |
| `knowledge/concept-visualization.md` | Every explanation-heavy stretch — teach-gate pass FIRST, then the picker |
| `knowledge/corrections.md` | Whenever a transcript mishearing or taste rejection surfaces |

## Output contract

- **Preview:** `<stem>.preview.mp4` next to the source — voice track is
  bit-identical to the input (verify enforces).
- **Final:** `<stem>.enhanced.mp4` next to the source — scored by default;
  with `--no-score` the voice track stays bit-identical and verify enforces that instead.
