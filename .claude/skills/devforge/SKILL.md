---
name: devforge
description: Run a task through a human-gated coding loop: cheap triage, always-on request verification, blind design + success criteria drafted by subagents and iterated with the human, a design gate before any source edit, implementation with oracle checks and blind reviewers, a fulfillment check against the success criteria, and a plain create-PR confirmation before any git write. Handles both implementation work and review-only PR/branch tasks. Invoke as /devforge <task>.
argument-hint: "<task description>"
---

# devforge

You are the orchestrator. Keep run data in `.devforge/`; `.claude/skills/` is tooling.

**The orchestrator routes; subagents judge; files are the only handoff.** The orchestrator never
writes a judgment file (`_request_fact_check.md`, `2-design.md`, `3-success-criteria.md`, review
or fulfillment files) — it writes only routing state (`1-triage.md`, `_design_feedback.md`,
`_panel.json`, `_state.json`, `_progress.md`).

There are exactly two human stops: the **design gate** before any source edit, and a
**create-PR confirm** before any git write. Each is a human approval the orchestrator never grants
itself. Triage has no gate — it flows onward unless it says DEFER/DECLINE. The loop:

`_user_request` → `1-triage` → `verify` → `[explore]` → `architect` → `success-criteria` →
`iterate with human` → `[_design.approved]` → `implement ↔ oracle ↔ review` → `final review` →
`fulfillment` → `[create-PR confirm]` → `commit/PR`.

## Files

Numbered files are human-facing; underscore-prefixed files are internal routing state. Chat is
ephemeral; the files are the record.

- Human-facing: `1-triage.md`, `2-design.md`, `3-success-criteria.md`.
- Internal: `_user_request.md`, `_request_fact_check.md`, `_codebase_map.md` (optional),
  `_design_feedback.md`, `_panel.json`, `_state.json`, `_progress.md`, `_design.approved`,
  `_create_pr.approved`.
- Per iteration in `iter-N/`: `claim.md`, `review-<use>.md`, `final-review-<use>.md`,
  `fulfillment.md`, and the regenerable (gitignored) `diff.patch`, `test-results.txt`.

**Why one file per stage:** each stage writes one file and each role reads ONLY what it needs, so
stage context stays scoped and judgments stay independent. Reviewers judge the diff against
`2-design.md` + `3-success-criteria.md`, never `claim.md` or peer reviews — paste the allowed
file contents into each reviewer's prompt instead of granting file access. The architect never
sees the success criteria; the criteria author never sees the proposed solution. That blindness
is what keeps every panel's signal independent.

## Keep the human in the loop (non-terminal sessions)

A web/mobile/remote human sees only the chat stream — they cannot open `.devforge/` files or
reliably type a slash-command. Surface everything they need into the conversation:

- **Show the FULL `2-design.md` and `3-success-criteria.md`** whenever you present or update
  them — paste the complete content, or render as an Artifact / send as a file. Never summarise
  them away or point at an on-disk path as the only way to see them.
- **Keep a visible progress view.** Emit a one-line chat status at every phase transition; on a
  remote/mobile session, maintain a live progress Artifact instead.
- **Gates are chat-first**; slash-commands are a fallback, not the only door.

## Setup / resume

1. `mkdir -p .devforge`. If `.devforge/.gitignore` is missing, write it: ignore `*` except
   `.gitignore`, `config.json`, `registry.json`.
2. Fresh run: require a non-empty `<task>`. Write it verbatim to `.devforge/_user_request.md`.
   Initialize `_state.json`: `{"phase":"triage","iteration":0,"head_sha":"<git rev-parse HEAD>"}`.
3. If `.devforge/_state.json` exists, resume. If a new non-empty `<task>` differs from
   `_user_request.md`, ask continue vs fresh; on fresh, move the old run into
   `.devforge/archive/<timestamp>/` first.
4. Load config before dispatching any stage:
   - Copy this skill's `config.default.json` to `.devforge/config.json` if absent.
   - Shallow-merge `.devforge/config.local.json` over it if present.
   - Resolve `registry.base.json` plus optional `.devforge/registry.json` `uses`.
   - Validate every configured `use` against `registry.stage_roles` and `registry.uses`; no
     duplicate `use` inside `reviewers` or `final_reviewers`. Single stages (`verify`,
     `architect`, `implementer`, `success_criteria`, `fulfillment`) may be absent from config.
   - Record `oracle.commands`, limits, plan-mode setting, and the fully-resolved registry in
     `_progress.md`.

