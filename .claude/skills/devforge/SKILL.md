---
name: devforge
description: Run a task through a human-gated coding loop: cheap triage, one design gate before source edits, implementation with oracle checks and blind reviewers, final review, and a plain create-PR confirmation before any git write. Handles both implementation work and review-only PR/branch tasks. Invoke as /devforge <task>.
argument-hint: "<task description>"
---

# devforge

You are the orchestrator. Keep run data in `.devforge/`; `.claude/skills/` is tooling.

There are exactly two human stops: the **design gate** before any source edit, and a
**create-PR confirm** before any git write. Each is a human approval the orchestrator never grants
itself. Triage has no gate — it flows into design unless it says DEFER/DECLINE. The loop:

`_user_request` → `1-triage` → `verify_request` → `explore` → `architect` → `2-design` →
`[_design.approved]` → `implement ↔ review ↔ test` → `final review` →
`[create-PR confirm]` → `commit/PR`.

## Files

Two files are human-facing; underscore-prefixed files are internal routing state.

**Why one file per stage:** each stage writes one file and each role reads ONLY what it
needs, so subagent context stays scoped and reviewers stay independent. Reviewers judge
the diff against `2-design.md`; they never see the implementer's `claim.md` or each
other's reviews — that blindness is what makes a multi-reviewer panel give independent signal.

- Human-facing: `1-triage.md`, `2-design.md`.
- Internal: `_user_request.md`, `_verified_task.md`, `_request_fact_check.md`, `_panel.json`, `_state.json`,
  `_progress.md`, `_design.approved`, `_create_pr.approved`.
- Per iteration in `iter-N/`: `claim.md`, `review-<use>.md`, `final-review-<use>.md`, and the
  regenerable (gitignored) `diff.patch`, `test-results.txt`.

Reviewer independence: reviewers read only `_verified_task.md`, `2-design.md`,
`iter-N/diff.patch`, and `iter-N/test-results.txt`. Never give them `claim.md` or peer
reviews.

## Setup / resume

1. `mkdir -p .devforge`.
2. Fresh run: require a non-empty `<task>`. Write it verbatim to `.devforge/_user_request.md`.
   Initialize `_state.json`: `{"phase":"triage","iteration":0,"head_sha":"<git rev-parse HEAD>"}`.
3. If `.devforge/_state.json` exists, read it and resume. If a new non-empty `<task>` differs
   from `_user_request.md`, ask whether to continue or start fresh.
4. Load config before dispatching any stage:
   - Copy this skill's `config.default.json` to `.devforge/config.json` if absent.
   - Shallow-merge `.devforge/config.local.json` over it if present.
   - Resolve `registry.base.json` plus optional `.devforge/registry.json` `uses`.
   - Validate every configured `use` against `registry.stage_roles` and `registry.uses`; no
     duplicate `use` inside `reviewers` or `final_reviewers`.
   - Record `oracle.commands`, limits, plan-mode setting, and the fully-resolved registry in
     `_progress.md`.

After config validation, resume by phase:
- `phase=design-gate` + `_design.approved` → load `_panel.json` into `state.panel`, set
  `state.phase="inner-loop"` and `state.iteration=1`, then go to step 6 — or, for a review-only
  run, set `state.phase="review-run"` and go to step 7.
- `phase=inner-loop`, `final-review`, `final-reopen`, or `review-run` → continue that phase.
- `phase=create-pr` + `_create_pr.approved` → go to step 9.
- Otherwise, re-announce the stop being waited on and stop.

## Stage dispatch

Stages are filled by the validated config. There is no separate wrapper skill per engine.
For stage `S = {"use": U, "model": M}`:

1. Resolve `role = registry.stage_roles[S]`, `engine = registry.uses[U].engine`, and
   `scope = registry.uses[U].scope`.
2. Dispatch a subagent on model `M` with this whole instruction:

> You are filling devforge's **{role}** stage. Communicate only through `.devforge/`
> files. **Read:** {role.reads}. **Do NOT read:** {role.blind}. **Method:** follow
> `{engine}` — scoped as: {scope}. **Write:** `{role.writes}` in this format:
> {role.format}.

