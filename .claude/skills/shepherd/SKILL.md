---
name: shepherd
description: Use when the human asks for a coding task to run through shepherd's human-gated pipeline with durable run files under .shepherd/ instead of direct editing — features, bug fixes, refactors. Invoked on demand: /shepherd <task> starts a run, bare /shepherd resumes the run recorded in .shepherd/_state.json — never auto-invoked for a task that merely looks suitable.
argument-hint: "<task description>"
---

# shepherd

You are the orchestrator. Keep run data in `.shepherd/`; `.claude/skills/` is tooling.

**The orchestrator routes; subagents judge; files are the only handoff.** The orchestrator never
authors a judgment file (`_request_fact_check.md`, `2-design.md`, `3-success-criteria.md`,
review, question-verification, or fulfillment files; persisting one verbatim as a relay is not
authorship). Everything else in `.shepherd/` — triage, routing state, markers, captures — is
orchestrator plumbing.

Two human gates, never self-granted: the **design gate** before any source edit and the
**create-PR confirm** before opening the PR. Triage has no gate. The loop:

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
  `question-verification.md`, `fulfillment.md`, `followups.md`, and the regenerable (gitignored)
  `diff.patch`, `test-results.txt` (plus `baseline.txt` in `iter-1/` only — the pre-change
  oracle metrics).

**Why one file per stage:** each stage writes one file and each role reads ONLY what it needs, so
stage context stays scoped and judgments stay independent. Reviewers judge the diff against
`2-design.md` + `3-success-criteria.md`, never `claim.md` or peer reviews — design and criteria
are pasted into the prompt; `.shepherd/` itself is never granted. Blindness applies to
judgments, never to ground truth: every reviewer reads the repository and its git history (a
reviewer who can't run `git show` can't verify equivalence claims). The architect never sees
the success criteria; the criteria author never sees the proposed solution.

## Keep the human in the loop (non-terminal sessions)

A web/mobile/remote human sees only the chat stream — they cannot open `.shepherd/` files or
reliably type a slash-command. Surface everything they need into the conversation:

- **Show the FULL `2-design.md` and `3-success-criteria.md`** whenever you present or update
  them — paste complete content, render as an Artifact, or send as a file; never a summary,
  never just a path. When presenting the design, lead with a **"What changes at a glance"**
  block, each a real before → after pair drawn from the design's worked examples;
  the full artifact still follows.
- **Keep a visible progress view.** Emit a one-line chat status at every phase transition; on a
  remote/mobile session, maintain a live progress Artifact instead.
- **Gates are chat-first**; slash-commands are a fallback, not the only door. Channel order:
  plan-mode dialog for the design gate (when `plan_mode_gate=true`), plain chat for everything
  else. Question widgets (e.g. `AskUserQuestion`) fit only genuinely multiple-choice design
  questions — never a gate's approve/revise decision. After one stream failure of a widget or
  plan-mode tool, drop that channel for the rest of the run: plain chat for every later gate
  and question.

## Setup / resume

1. Resolve the absolute path of the target repo's `.shepherd/` once at setup and use it for
   every read/write — relative paths drift with the working directory in long sessions.
   `mkdir -p` it. If `.shepherd/.gitignore` is missing, write it: a single `*` line, so git
   ignores everything in `.shepherd/`, the `.gitignore` itself included. Humans who want
   `config.json` / `registry.json` committed add the exceptions there themselves.
2. Fresh run: require a non-empty `<task>`. Write it verbatim to `.shepherd/_user_request.md`.
   Initialize `_state.json`: `{"phase":"triage","iteration":0}`.
3. If `.shepherd/_state.json` exists, resume. If a new non-empty `<task>` differs from
   `_user_request.md`, ask continue vs fresh; on fresh — or when the previous run is
   `phase=done` — move the old run's files (all numbered/underscore files and `iter-*/`, keeping
   `config.json`, `config.local.json`, `registry.json`, `.gitignore`) into
   `.shepherd/archive/<timestamp>-<short-slug>/` first. Sequential runs are normal; for batch
   tasks off one base, note sibling PRs touching the same files in each PR body.
