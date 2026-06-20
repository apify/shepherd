---
name: approve-merge
description: HUMAN-ONLY pre-merge-gate approval for the devforge loop. Run this after reviewing the change and the evidence in .devforge/ to unlock push / merge / PR-create — it writes .devforge/merge.approved, which the /devforge:devforge loop requires before it will push or merge. The agent cannot invoke this; only a human can approve.
disable-model-invocation: true
allowed-tools: Read, Bash, Skill
argument-hint: ""
---

# Approve merge (human-only gate)

You are recording a **human's** approval to merge so push / PR-create can proceed.

1. Summarize the evidence the human is approving: read `.devforge/progress.md` and
   the latest `.devforge/iter-*/review-*.md` + `final-review-*.md` if present. Give a
   3–5 line summary — what changed, the test/oracle status, and each reviewer's verdict.
2. If tests are not green, or any reviewer verdict is FAIL, **warn the user
   explicitly** and ask them to confirm they still want to approve before continuing.
3. Write the approval marker so the /devforge:devforge loop will proceed to push/merge:
   ```bash
   mkdir -p .devforge
   printf 'approved_at=%s\napproved_commit=%s\nnote=merge approved by human via /devforge:approve-merge\n' \
     "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git rev-parse HEAD 2>/dev/null || echo none)" \
     > .devforge/merge.approved
   ```
4. Briefly confirm the approval is recorded, then **continue automatically**: invoke the
   `devforge` skill (`/devforge:devforge`). It resumes from `.devforge/state.json` into the
   finish step (commit + PR) — do not stop to ask the user to re-run anything.

This skill only records approval and hands off; it does not push or merge anything itself.
