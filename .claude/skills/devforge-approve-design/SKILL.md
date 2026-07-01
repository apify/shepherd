---
name: devforge-approve-design
description: HUMAN-ONLY devforge design approval. Run after reviewing .devforge/2-design.md and .devforge/_panel.json. Records the approved panel in _state.json, writes .devforge/_design.approved, and hands control back to /devforge. The agent cannot invoke this.
disable-model-invocation: true
allowed-tools: Read, Bash, Skill
argument-hint: ""
---

# Approve design

Record human approval of the design and review panel so implementation can begin.

1. Read `.devforge/2-design.md` and `.devforge/_panel.json`; stop if either is missing.
2. Summarize the approach, planned changes, reviewers, final reviewers, limits, and panel
   reason in 3-5 lines.
3. Copy the approved panel into `_state.json`:
   ```bash
   python3 - <<'PY'
   import json
   import re
   from pathlib import Path
   state_path = Path(".devforge/_state.json")
   panel = json.loads(Path(".devforge/_panel.json").read_text())
   for key in ("reviewers", "final_reviewers", "inner_iterations", "final_review_rounds"):
       if key not in panel:
           raise SystemExit(f"_panel.json missing required key: {key}")
   state = json.loads(state_path.read_text()) if state_path.exists() else {}
   triage = Path(".devforge/1-triage.md")
   triage_text = triage.read_text().lower() if triage.exists() else ""
   state_review_only = state.get("review_only")
   review_only = (
       state_review_only is True
       or str(state_review_only).lower() == "true"
       or bool(re.search(r"review-only\?\s*`?yes`?", triage_text))
   )
   state["panel"] = panel
   state["review_only"] = review_only
   if review_only:
       state["phase"] = "review-run"
   else:
       state["phase"] = "inner-loop"
   state["iteration"] = 1
   state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
   PY
   ```
4. Write the marker:
   ```bash
   mkdir -p .devforge
   printf 'approved_at=%s\napproved_commit=%s\nnote=design approved by human via /devforge-approve-design\n' \
     "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git rev-parse HEAD 2>/dev/null || echo none)" \
     > .devforge/_design.approved
   ```
5. Confirm briefly, then invoke `/devforge` so it resumes into review mode or implementation.

Do not edit source here.