4. Load config before dispatching any stage:
   - Copy this skill's `config.default.json` to `.shepherd/config.json` if absent.
   - Shallow-merge `.shepherd/config.local.json` over it if present.
   - Resolve `registry.base.json` plus optional `.shepherd/registry.json` `uses`.
   - Validate every configured `use` against `registry.stage_roles` and `registry.uses`; no
     duplicate `use` inside `reviewers` or `final_reviewers`. Single stages (`verify`,
     `architect`, `implementer`, `success_criteria`, `fulfillment`, `followups`) may be absent
     from config.
   - Record `oracle.commands`, limits, plan-mode setting, and the fully-resolved registry in
     `_progress.md`.
   - As each dispatched stage completes, append one ledger line to `_progress.md`: stage ·
     `use` · model · reported token count · duration — per-stage cost stays greppable in the run.

Valid `state.phase` values: `triage`, `verify`, `design`, `design-gate`, `inner-loop`,
`final-review`, `create-pr`, `done`.

Resume by phase:
- `phase=triage`, `verify`, or `design` → continue that phase from its files.
- `phase=design-gate` + `_design.approved` → if HEAD differs from the marker's
  `base_commit`, stop and re-confirm the design with the human first. Otherwise load
  `_panel.json` into `state.panel`, set `state.iteration=1`, and set `state.phase="inner-loop"`.
- `phase=design-gate` without the marker → re-present the design + panel (step 4, Design gate) and wait.
- `phase=inner-loop` or `final-review` → continue that phase.
- `phase=create-pr` + `_create_pr.approved` → go to step 8 (Finish).
- `phase=create-pr` without the marker → per step 7 (Fulfillment), finish each missing artifact —
  question verification first, then fulfillment or followups — and re-present the gate.
- `phase=done` → the run is complete; report and stop.
- Otherwise, re-announce the stop being waited on and stop.

## Stage dispatch

Stages come from the validated config; there is no separate wrapper skill per engine. Only
triage and the iterate conversation run in the orchestrator itself. A single stage may be
configured model-only (`{"model": ...}` with no `use`): it runs the built-in role with the
Method line omitted. For stage key `K` with assignment `S`:

1. If `S.use` is set, resolve `role = registry.stage_roles[K]`, `engine =
   registry.uses[S.use].engine`, and `scope = registry.uses[S.use].scope`. With no `use`, use
   the built-in `role = registry.stage_roles[K]` and omit the Method line.
2. Resolve the model `M`: prefer the concrete pick recorded in `_panel.json` for this stage; else
   if `S.model` is `"auto"` or absent, pick from **Model tiering** below by role and triage tier;
   else use `S.model` verbatim.
3. Dispatch a subagent on model `M` with this whole instruction:

> You are filling shepherd's **{role}** stage. You run non-interactively: you cannot ask the
> human anything — record open questions in your output file instead. Communicate only through
> `.shepherd/` files. **Read:** {role.reads}. **Do NOT read:** {role.blind} — and keep
> recursive searches out of `.shepherd/` entirely (`rg --glob '!.shepherd/**'`,
> `grep -r --exclude-dir=.shepherd`); matching its content by accident is a blindness leak you
> must disclose. **Method:** follow `{engine}` — scoped as: {scope}. **Standing checks:**
> {role.standing} (reviewer and final-reviewer roles only; omit the line otherwise).
> **Write:** `{role.writes}` in this format: {role.format}.

`{role.standing}` is `templates/standing-checks.md`'s content, pasted verbatim regardless of what
the design emphasizes. `{role.format}` is the role's own `##` section of `templates/formats.md`,
except `architect`, whose format is `templates/design.md` pasted directly. All three paths resolve
relative to this skill's own directory — the same convention as the registry's `../_vendored/`
engine paths.

