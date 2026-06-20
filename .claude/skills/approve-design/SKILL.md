---
name: approve-design
description: HUMAN-ONLY design-gate approval for the devforge loop. Run this after reviewing .devforge/design.md to unlock implementation — it writes .devforge/design.approved, which the /devforge:devforge loop requires before it will edit any source. The agent cannot invoke this; only a human can approve.
disable-model-invocation: true
allowed-tools: Read, Bash, Skill
argument-hint: ""
---

# Approve design (human-only gate)

You are recording a **human's** approval of the design so implementation can begin.
This is the only thing that opens the design gate; the agent cannot reach it.

1. Read `.devforge/design.md`. If it does not exist, STOP and tell the user there
   is no design to approve yet.
2. Give the user a 3–5 line summary of what they are approving (the core approach and
   the planned changes) so the approval is informed.
3. Write the approval marker so the /devforge:devforge loop will proceed to implementation:
   ```bash
   mkdir -p .devforge
   printf 'approved_at=%s\napproved_commit=%s\nnote=design approved by human via /devforge:approve-design\n' \
     "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git rev-parse HEAD 2>/dev/null || echo none)" \
     > .devforge/design.approved
   ```
4. Briefly confirm the approval is recorded, then **continue automatically**: invoke the
   `devforge` skill (`/devforge:devforge`). It resumes from `.devforge/state.json` straight
   into implementation — do not stop to ask the user to re-run anything.

Do NOT edit source files *in this skill*. You only record approval and then hand off to
`devforge`, which does the implementation under its own (unrestricted) context.
