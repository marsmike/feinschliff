# Error Recovery

Failure handling and retry strategies for each pipeline phase.

| Phase | Failure | Action |
|-------|---------|--------|
| 1 Storyboard | User rejects | Iterate with new options |
| 2 Audio | Duration wrong | Regenerate clips |
| 3 Build | Scene broken | Per-scene fix loop (max 3) |
| 4 Eval | Fails QA | Fix + re-eval (max 3) |
| 5 Verify | Doesn't match | Back to Phase 3 → 4 → 5 |
| 5 Verify | Storyboard wrong | Back to Phase 1, cascade all |