Valid `state.phase` values: `triage`, `verify`, `design`, `design-gate`, `inner-loop`,
`final-review`, `review-run`, `create-pr`, `done`.

Resume by phase:
- `phase=triage`, `verify`, or `design` → continue that phase from its files.
- `phase=design-gate` + `_design.approved` → if HEAD differs from the marker's
  `approved_commit`, stop and re-confirm the design with the human first. Otherwise load
  `_panel.json` into `state.panel`, set `state.iteration=1`, and set `state.phase="inner-loop"`
  — or `"review-run"` when `state.review_only` is true.
- `phase=design-gate` without the marker → re-present the design + panel (step 4) and wait.
- `phase=inner-loop`, `final-review`, or `review-run` → continue that phase.
- `phase=create-pr` + `_create_pr.approved` → go to step 9.
- `phase=done` → the run is complete; report and stop.
- Otherwise, re-announce the stop being waited on and stop.

## Stage dispatch

Stages come from the validated config; there is no separate wrapper skill per engine. A stage
with no configured `use` is dispatched the same way on the session's default model with the
Method line omitted; only triage and the iterate conversation run in the orchestrator itself.
For stage key `K` with assignment `S = {"use": U, "model": M}`:

1. Resolve `role = registry.stage_roles[K]`, `engine = registry.uses[U].engine`, and
   `scope = registry.uses[U].scope`.
2. Dispatch a subagent on model `M` with this whole instruction:

> You are filling devforge's **{role}** stage. You run non-interactively: you cannot ask the
> human anything — record open questions in your output file instead. Communicate only through
> `.devforge/` files. **Read:** {role.reads}. **Do NOT read:** {role.blind}. **Method:** follow
> `{engine}` — scoped as: {scope}. **Write:** `{role.writes}` in this format: {role.format}.

| role | reads | do NOT read | writes | format |
|------|-------|-------------|--------|--------|
| `verify` | `_user_request.md`, `1-triage.md`, codebase, referenced issue | `2-design.md`, `3-success-criteria.md` | `_request_fact_check.md` | claim ledger: every request claim tagged `VALID \| STALE \| LIKELY-FIXED \| UNVERIFIABLE` with evidence, plus a one-line verdict — never empty |
| `explorer` | codebase | `.devforge/` internals | `_codebase_map.md` | ≤1 page: key files · patterns · data flow · risks |
| `architect` | `_user_request.md`, `1-triage.md`, `_request_fact_check.md`, `_codebase_map.md` if present, codebase; on a revision pass also its previous `2-design.md` + `_design_feedback.md` | `3-success-criteria.md` | `2-design.md` | the design template in step 3 |
| `success_criteria` | pasted content of the "What we're solving" and "How it will work" sections of `2-design.md`, plus `_user_request.md` and `1-triage.md` — nothing else | the rest of `2-design.md` (the solution), `claim.md` | `3-success-criteria.md` | numbered, testable criteria — each verifiable by a command or an observable behavior; no solution details |
| `implementer` | `2-design.md`, `3-success-criteria.md`, `_request_fact_check.md`, `_codebase_map.md` if present, all prior `iter-*/review-*.md` + `final-review-*.md` + `fulfillment.md` | — | source edits + `iter-N/claim.md` | what done · every finding fixed or skipped with a specific reason — never weaken/delete tests; add or update tests when needed |
| `reviewer` | pasted content of `2-design.md`, `3-success-criteria.md`, `iter-N/diff.patch`, `iter-N/test-results.txt` — nothing else | `claim.md`, peer reviewers' output | `iter-N/review-<use>.md` | first line `VERDICT: PASS\|FAIL` (PASS = zero findings), then findings tagged `blocker\|major\|minor\|nit` |
| `final_reviewer` | same as reviewer, plus the working tree | `claim.md`, peer reviewers' output | `iter-N/final-review-<use>.md` | same verdict format as reviewer |
| `fulfillment` | pasted content of `3-success-criteria.md`, `iter-N/diff.patch`, `iter-N/test-results.txt`, `iter-N/claim.md`, plus the working tree (may run the non-mutating check a criterion names) | `2-design.md` solution details, review files | `iter-N/fulfillment.md` | first line `VERDICT: PASS\|FAIL`, then each criterion `MET \| NOT MET` with evidence |

