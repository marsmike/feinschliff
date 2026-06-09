# Verification Report Template

Write to `docs/VERIFICATION_REPORT.md` in the project.

```markdown
# Video Verification Report

**Generated:** [Date]
**Storyboard:** docs/STORYBOARD.md
**Video:** out/video.mp4

---

## Summary

**Total Beats:** [N]
**Passed:** [X] ✅
**Issues Found:** [Y] ⚠️
**Failed:** [Z] ❌

**Overall Status:** ✅ Pass | ⚠️ Needs Revision | ❌ Fail

---

## Scene [N]: [Title]

### Beat [N.M]: [Story Moment]

**Expected (from storyboard):**
- Concept: [concept name]
- Visual Type: [flowchart/timeline/etc.]
- Components: [expected components]
- Animation: [expected animation]
- Timing: frames [X] - [Y]

**Actual (from rendered frame):**
- Visual: [description of what was rendered]
- Components: [components identified]
- Layout: [layout assessment]
- Animation State: [animation state at captured frame]

**Verification:**
- [ ] Visual matches storyboard description
- [ ] Correct components used
- [ ] Animation executed as specified
- [ ] Timing aligns with audio
- [ ] No layout issues (overlap, overflow, alignment)
- [ ] Theme tokens used correctly

**Status:** ✅ Pass | ⚠️ Issues Found | ❌ Fail

**Notes:**
[Any discrepancies, issues, or observations]

---

[Repeat for each beat]

---

## Issues Requiring Attention

1. [Scene X, Beat Y]: [Issue description] — [Suggested fix]
2. [Scene X, Beat Y]: [Issue description] — [Suggested fix]

## Recommendations

[Any overall improvements or suggestions for the next iteration]
```
