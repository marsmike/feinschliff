
# Remotion Eval — Self-Improving Scene Evaluation

Stills-first QA loop: render keyframe stills → evaluate in parallel → fix failures → re-render stills → repeat until all pass → full render.

## When to Use

After scenes are implemented and renderable. Replaces the expensive "render everything then check" approach with fast still-based evaluation. Typically invoked after `remotion-build` (Phase 3).

## Prerequisites

- Remotion project with per-scene `<Composition>` entries in Root.tsx
- `src/timing.ts` with beat/scene timing data
- Scene source files in `src/scenes/`
- `parallel-render.sh` in the remotion scripts directory (for final MP4 render only)

## The Loop

```
┌──────────────────────────────────────────────────────┐
│  RENDER STILLS (npx remotion still, ~1s per frame)    │
│  5 keyframes per scene at 0%, 25%, 50%, 75%, 100%    │
└────────────────────────┬─────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│  EVALUATE (parallel sub-agents, 1 per scene)          │
│  Each agent: reads 5 stills → scores → fix instruct.  │
└────────────────────────┬─────────────────────────────┘
                         ▼
                    ┌────┴────┐
                    │All PASS?│
                    └────┬────┘
                 yes │      │ no
                     ▼      ▼
┌──────────────────────┐  ┌────────────────────────────┐
│  FULL MP4 RENDER     │  │ FIX (parallel sub-agents)   │
│  parallel-render.sh  │  │ Each: reads eval + source   │
│  → concat → done     │  │ → edits code → renders      │
└──────────────────────┘  │   verification still         │
                          └──────────────┬─────────────┘
                                         ▼
                          ┌──────────────────────────┐
                          │ RE-RENDER STILLS (failed  │
                          │ scenes only) → back to    │
                          │ EVALUATE                  │
                          └──────────────────────────┘
```

**Max iterations:** 3 (initial + 2 fix rounds).

## Step-by-Step Execution

### Step 1: Render Keyframe Stills

For each scene, render 5 stills directly from the Composition using `npx remotion still`. This is fast (~1s per frame) and catches layout/design issues before committing to full renders.

```bash
cd <project-dir>

# For each scene, compute frame positions and render stills
# Example for a 100-frame scene: frames 0, 25, 50, 75, 99
mkdir -p out/eval/Scene0

npx remotion still src/index.ts Scene0 out/eval/Scene0/frame_000.png --frame=0 --scale=0.5
npx remotion still src/index.ts Scene0 out/eval/Scene0/frame_025.png --frame=16 --scale=0.5
npx remotion still src/index.ts Scene0 out/eval/Scene0/frame_050.png --frame=32 --scale=0.5
npx remotion still src/index.ts Scene0 out/eval/Scene0/frame_075.png --frame=48 --scale=0.5
npx remotion still src/index.ts Scene0 out/eval/Scene0/frame_100.png --frame=64 --scale=0.5
```

**Scale:** Use `--scale=0.5` for evaluation (540x960 — fast render, enough detail to judge). Use `--scale=1.0` only for final verification if needed.

**Parallelism:** You can background the still renders per scene since they're independent:

```bash
for scene in Scene0 Scene1 Scene2 Scene3 Scene4 Scene5; do
  (
    mkdir -p out/eval/$scene
    for pct in 0 25 50 75 100; do
      FRAME=$((total_frames * pct / 100))
      [ $pct -eq 100 ] && FRAME=$((total_frames - 1))
      npx remotion still src/index.ts $scene out/eval/$scene/frame_$(printf '%03d' $pct).png \
        --frame=$FRAME --scale=0.5 --quiet
    done
  ) &
done
wait
```

### Step 2: Dispatch Parallel Evaluation Agents

Launch **one Agent per scene**, all in a **single message** for parallel dispatch. Each agent is a research-only agent (no code edits) that reads stills and returns structured scores.

**Agent type:** `general-purpose` (needs Read tool for images)

**Agent prompt template** — fill in `{scene}`, `{project_dir}`, `{source_file}`, `{scene_description}`:

```
You are a critical visual design evaluator for YouTube Shorts content.
Do NOT write any code or edit any files. This is evaluation only.

## Task
Evaluate scene "{scene}" ({scene_description}) by inspecting its rendered keyframe stills.

## Instructions

1. Read each keyframe image IN ORDER (use the Read tool — you will see the images):
   - {project_dir}/out/eval/{scene}/frame_000.png  (scene start)
   - {project_dir}/out/eval/{scene}/frame_025.png  (25% through)
   - {project_dir}/out/eval/{scene}/frame_050.png  (midpoint)
   - {project_dir}/out/eval/{scene}/frame_075.png  (75% through)
   - {project_dir}/out/eval/{scene}/frame_100.png  (scene end)

2. Read the source code to understand intent:
   - {project_dir}/src/scenes/{source_file}

3. Score each criterion 0-10:

   **Heavyweight (70% weight):**
   - Design Quality (×0.35): color harmony, typography hierarchy, spatial balance, contrast, professional polish
   - Originality (×0.35): unique visualization concept vs generic template, creative use of animation

   **Lightweight (30% weight):**
   - Craft (×0.15): alignment precision, animation progression across frames, rendering quality, no artifacts
   - Functionality (×0.15): message clarity, information hierarchy, mobile readability (min 28px text)

4. Total = (design × 0.35) + (originality × 0.35) + (craft × 0.15) + (functionality × 0.15)

5. Verdict: PASS (>= 7.0) | REVIEW (5.0–6.9) | FAIL (< 5.0)

6. For REVIEW/FAIL: provide EXACT fix instructions. Reference the component name,
   specific JSX element/style property, and the precise change. Be unambiguous —
   another agent will execute these fixes mechanically.

## Output

Frame-by-frame observations, then this JSON block (machine-parsed):

```json
{
  "scene": "{scene}",
  "verdict": "PASS|REVIEW|FAIL",
  "total_score": 0.00,
  "scores": {"design_quality": 0, "originality": 0, "craft": 0, "functionality": 0},
  "fixes": [
    {"priority": 1, "component": "BeatXxx", "file": "src/scenes/BoschShort.tsx", "issue": "...", "instruction": "..."}
  ],
  "strengths": ["preserve this"]
}
```

Be harsh. Score a 5 as a 5, not a 7. This is the quality gate.
```