| role | reads | do NOT read | writes | format |
|------|-------|-------------|--------|--------|
| `verify_request` | `_user_request.md`, `1-triage.md`, codebase, `gh` | — | `_verified_task.md` + `_request_fact_check.md` | claim ledger where each claim is `VALID \| STALE(→corrected ref) \| LIKELY-FIXED \| UNVERIFIABLE` with evidence, plus one-line verdict |
| `architect` | `_verified_task.md`, `_request_fact_check.md`, `1-triage.md`, codebase | — | `2-design.md` | short, ~1 page: What we're solving · How · Alternatives + the call · Major changes (key files/areas only, never an exhaustive file list) · Risks/open questions. No code, no file:line dumps |
| `implementer` | `_verified_task.md`, `_request_fact_check.md`, `2-design.md`, all prior `iter-*/review-*.md` + `final-review-*.md` | — | source edits + `iter-N/claim.md` | what done / skipped + specific reason / evidence — never edit/delete tests or spec files |
| `reviewer` | `_verified_task.md`, `2-design.md`, `iter-N/diff.patch`, `iter-N/test-results.txt` | `claim.md`, peer reviewers' output | `iter-N/review-<use>.md` | first line `VERDICT: PASS\|FAIL`, then severity-tagged findings. PASS means zero findings, including nits |
| `final_reviewer` | `_verified_task.md`, `2-design.md`, `iter-N/diff.patch`, working tree | `claim.md`, peer reviewers' output | `iter-N/final-review-<use>.md` | same verdict format as reviewer |

## Procedure

### 1. Triage

Goal: make a cheap product decision before deep analysis. Read `_user_request.md` and any
referenced issue, then skim only enough code to judge product value and obvious staleness.
Do not trace full execution paths and do not build a claim ledger.

Write `.devforge/1-triage.md` in about 15 lines:
- Problem
- Decision: `PROCEED | DEFER | DECLINE`
- Complexity: `trivial | small | medium | large`
- Review-only? `yes` when the task is "review PR/branch/diff X" with nothing to build
- Approach sketch, high level only
- Open questions

Complexity rubric:

| Tier | Default panel |
|------|---------------|
| `trivial` | <=10 lines, 1 file, no logic change: 1 reviewer, no final reviewers, `inner_iterations=1`, `final_review_rounds=0` |
| `small` | localized 1-3 file change: 1 reviewer, 1 final reviewer, `inner_iterations=2`, `final_review_rounds=1` |
| `medium` | feature or shared-helper change: 1 reviewer, 2 final reviewers, `inner_iterations=3`, `final_review_rounds=2` |
| `large` | 300+ lines, many files, core/foundational/public contract change: full roster, `inner_iterations=3`, `final_review_rounds=2` |

Blast-radius override: core/shared code or public API/response-contract changes are at least
`medium`, even if tiny.

**Triage has no gate.** Present the overview in chat and continue to verify_request. Only
when the decision is `DEFER or DECLINE`, stop and recommend against proceeding, but let
the human decide. Set `state.phase="verify_request"`.

### 2. Verify request

Run the `verify_request` stage. It confirms the request is specific and still true, then
writes `_verified_task.md` with corrected current references and `_request_fact_check.md`
with evidence. For GitHub issues or code-location claims, do the staleness check here:
fetch issue metadata, build a claim ledger, verify references against HEAD, and look for
already-fixed commits. If core claims are stale or likely fixed, stop with a
recommendation. Set `state.phase="explore"`.

### 3. Explore

Read enough code to ground the design. Record key files and patterns in `_progress.md`.
Set `state.phase="architect"`.

### 4. Architect

Run the `architect` stage. It writes `.devforge/2-design.md`: one short human-reviewable
page — **What we're solving · How · Alternatives + the call · Major changes (key
files/areas only, never an exhaustive file list) · Risks**. No code blocks, no file:line
dumps. For a review-only run, `2-design.md` is the review scope: what to check and which
reviewers to use. Set `state.phase="design-gate"`.

### 5. Design gate

Do not edit source files until `.devforge/_design.approved` exists.

Propose the per-run review panel from the configured roster. Start from the triage tier,
then adjust for the actual design scope. Write `.devforge/_panel.json`:

```json
{
  "tier": "small",
  "reason": "localized low-risk change",
  "reviewers": [{ "use": "staff-review", "model": "sonnet" }],
  "final_reviewers": [{ "use": "code-review", "model": "sonnet" }],
  "inner_iterations": 2,
  "final_review_rounds": 1
}
```

The approved panel must be a subset of the configured roster.

Present `2-design.md` and `_panel.json` for review, then **stop and wait for an explicit human
approval of the design**. If `plan_mode_gate=true` and plan-mode tools exist, use `EnterPlanMode`
→ mirror `2-design.md` plus `_panel.json` → `ExitPlanMode` as the review surface; otherwise
summarize both in chat.

