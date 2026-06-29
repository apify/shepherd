---
name: devforge-approve-create-pr
description: HUMAN-ONLY devforge create-PR approval. Run after reviewing the change and .devforge evidence. Writes .devforge/_create_pr.approved and hands control back to /devforge. The agent cannot invoke this.
disable-model-invocation: true
allowed-tools: Read, Bash, Skill
argument-hint: ""
---

# Approve PR creation

Record human approval for commit, push, and PR creation. Interactive runs confirm in chat;
this skill is the headless fallback that records the same marker. This approves creating the
PR, not merging it.

1. Read `.devforge/_progress.md` plus the latest `iter-*/review-*.md` and
   `iter-*/final-review-*.md` files if present. Summarize the change, oracle status, and
   verdicts.
2. If tests are not green or any verdict is `FAIL`, warn the user and confirm they still want to
   proceed.
3. Write the marker:
   ```bash
   mkdir -p .devforge
   printf 'approved_at=%s\napproved_commit=%s\nnote=create-PR approved by human via /devforge-approve-create-pr\n' \
     "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git rev-parse HEAD 2>/dev/null || echo none)" \
     > .devforge/_create_pr.approved
   ```
4. Confirm briefly, then invoke `/devforge` so it resumes into finish.

This skill records approval only; it does not push or merge.