### Step 3: Collect Results & Decide

After all evaluation agents return:

1. **Parse JSON** from each agent's response (find the ```json block)
2. **Build summary table:**

| Scene | Design | Originality | Craft | Func | Total | Verdict |
|-------|--------|-------------|-------|------|-------|---------|
| Scene0 | 7 | 6 | 8 | 8 | 7.05 | PASS |
| Scene1 | 5 | 4 | 7 | 6 | 5.10 | REVIEW |

3. **Decision:**
   - All PASS → go to Step 6 (full render)
   - Any REVIEW/FAIL and iteration < 3 → go to Step 4 (fix)
   - Any FAIL after 3 iterations → ESCALATE to user

### Step 4: Dispatch Parallel Fix Agents

For each REVIEW/FAIL scene, launch a **fix agent** (parallel, one per scene):

**Agent prompt template:**

```
You are a Remotion component developer fixing visual issues in a YouTube Shorts scene.

## Scene: {scene} — Score: {total_score}/10 ({verdict})
## Iteration: {n}/3

## Issues to Fix (priority order):
{numbered list of fixes from evaluation agent}

## Strengths to PRESERVE (do NOT change these):
{list of strengths}

## Instructions
1. Read the source: {project_dir}/src/scenes/BoschShort.tsx
2. Read the theme: {project_dir}/src/theme.ts
3. Apply ONLY the listed fixes. Do not refactor or "improve" anything else.
4. Use the Edit tool for precise changes.
5. After each edit, render a verification still:
   ```bash
   cd {project_dir} && npx remotion still src/index.ts {scene} /tmp/{scene}-fix.png --frame={mid_frame} --scale=0.5
   ```
6. Read the still to confirm your fix looks correct.
7. Report exactly what you changed (file, line, old value → new value).

CRITICAL: Minimal edits. Only fix listed issues. Preserve strengths.
```

### Step 5: Re-Render Stills & Re-Evaluate

After fix agents complete:

1. Re-render keyframe stills for ONLY the fixed scenes (same as Step 1 but scoped)
2. Dispatch evaluation agents for ONLY the fixed scenes (same as Step 2 but scoped)
3. Merge new scores with existing passing scores
4. If all PASS → Step 6. If not and iteration < 3 → Step 4 again.

### Step 6: Full MP4 Render

All scenes passed evaluation. Now render the full video:

```bash
/path/to/remotion/scripts/parallel-render.sh --warmup <project-dir> Scene0 Scene1 ... SceneN
```

Or for a final preview check first:

```bash
/path/to/remotion/scripts/parallel-render.sh --preview <project-dir> Scene0 Scene1 ... SceneN
```

## Timing Expectations

| Step | Per Scene | 6 Scenes (parallel) |
|------|-----------|---------------------|
| Render 5 stills | ~5s | ~5s |
| Evaluation agent | ~15-30s | ~30s |
| Fix agent | ~30-60s | ~60s |
| Re-render stills | ~5s | ~5s |
| **One full iteration** | | **~90s** |
| Full MP4 render (final) | varies | ~8s preview, ~5min production |

Compare: rendering full MP4s before evaluating would cost ~5-10 minutes per iteration.

## Scoring Reference

| Score | Verdict | Action |
|-------|---------|--------|
| >= 7.0 | PASS | Ship it |
| 5.0–6.9 | REVIEW | Auto-fix, re-evaluate |
| < 5.0 | FAIL | Auto-fix, re-evaluate |
| < 5.0 after 3 rounds | ESCALATE | Report to user |

## Integration with Remotion Pipeline

```
Phase 1: remotion-storyboard  →  creative direction
Phase 2: remotion-audio        →  voiceover + timing
Phase 3: remotion-build        →  implement scenes
Phase 3.5: remotion-eval       →  stills-first QA loop (this skill)
         ↳ render stills → eval agents → fix agents → repeat
Phase 4: remotion-verify       →  final storyboard compliance (optional)
```

## Key Design Decisions

1. **Stills before MP4s:** Catch issues in ~5s instead of ~5min. Only render full video after QA passes.
2. **Parallel sub-agents:** One evaluator per scene runs concurrently. Same for fixers.
3. **Eval agents don't edit code:** Clean separation — evaluators only score, fixers only edit. Prevents confused agent roles.
4. **Fix agents verify their own work:** Each fixer renders a still after editing to confirm the fix visually.
5. **Scoped re-evaluation:** Only re-process scenes that failed. Passing scenes are locked in.
6. **Max 3 iterations:** Prevents infinite loops. If 3 rounds can't fix it, a human needs to look.