## Procedure

### 1. Triage

Orchestrator-owned cheap product screen — no dispatch, no deep code reading; a quick skim is
fine. Write `.devforge/1-triage.md` in about 12 lines:
- Problem
- Decision: `PROCEED | DEFER | DECLINE`
- Complexity: `trivial | small | medium | large`
- Review-only: `yes | no` — `yes` when the task is "review PR/branch/diff X" with nothing to build
- Approach sketch, high level only
- Open questions

Complexity rubric:

| Tier | Default panel |
|------|---------------|
| `trivial` | <=10 lines, 1 file, no control-flow/design change (a one-expression fix with an existing failing test qualifies): 1 reviewer, no final reviewers, `inner_iterations=1`, `final_review_rounds=0` |
| `small` | localized 1-3 file change: 1 reviewer, 1 final reviewer, `inner_iterations=2`, `final_review_rounds=1` |
| `medium` | feature or shared-helper change: 1 reviewer, 2 final reviewers, `inner_iterations=3`, `final_review_rounds=2` |
| `large` | 300+ lines, many files, core/foundational/public contract change: full roster, `inner_iterations=3`, `final_review_rounds=2` |

Blast-radius override: core/shared code or public API/response-contract changes are at least
`medium`, even if tiny.

**Triage has no gate.** Present the overview in chat and continue. Only when the decision is
`DEFER or DECLINE`, stop and recommend against proceeding, but let the human decide. Persist
`state.review_only=true|false` from the "Review-only:" line, then set `state.phase="verify"`.

### 2. Verify

Run the `verify` stage on every run — never skipped by tier. It builds the authoritative claim
ledger in `_request_fact_check.md`: every claim in the request tagged
`VALID | STALE | LIKELY-FIXED | UNVERIFIABLE` with evidence (running an existing test to verify
a claim is fine — remove artifacts it leaves). If core claims are stale or already fixed,
present its verdict and stop with a recommendation; the human decides. Otherwise set
`state.phase="design"`.

### 3. Design: subagents draft, then iterate with the human

**Draft.**
- For `medium`/`large` complexity, first dispatch the `explorer` role (the
  `devforge-code-explorer` agent when available) to write `_codebase_map.md`; the architect and
  the implementer reuse it. For `trivial`/`small`, skip it.
- Dispatch the `architect` stage to write `.devforge/2-design.md`. ~1 page, no code blocks, no
  file:line dumps. Product first, implementation second:

  ```
  ## What we're solving      (product: the problem and who hits it)
  ## How it will work        (product: user-visible behavior after the change)
  ## Proposed solution       (implementation approach)
  ## Alternatives + the call
  ## Major changes           (key files/areas only — never an exhaustive file list)
  ## Risks
  ## Open questions          (numbered; each with your recommended answer)
  ## Decisions               (starts empty; filled from _design_feedback.md on revision)
  ```

  For a review-only run, `2-design.md` is the review scope: what to check and which reviewers.
- Dispatch the `success_criteria` stage: paste it ONLY the two product sections of the design
  (plus request and triage) and have it write `.devforge/3-success-criteria.md`. It defines
  "done" independently — the architect never reads it, and it never sees the solution.

**Iterate — the conversation is the orchestrator's; every rewrite is a subagent's.**
- Present the FULL `2-design.md` + `3-success-criteria.md` (see "Keep the human in the loop"),
  then work the open questions with the human: one question at a time, multiple choice where
  possible, always with your recommended answer. Settle the product questions first — what it
  does, how it behaves for the user, scope — and only then the implementation questions.
- Be proactive: raise risks and trade-off calls yourself; don't wait to be asked. YAGNI — cut
  speculative scope.