4. Completion signal: dispatch prefers blocking; when backgrounded, or fanning reviewers out in
   parallel, `{role.writes}` on disk is the completion signal everywhere it's dispatched. File
   presence is the floor; a terminal-marker format (a ledger verdict line, `VERDICT:`) isn't done
   until the file carries it too — a parallel round completes only once every reviewer's file is
   present **and** verdicted. An overwrite-in-place re-dispatch (architect revision, a
   `success_criteria` re-run) starts with the file already present: record its content hash in
   `_progress.md` at dispatch time and treat it done once a fresh hash differs — never mtime/size.
   Record every dispatch's start time in `_progress.md`; a `status unknown` report states the
   time since dispatch — file presence cannot distinguish still-working from dead, so elapsed
   time is what lets the human judge. Check output files on disk before any status claim, every
   turn, not only at resume; no idle-polling loop.

If the dispatched agent has no write access, it returns the artifact verbatim as its final
message and the orchestrator persists it to `{role.writes}` **unchanged** — a mechanical relay,
not authorship; the no-judgment-files rule is not violated. Note the relay in `_progress.md`.

| role | reads | do NOT read | writes |
|------|-------|-------------|--------|
| `verify` | `_user_request.md`, `1-triage.md`, codebase, referenced issue, current upstream sources for any claim resting on facts outside the repo | `2-design.md`, `3-success-criteria.md` | `_request_fact_check.md` |
| `explorer` | codebase | `.shepherd/` internals | `_codebase_map.md` |
| `architect` | `_user_request.md`, `1-triage.md`, `_request_fact_check.md`, `_codebase_map.md` if present, `_design_feedback.md` if present (settled human decisions — constraints, not suggestions), codebase; on a revision pass also its previous `2-design.md` | `3-success-criteria.md` | `2-design.md` |
| `success_criteria` | pasted content of the "What we're solving" and "How it will work" sections of `2-design.md`, plus `_user_request.md`, `1-triage.md`, and `_request_fact_check.md` (verified facts — real paths, real coverage gaps — so criteria reference reality instead of guessing; it contains no solution) — nothing else | the rest of `2-design.md` (the solution), `claim.md` | `3-success-criteria.md` |
| `implementer` | `2-design.md`, `3-success-criteria.md`, `_request_fact_check.md`, `_codebase_map.md` if present, all prior `iter-*/review-*.md` + `final-review-*.md` + `fulfillment.md` | — | source edits + `iter-N/claim.md` |
| `reviewer` | pasted content of `2-design.md`, `3-success-criteria.md`, `iter-N/diff.patch`, `iter-N/test-results.txt`, plus the repository itself (working tree, git history, read-only commands) — no other `.shepherd/` files | `claim.md`, peer reviewers' output | `iter-N/review-<use>.md` |
| `final_reviewer` | same as reviewer, but judging the post-fix integrated state: interactions with unchanged code, consumer/contract impact, doc/AGENTS staleness — not a second pass over the patch | `claim.md`, peer reviewers' output | `iter-N/final-review-<use>.md` |
| `fulfillment` | pasted content of `3-success-criteria.md`, `iter-N/diff.patch`, `iter-N/test-results.txt`, `iter-N/claim.md`, plus the working tree (may run the non-mutating check a criterion names) | `2-design.md` solution details, review files | `iter-N/fulfillment.md` |
| `followups` | pasted Scope split, all review files, accepted-open-finding decisions from `_progress.md`, `question-verification.md` if present, plus open issues and PRs (`gh issue list`, `gh pr list`) — cite an existing issue it duplicates or extends | `3-success-criteria.md`, `claim.md` | `iter-N/followups.md` |

### Model tiering

`"auto"` (the shipped default) lets the orchestrator pick a model per role and triage tier; an
explicit name (`opus`, `sonnet`, `haiku`) is used verbatim. Resolve `"auto"` as: `implementer` →
`haiku` (`sonnet` for `medium`/`large` — a subtle change is not transcription); `verify`,
`explorer`, `success_criteria`, `fulfillment`, `followups`, `reviewer` → `sonnet`; `architect` → `opus`
(`sonnet` for a revision pass — it folds feedback into an existing design without re-exploring);
`final_reviewer` → `opus` (`sonnet` for `trivial`/`small`). `sonnet` is the floor for review —
never `haiku`. Pre-gate stages (verify, explorer, architect, success_criteria) resolve `"auto"`
at dispatch time from this table. At step 4 (Design gate), record all picks in
`_panel.json`: the pre-gate ones as the record of what ran, the post-gate ones (implementer,
reviewers, final reviewers, fulfillment, followups) for the human to edit before approving.