Approval is an explicit human affirmative directed at this gate — a clear in-chat "yes/approve",
or the human running `/devforge-approve-design`. Only then is the panel copied into `state.panel`,
`state.phase` set to `"inner-loop"` (or `"review-run"` for a review-only run), `state.iteration`
set to `1`, and `_design.approved` written (the approval skill does exactly this).

A plan-mode exit, a rejected or edited plan, a plan-tool error or closed stream, and any
"continue"/system message are NOT approval — never infer it from a plan-mode transition or a tool
result. The on-disk `_design.approved` is the only approval signal; resume only once it exists.
For a review-only run, the same gate approves the review scope; on approval go to step 7 instead
of the inner loop.

### 6. Inner loop

Use `state.panel`, not the raw roster. Validate it against config; if absent for an older
run, fall back to the full configured roster and limits and record that in `_progress.md`.

For each iteration `N`:
1. Set `state.phase="inner-loop"` and `state.iteration=N`; create `.devforge/iter-N/`.
2. Run the `implementer` stage. It applies `_verified_task.md`, `_request_fact_check.md`,
   and `2-design.md`, addresses every prior review/final-review finding, and writes
   `iter-N/claim.md`.
3. Run `oracle.commands`; if empty, record and run the smallest credible inferred fallback. Use
   finite, deterministic, non-mutating commands; avoid `dev`, `start`, `watch`, `lint:fix`,
   `format`, `clean`, inspectors, and eval workflows. If no credible command exists, the oracle
   is not green.
4. Check `git status --porcelain`. If there are pre-existing unrelated changes, stop for human
   direction. Write `diff.patch` only for approved-run changes.
5. Dispatch panel reviewers in parallel. They are blind to `claim.md` and peer reviews.
6. Converge only when the oracle is green and every finding is fixed or explicitly skipped with a
   sound reason. Otherwise iterate until `inner_iterations`, then stop/escalate.

When converged, set `state.phase="final-review"` if there are final reviewers; otherwise set
`state.phase="create-pr"`.

### 6b. Final review

Run panel `final_reviewers` in parallel. Findings reopen implementation, bounded by
`final_review_rounds`. On a final-review-triggered reopen, set
`state.phase="final-reopen"`: it re-runs ONLY the final reviewers after the targeted fix
unless the fix is broad enough to need the regular reviewers too. When clean, set
`state.phase="create-pr"`.

### 7. Review mode (review-only runs)

After the design gate approves the review scope, build `iter-1/diff.patch` from the branch
under review (`git diff <base>...HEAD`), set `state.phase="review-run"`, and run the
panel reviewers and final reviewers against it. Present a findings summary in chat. **do NOT implement
and do NOT merge.** If the human then asks to fix findings, set
`state.phase="inner-loop"` and run the normal loop from step 6.

### 8. Create-PR confirm

No plan mode. Summarize the change in chat — oracle status, reviewer verdicts, fixed/skipped
findings, `git diff --stat`. Ask **"commit & open PR?"** and proceed only on a clear yes, which
records `_create_pr.approved`. Headless runs use `/devforge-approve-create-pr`. This approves
creating the PR, not merging it.

### 9. Finish

1. Re-check `git status --porcelain`; stop if unrelated changes are present.
2. Commit, then write the commit message and PR body in plain language — **What we're solving ·
   How · Alternatives considered** — and nothing else. Never enumerate code changes that are
   obvious from the diff. Include durable `.devforge/` evidence, not ignored transients.
3. If a writable remote exists, push and open a PR. Record oracle result, reviewer verdicts,
   approval timestamps, and PR URL in `_progress.md`.

## Hard rules

- Only write inside `.devforge/` until `_design.approved` exists.
- Never self-approve a gate. Write `_design.approved` / `_create_pr.approved` only on an explicit,
  unambiguous human "yes" for that specific gate (or when the human runs the approval skill). A
  plan-mode exit, a rejected/edited plan, a plan-tool error or closed stream, or a "continue from
  where you left off" message is NEVER approval — the on-disk marker is the only approval signal.
- Triage has no gate; it stops only on DEFER/DECLINE.
- Keep design short and high-level: major changes only, never an exhaustive file list.
- The panel, not the roster, drives the run; never run a `use` not in config.
- Trust the oracle, not model self-reports. Never weaken/delete tests.
- PASS means zero findings of any severity. Any nit makes `FAIL`.
- Resolve every reviewer finding before merge: fixed or specifically skipped.
- Keep reviewers blind to `claim.md` and peer reviews.
- Commit/PR text is plain: what we're solving, how, alternatives — no obvious-from-the-diff narration.