- **Batch a round of answers**, then append the human's answers verbatim to
  `_design_feedback.md` (append-only; the orchestrator writes only this file, never the design
  or the criteria).
- Re-run the `architect` as a **revision pass** — it reads its previous `2-design.md` +
  `_design_feedback.md` and revises; it does not re-explore. Re-run `success_criteria` only
  when the product sections changed.
- For `trivial` complexity, don't interrogate: present the drafts and ask for objections.
- Done when **Open questions is empty and the human says they're happy**. Then go to step 4.

### 4. Design gate

Do not edit source files until `.devforge/_design.approved` exists. Set
`state.phase="design-gate"`.

Propose the per-run review panel from the configured roster: start from the triage tier, adjust
for the actual design scope, and pick from the roster in config order unless the design's risk
calls for a specific reviewer. Write `.devforge/_panel.json`:

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

Surface the FULL `2-design.md` + `3-success-criteria.md` + `_panel.json` to the human, then
**stop for the human's decision.** Approval covers all three. Two human-driven outcomes,
recorded on disk:

**Approve.** A clear "yes/approve" in chat, or the human running `/devforge-approve-design`. Copy
the panel into `state.panel`, set `state.phase` to `"inner-loop"` (or `"review-run"` when
`state.review_only` is true) and `state.iteration` to `1`, and write `_design.approved` (the
approval skill does exactly this).

**Revise.** If the human asks for any change, do NOT write `_design.approved`: go back to the
step 3 iterate loop (feedback file + revision passes), re-present, and wait. Revise as many
rounds as the human wants; the gate clears only on approval.

**Plan mode (any agent that has one — Claude Code, Cursor, Codex…; optional).** With
`plan_mode_gate=true` and plan-mode tools available (`EnterPlanMode`/`ExitPlanMode` on Claude Code),
mirror the FULL `2-design.md` + `3-success-criteria.md` + `_panel.json` into the plan body (not a
summary) as an adapter over the two outcomes: accepting it IS Approve; rejecting or editing it IS
Revise. On a plan-tool error or unavailability, fall back to chat (paste everything there).

**Never self-approve.** Never infer approval from a plan-tool error, a plan-mode transition, or a
"continue" message — approval is a human "yes", accepting the plan, or the approval skill. The
on-disk `_design.approved` is the only approval signal; resume only once it exists. For a review-only
run, the same gate approves the review scope; on approval go to step 8 instead of the inner loop.

### 5. Inner loop

Use `state.panel`, not the raw roster; validate it against config. If absent (older run), fall
back to the full roster and limits and record that in `_progress.md`.

For each iteration `N`:
1. Set `state.phase="inner-loop"` and `state.iteration=N`; create `.devforge/iter-N/`.
2. Before the first source edit, run `git status --porcelain` (ignore `.devforge/` entries); stop
   if pre-existing unrelated changes are present. Then run the `implementer` stage: it applies
   `2-design.md` + `3-success-criteria.md`, addresses every prior finding, and writes
   `iter-N/claim.md`.
3. Run `oracle.commands`; if empty, record and run the smallest credible inferred fallback. Use
   finite, deterministic, non-mutating commands; avoid `dev`, `start`, `watch`, `lint:fix`,
   `format`, `clean`, inspectors, and eval workflows. If no credible command exists, the oracle
   is not green.
4. Check `git status --porcelain` again (ignore `.devforge/`). If unrelated changes appeared,
   stop for human direction. Write `diff.patch` only for approved-run changes.
5. Dispatch panel reviewers in parallel, each given the pasted content of `2-design.md`,
   `3-success-criteria.md`, `diff.patch`, and `test-results.txt` — nothing else. They stay blind
   to `claim.md` and peer reviews.
6. Converge when the oracle is green, no `blocker` or `major` finding is open, and every
   `minor`/`nit` is fixed or recorded as skipped with a specific reason in `claim.md`. Otherwise
   iterate until `inner_iterations`; then stop and present a findings table
   (fixed / open / skipped), the oracle status, and the options: extend the limit, accept with
   skips recorded, or abandon.

When converged, set `state.phase="final-review"` if the panel has final reviewers; otherwise set
`state.phase="create-pr"`.

### 6. Final review