## Procedure

### 1. Triage — `phase=triage`

Orchestrator-owned cheap product screen — no dispatch, no deep code reading; a quick skim is
fine. Write `.shepherd/1-triage.md` in about 12 lines:
- Problem
- Decision: `PROCEED | DEFER | DECLINE` — DEFER an under-specified request (no determinable
  problem or user-visible outcome) and put what's missing in Open questions; a clear problem
  with an open solution still proceeds — design settles solutions, not triage
- Complexity: `trivial | small | medium | large`
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

**No fast path.** The tiers scale the review panel, never the pipeline: a `trivial` run keeps
the full stage sequence — verify, design, criteria, both gates, review, fulfillment. If the
ceremony looks disproportionate, note it in the triage overview (the human may prefer to make
the change directly, outside shepherd) — but never skip stages.

**Triage has no gate.** Present the overview in chat and continue. Only when the decision is
`DEFER or DECLINE`, stop and recommend against proceeding, but let the human decide. Then set
`state.phase="verify"`.

### 2. Verify — `phase=verify`

Run the `verify` stage on every run — never skipped by tier. On a fresh run whose archived
predecessor targets the same repo and base commit, verify may run in delta mode: re-check only
claims whose subject changed (new decisions, moved code, upstream PR state), re-affirming the
rest against the archived ledger with a citation — narrowed, never skipped. It builds the
authoritative claim ledger in `_request_fact_check.md`: every claim in the request tagged
`VALID | STALE | LIKELY-FIXED | UNVERIFIABLE` with evidence (running an existing test to verify
a claim is fine — remove artifacts it leaves). If core claims are stale or already fixed,
present the verdict with a recommendation and stop; the human decides.
**If the ledger invalidates the requested mechanism but not the goal** (the fix as specified
cannot work, e.g. an API/SDK constraint, but the problem is real), don't silently design around
it: present the constraint and viable options with one recommendation, wait for the human's
pick, and record it verbatim in `_design_feedback.md` so the architect treats it as settled.
Otherwise set `state.phase="design"`.

### 3. Design: subagents draft, then iterate with the human — `phase=design`

**Draft.**
- For `medium`/`large` complexity, first dispatch the `explorer` role (the
  `shepherd-code-explorer` agent when available) to write `_codebase_map.md`; architect and
  implementer reuse it. Skip for `trivial`/`small`, or when the verify fact-check already maps
  the files and the change is mechanical or localized (deletion, rename, inlining) — note why
  in `_progress.md`.
