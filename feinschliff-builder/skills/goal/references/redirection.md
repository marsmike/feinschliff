# Redirection directive

The loop has PLATEAUED — recent iterations stopped improving the score.
Incremental tweaks are exhausted. Step back and make a STRUCTURALLY DIFFERENT
change.

## Process
1. Read `.autoloop/<target>/notes/*.md` end-to-end. What has been tried? Where did
   past mutators think the next angle was?
2. Read `.autoloop/<target>/attempts/*.json`. Which kinds of changes were KEPT and
   which REVERTED? Find the pattern in what did not move the score.
3. Read `.autoloop/<target>/techniques/*.md`.
4. Ask: **what category of change has NOT been tried?**
   - If past mutators added clarifications -> try deletion (which instruction is
     contradictory or redundant?).
   - If they tightened wording -> try restructuring (section order, framing).
   - If they fixed one failure type -> address a different one.
   - If they all read the skill the same way -> try a different theory of what is
     wrong (e.g. the issue is *when* the skill fires, not *what* it says).
5. Apply ONE structurally-different change. Note in `notes/iter-N.md` that this
   was a redirection and which category you chose.

## Not allowed
- Don't bundle many small changes to seem different — that's incrementalism with
  more risk. Don't add length (plateau often comes from bloat; deletion is a
  legitimate redirection). Don't gut the skill — pivot the angle, keep the signal.