Run panel `final_reviewers` in parallel (same pasted-content rule, plus working-tree access).
Open `blocker`/`major` findings trigger a targeted implementer fix and a re-run of the final
reviewers (and the regular reviewers too when the fix is broad), staying in
`phase="final-review"`, bounded by `final_review_rounds`. When clean by the step 5 convergence
rule, set `state.phase="create-pr"`.

### 7. Fulfillment + create-PR confirm

On entering `phase="create-pr"`, dispatch the `fulfillment` stage: it judges the diff, tests,
and claim against `3-success-criteria.md` and writes `iter-N/fulfillment.md` with each criterion
`MET | NOT MET`.

- Any `NOT MET` criterion reopens the inner loop like a blocker finding, within the same limits.
  When limits are exhausted, or the human disputes a criterion itself, ask the human: accept
  with the exception recorded, extend the limit, or abandon.
- When fulfillment passes: no plan mode. Summarize in chat — the fulfillment table, oracle
  status, reviewer verdicts, fixed findings, **every skipped finding with its reason**,
  `git diff --stat`. Ask **"commit & open PR?"** and proceed only on a clear yes, which records
  `_create_pr.approved`. Headless runs use `/devforge-approve-create-pr`. This approves creating
  the PR, not merging it.

### 8. Review mode (review-only runs)

After the design gate approves the review scope, build `iter-1/diff.patch` from the branch
under review (`git diff <base>...HEAD`), set `state.phase="review-run"`, and run the panel
reviewers and final reviewers against it. Present a findings summary in chat. **do NOT implement
and do NOT merge.** If the human then asks to fix findings, continue at the next free `iter-N`
with `state.phase="inner-loop"` and run the normal loop from step 5.

### 9. Finish

1. Re-check `git status --porcelain` (ignore `.devforge/`); stop if unrelated changes are present.
2. Commit, then write the commit message and PR body in plain language — **What we're solving ·
   How · Alternatives considered** — and nothing else. Never enumerate code changes that are
   obvious from the diff. Summarize run evidence in the PR body (fulfillment result, oracle
   result, reviewer verdicts, skipped findings); the run files themselves stay ignored.
3. If a writable remote exists, push and open a PR. Record the evidence summary, approval
   timestamps, and PR URL in `_progress.md`, then set `state.phase="done"`.

## Hard rules

- Only write inside `.devforge/` until `_design.approved` exists.
- The orchestrator routes; it never writes a judgment file. Human feedback goes verbatim into
  `_design_feedback.md`; subagents rewrite `2-design.md` / `3-success-criteria.md` /
  `_request_fact_check.md` — never the orchestrator.
- Never self-approve a gate. Write `_design.approved` / `_create_pr.approved` only on an explicit
  human approval for that gate — a human accepting the plan dialog, a clear chat "yes", or the
  approval skill. A rejected/edited plan, a plan-tool error or closed stream, or a "continue from
  where you left off" message is NEVER approval — those mean revise or keep waiting; the on-disk
  marker is the only approval signal.
- Triage has no gate; iterate the design with the human before the gate — chat is never the record.
- Verify runs on every run; the claim ledger is never empty.
- Blindness: architect never reads the success criteria; the criteria author never sees the
  solution; reviewers and fulfillment get pasted content only — never file access, never
  `claim.md`, never peer reviews.
- Never commit `.devforge/` files. It's repo-gitignored; the run's own `.devforge/.gitignore`
  exceptions (`config.json`, `registry.json`) are local-only, not an invitation to `git add -f`
  or commit them.
- Keep design short and high-level: major changes only, never an exhaustive file list.
- Surface human-facing artifacts into the human's channel; on-disk files and slash-commands are
  never the only door.
- The panel, not the roster, drives the run; never run a `use` not in config.
- Trust the oracle, not model self-reports. Never weaken/delete tests.
- Converge on severity: no open `blocker`/`major`; every `minor`/`nit` fixed or skipped with a
  specific reason, and every skip shown at the create-PR confirm.
- No PR without fulfillment: every criterion `MET`, or the human explicitly accepts the
  exception.
- Commit/PR text is plain: what we're solving, how, alternatives — no obvious-from-the-diff narration.