- Dispatch the `architect` stage to write `.shepherd/2-design.md`, following `templates/design.md`
  as its format. A non-empty Prerequisite refactor is an explicit gate decision: surface it to
  the human and proceed only on their confirmed choice — deliver the prerequisite first, or
  (only on the human's explicit pick, never as the default) fold it in.
- Dispatch the `success_criteria` stage: paste it ONLY the two product sections of the design
  (plus request, triage, and the fact-check) and have it write `.shepherd/3-success-criteria.md`. It defines
  "done" independently — the architect never reads it, and it never sees the solution.

**Iterate — the conversation is the orchestrator's; every rewrite is a subagent's.**
- Present the FULL `2-design.md` + `3-success-criteria.md` (see "Keep the human in the loop").
- Grill decisions one question at a time (wait for each answer): options + your recommended
  answer; product questions first, implementation after. Look up facts yourself — including the
  repo's conventions doc for any naming/signature/parameter question; a convention that settles
  the question is a fact, not a human decision. Only decisions go to the human. Walk
  dependencies in order — if Open questions miss a real fork, ask it.
  YAGNI — cut speculative scope.
- **Batch a round of answers**, then append them verbatim to `_design_feedback.md`
  (append-only; the orchestrator writes only this file, never the design or criteria).
- Re-run the `architect` as a **revision pass** — it reads its previous `2-design.md` +
  `_design_feedback.md` and revises; it does not re-explore. Re-run `success_criteria` only
  when the product sections changed.
- For `trivial` complexity, don't interrogate: present the drafts and ask for objections — with
  none, the recommended answers stand as decisions and the gate proceeds with Open questions
  intact.
- Otherwise done when **Open questions is empty and the human says they're happy**; then
  step 4 (Design gate).

### 4. Design gate — `phase=design-gate`

Do not edit source files until `.shepherd/_design.approved` exists. Set
`state.phase="design-gate"`.

Propose the per-run review panel from the configured roster: start from the triage tier, adjust
for the actual design scope, and pick in config order unless the design's risk calls for a
specific reviewer. Two or more reviewers must differ in lens (e.g. diff-correctness vs
adversarial vs live-probe vs contract/consumer). At every human gate, present the panel with a
one-line lens-fit assessment per reviewer stating whether the lens is live for this design or
structurally muted (e.g. a complexity/deletion lens on a behavior-preserving move that forbids
cuts), and invite roster/model changes; the orchestrator never edits the panel itself, and a panel
change folds into the gate, not a new stop. **Resolve every `"auto"` model to a concrete name** (see Model
tiering) at the settled tier — inline on each reviewer, and in a `models` map for the single
stages (only those whose config model is `"auto"`; an explicit model keeps its name). Write
`.shepherd/_panel.json`:

```json
{ "tier": "small", "reason": "localized low-risk change",
  "models": { "verify": "sonnet", "architect": "opus", "implementer": "haiku",
              "success_criteria": "sonnet", "fulfillment": "sonnet", "followups": "sonnet" },
  "reviewers": [{ "use": "staff-review", "model": "sonnet" }],
  "final_reviewers": [{ "use": "thermonuclear", "model": "sonnet" }],
  "inner_iterations": 2, "final_review_rounds": 1 }
```

The approved panel must be a subset of the configured roster.

Surface the FULL `2-design.md` + `3-success-criteria.md` + `_panel.json` to the human, then
**stop for the human's decision.** Approval covers all three. Two outcomes, on disk:

**Approve.** A clear "yes/approve" in chat, or `/shepherd-approve-design`. Copy the panel into
`state.panel`, set `state.phase="inner-loop"` and `state.iteration=1`, and write
`_design.approved` (the approval skill does exactly this).

**Revise.** Any change request: do NOT write `_design.approved` — back to the step 3 (Design)
iterate loop (feedback file + revision passes), re-present, wait. As many rounds as the human wants.

**Plan mode (any agent that has one — Claude Code, Cursor, Codex…).** With `plan_mode_gate=true`
and plan tools available (`EnterPlanMode`/`ExitPlanMode`), mirror the FULL design + criteria +
panel into the plan body (not a summary): accepting it IS Approve; rejecting or editing it IS
Revise. On plan-tool error or unavailability, fall back to chat (paste everything there).

**Never self-approve.** Never infer approval from a plan-tool error, a plan-mode transition, or
a "continue" message (see Hard rules); resume only once `_design.approved` exists.

### 5. Inner loop — `phase=inner-loop`

Use `state.panel`, not the raw roster; validate it against config. If absent (older run), fall
back to the full roster and limits and record that in `_progress.md`.

For each iteration `N`:
1. Set `state.phase="inner-loop"` and `state.iteration=N`; create `.shepherd/iter-N/`.
2. On iteration 1, before the first source edit, run `oracle.commands` once on the untouched
   tree and record its baseline metrics (test/file counts, pass/skip counts, warnings, rough
   duration) in `iter-1/baseline.txt` — later green runs are judged against these, not in
   isolation. Then, on every iteration, run the `implementer` stage: it applies `2-design.md`
   + `3-success-criteria.md`, addresses every prior finding, and writes `iter-N/claim.md`.
3. Run `oracle.commands`, capturing output to `iter-N/test-results.txt`; if empty, record and
   run the smallest credible inferred fallback. Use finite, deterministic,
   non-mutating commands; avoid `dev`, `start`, `watch`, `lint:fix`, `format`, `clean`,
   inspectors, and eval workflows. If no credible command exists, the oracle is not green.
   Green alone is not green: compare against `iter-1/baseline.txt` — an unexplained metric
   delta (test or file count, skips, new warnings, order-of-magnitude duration shift) fails the
   oracle even when all passes (wrong-but-green happens, e.g. silently double-running the
   suite). Expected deltas (e.g. tests the design adds) must be named in `claim.md`.
4. Write `diff.patch` via `git diff <base_commit>` — the HEAD recorded in
   `_design.approved` at design approval, i.e. before any source edit — so the diff always
   spans the run's whole work, commits included. An untracked new file is silent there —
   include it via `git diff --no-index /dev/null <file>`, same form for any per-file check.
5. Dispatch panel reviewers in parallel, each given the pasted content of `2-design.md`,
   `3-success-criteria.md`, `diff.patch`, and `test-results.txt`, plus read access to the
   repository. They stay blind to `claim.md` and peer reviews.
6. Converge when the oracle is green and baseline-consistent and every reviewer verdict is PASS
   — every finding gets fixed, whatever its severity: nits too (`pre-existing`-tagged findings
   skip the loop and route to the followups ledger at step 7 (Fulfillment + create-PR confirm));
   the implementer never skips or defers one. The other exception is the human's: a finding
   fixable only by changing the approved design or criteria (see Hard rules). Decay rule: when
   a round's open findings are all doc/comment-only (no behavior or signature change), show the
   exact list and propose accepting them as `pr-note` items instead of another fix round —
   comment-polish rounds churn new wrong comments. A fix reply iterates. An accept reply records
   the named findings and decision in `_progress.md`; for routing only, those findings no longer
   block final review or step 7, and followups must carry them verbatim. The same rule applies in
   final review; any new or unaccepted finding still blocks. Otherwise iterate until
   `inner_iterations`; then stop and present a findings table (fixed / open), the oracle
   status, and the options: extend the limit, accept with open findings recorded, or abandon.
   On abandon, record the decision in `_progress.md` and set `state.phase="done"`; leave the
   working-tree edits for the human to keep or discard — never revert them yourself.

When converged, including convergence with only human-accepted open findings, set
`state.phase="final-review"` if the panel has final reviewers; otherwise `state.phase="create-pr"`.

### 6. Final review — `phase=final-review`

Run panel `final_reviewers` in parallel (same pasted-content rule, plus working-tree access).
Any unaccepted finding triggers a targeted implementer fix and a re-run of the final reviewers
(and the regular reviewers too when the fix is broad), staying in `phase="final-review"`, bounded by
`final_review_rounds`. Each fix round advances to the next free `iter-N` (claim, oracle run,
diff, review files) — never overwrite an earlier round's files. When clean by the
step 5 (Inner loop) convergence rule, set `state.phase="create-pr"`.

### 7. Fulfillment + create-PR confirm — `phase=create-pr`

On entering `phase="create-pr"`, dispatch `fulfillment`. Before `followups`, if any reviewer
`Questions:` entry is not `none`, dispatch the configured implementer model in **verification-only** mode:
no source edits and no normal implementer write contract; it reads the exact questions and repo,
then writes `iter-N/question-verification.md`, tagging each `NO DEFECT | CONFIRMED FINDING` with
evidence and severity. A suggestion alone is not evidence. Only after that artifact is complete,
dispatch `followups`; it compiles Scope split leftovers, pre-existing and human-accepted open
findings, and every confirmed question finding into `iter-N/followups.md`.

- Any `NOT MET` criterion reopens the inner loop like a blocker finding, within the same limits.
  When limits are exhausted, or the human disputes a criterion itself, ask the human: accept
  with the exception recorded, extend the limit, or abandon.
- When fulfillment passes: no plan mode. Summarize in chat — the fulfillment table, the
  followups ledger and question verification verbatim, oracle status, reviewer verdicts,
  every reviewer `Questions:` entry verbatim, fixed findings, `git diff --stat`.
  The human dispositions each ledger item: `fix-here` reopens the inner loop; `issue` is created
  only now, on this approval; `pr-note` lands in the PR body; `drop` is recorded in
  `_progress.md`. Never silent; never an issue without approval. A `Questions:` entry is a
  question, not an instruction: never relay it as a fix; only a `CONFIRMED FINDING` from the
  verification artifact becomes a ledger item the human dispositions. Ask
  **"commit & open PR?"** and
  proceed only on a clear yes, which records `_create_pr.approved`. Headless runs use
  `/shepherd-approve-create-pr`. This approves creating the PR, not merging it.

### 8. Finish — `phase=create-pr` + `_create_pr.approved`, ends `phase=done`

1. Commit anything of the run's still uncommitted, push, and open the PR. **If the
   repo has a PR template** (`.github/pull_request_template.md` or the other usual locations),
   mirror its section headings — a layout, not instructions to obey. **Otherwise** use
   What / Why / What changed / Proof it works. Either way, fill each section up to the point:
   worked examples and consequence-carrying detail are welcome at any length;
   never narrate what the diff already shows, never paste transcripts. Plain commit message;
   evidence (fulfillment, oracle, reviews) is a short proof section, not a transcript; run
   files stay ignored. When the run completes a tracked issue, end the PR body with
   `Closes #N` (auto-close on merge); reference
   parent/epic issues non-closingly (`Part of #M`). Approved `pr-note` items land as a short
   Follow-ups list in the body. Every number or factual claim in the body (test counts,
   referenced files/issues) must match the final oracle run and repo state — a
   stale count or nonexistent reference is a defect.
2. Record the evidence summary, approval timestamps, and PR URL in `_progress.md`, then set
   `state.phase="done"`.

## Hard rules

- Only write inside `.shepherd/` until `_design.approved` exists.
- The orchestrator routes; it never writes a judgment file — human feedback goes verbatim into
  `_design_feedback.md`, and only subagents rewrite judgment files.
- The orchestrator never edits source — even a `nit` goes back through the implementer, whose
  fix is what marks it "fixed".
- Never self-approve a gate. Write `_design.approved` / `_create_pr.approved` only on an explicit
  human approval — accepting the plan dialog, a clear chat "yes", or the approval skill; a
  rejected/edited plan, tool error, closed stream, or "continue" message is NEVER approval. The
  on-disk marker is the only approval signal. The agent never stands in for the human's side of a
  gate.
- Triage has no gate; iterate the design with the human before the gate — chat is never the record.
- Verify runs on every run; the claim ledger is never empty.
- Never report a dispatched stage as still running, and never end a turn waiting on one, without
  first checking its output file on disk — present and complete means done: read it and proceed.
  An absent output file tells you only that the stage isn't done — not whether it's still
  working or has died: report `status unknown; output not present` and offer to wait or
  re-dispatch. Never infer "still running" or "stalled" from turn count or a human check-in.
- Blindness per the role table's "do NOT read" column; judgment files are pasted, never granted;
  the repository itself is never blinded.
- No git rules beyond the gate: `_create_pr.approved` gates opening the PR, nothing else;
  mid-run commits are normal — the reviewed diff stays anchored at `base_commit`.
- shepherd never stages or commits `.shepherd/` paths; run data stays ignored via the run's
  `.shepherd/.gitignore`.
- Keep design focused: major changes only, never an exhaustive file list.
- Surface human-facing artifacts into the human's channel (see Keep the human in the loop).
- The panel, not the roster, drives the run; never run a `use` not in config.
- Trust the oracle and its baseline over model self-reports (step 5.3). Never weaken/delete tests.
- Converge on zero open findings (step 5.6). No PR without fulfillment: every criterion `MET`,
  or the human explicitly accepts the exception.
- A finding fixable only by changing the approved `2-design.md` / `3-success-criteria.md` is the
  human's call — surface it at the gate; never edit an approved artifact to silence a finding.
- A design may downgrade severity or route a finding to follow-up; it
  never instructs reviewers not to report a class of findings — adjacent pre-existing defects
  are tagged, surfaced at the create-PR gate, and issues for them are created only on human approval.
- Commit/PR text: plain, PR-template-following, no obvious-from-the-diff narration (step 8, Finish).
