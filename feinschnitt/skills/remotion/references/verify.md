
# Remotion Verify

Verify the final video matches the storyboard vision. The storyboard created in Phase 1 serves as the verification checklist — closing the loop from planning to validation.

## Prerequisites

- `docs/STORYBOARD.md` — Production storyboard (source of truth)
- `src/timing.ts` — Timing manifest
- Working Remotion project with all scenes implemented
- Final render completed (or ability to render stills)

## Process

### Step 1: Load Storyboard & Timing

Read `docs/STORYBOARD.md` and `src/timing.ts` to understand what was planned.

### Step 2: Extract Key Frames

For each beat in the storyboard, render the frame at the beat's start time:

```bash
npx remotion still src/index.ts Main frame-[sceneId]-[beatId].png --frame=[beatStartFrame]
```

Also render mid-beat and end-of-beat frames for beats with significant animation:

```bash
npx remotion still src/index.ts Main frame-[beatId]-mid.png --frame=[midFrame]
npx remotion still src/index.ts Main frame-[beatId]-end.png --frame=[beatEndFrame - 1]
```

### Step 3: Visual Comparison

For each beat, read the rendered frame using the Read tool (Claude's vision capabilities) and compare against the storyboard specification:

- Does the visual match the described concept?
- Are the correct components used (expected vs actual)?
- Does the layout match (positioning, spacing, alignment)?
- Are theme tokens applied correctly (colors, fonts)?
- Is the animation state correct at this frame?
- Is there any text overflow, overlap, or clipping?

### Step 4: Generate Verification Report

Write the report to `docs/VERIFICATION_REPORT.md` using the template from [verification-template.md](verification-template.md).

### Step 5: User Review Gate

Present the report to the user:

> "Verification report generated at `docs/VERIFICATION_REPORT.md`. [X/Y] beats passed. [summary of any issues]. Please review the report and the video, then let me know if you approve or want changes."

**If issues found:** Return to remotion-build to fix specific beats, then re-verify.

**If all passed:** Video production is complete. Commit verification report.
