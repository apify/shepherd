---
name: devforge
description: Run a task through the gated coding loop — validate, explore, architect, STOP for human design approval, then implement ↔ review ↔ test, STOP for human pre-merge approval, then merge. Use this to drive any non-trivial change through controlled, human-gated steps where the implementer and reviewer stay independent and coordinate only through files. Invoke as /devforge <task>.
argument-hint: "<task description>"
---

# devforge — gated loop orchestrator

You are the **orchestrator** (the only conductor). You drive the phases and mediate
all hand-offs **through files under `.devforge/`** — the implementer and reviewer
never see each other's context. Two human gates stand between phases: you cannot edit
source before the design is approved, and cannot push/merge before merge is approved.

> **Working files live in `.devforge/` at the repo root — never under `.claude/`.**
> `.claude/skills/` is the tool (config); `.devforge/` is this run's data.

> **Config-driven slots.** Each phase is a *slot* filled by a vendored skill named in
> `.devforge/config.json`. There are **no per-skill adapters** — one universal dispatch
> contract (see *Slot dispatch*) drives every engine, parameterized by
> `.devforge/registry.json`. The default slots: validate ← `brainstorming`, architect ←
> `writing-plans`, implementer ← `feature-dev`, reviewers ← `staff-review` (parallel,
> every iteration — kept lean so the loop is fast), final_reviewers ← `thermonuclear` +
> `code-review` (parallel, after convergence). Every engine is **vendored in-repo**
> (`.claude/skills/_vendored/`) —
> nothing needs installing. See `docs/devforge-config.md` for the catalog. The oracle
> (tests/lint) is **not** a slot.

## File contract (`.devforge/`)

| File | Writer | Reader | Committed? |
|------|--------|--------|-----------|
| `config.json` | orchestrator (default) / human | orchestrator | yes |
| `config.local.json` | human (optional) | orchestrator | no (gitignored) |
| `registry.json` | tool | orchestrator | yes |
| `task.md` | validate slot | all | yes |
| `validation.md` | validate slot | human, all | yes |
| `design.md` | architect slot | impl, reviewers | yes |
| `design.approved` | **human** `/devforge-approve-design` | gate check | yes |
| `state.json` | orchestrator | resume | yes |
| `progress.md` | orchestrator | human | yes |
| `iter-N/claim.md` | implementer | **human only** | yes |
| `iter-N/diff.patch` | orchestrator (`git diff`) | reviewers | no (gitignored) |
| `iter-N/test-results.txt` | orchestrator (oracle) | reviewers | no (gitignored) |
| `iter-N/review-<use>.md` | each per-iteration reviewer | impl (next iter), orchestrator | yes |
| `iter-N/final-review-<use>.md` | each final reviewer | impl (next iter), orchestrator | yes |
| `merge.approved` | **human** `/devforge-approve-merge` | gate check | yes |

`<use>` is the slot value's `use` name (e.g. `review-staff-review.md`,
`review-thermonuclear.md`, `final-review-code-review.md`).

**Independence rule:** every reviewer reads `task.md`, `design.md`, `iter-N/diff.patch`,
`iter-N/test-results.txt` — **never `claim.md`, and never another reviewer's output.**
Each judges reality against the approved spec, blind to the implementer's narrative and
to its peers.

## Procedure

### 0. Setup or resume
- `mkdir -p .devforge`.
- **Resume check (do this first):** if `.devforge/state.json` already exists, READ it
  and **continue from where it left off — do not restart:**
  - If invoked with a `<task>` that differs from `.devforge/task.md`, ask the human
    whether to continue the existing run or start fresh (starting fresh clears `.devforge/`).
  - `phase=design-gate` and `.devforge/design.approved` now exists → go to the inner
    loop (step 5).
  - `phase` is in the inner loop → continue at the current `iteration`.
  - `phase=pre-merge-gate` and `.devforge/merge.approved` exists → go to finish (step 7).
  - Otherwise, re-announce the gate you're waiting on.
- **Fresh start** (no `state.json`): write `.devforge/task.md` = the `<task>` argument;
  initialize `.devforge/state.json` =
  `{"phase":"validate","iteration":0,"head_sha":"<git rev-parse HEAD>"}`; start
  `.devforge/progress.md` with a header and a timestamped "loop started" line.
- **Load + validate config (every start, fresh or resume):**
  - If `.devforge/config.json` is absent, write the committed default (the schema in
    `config.schema.json`); tell the human it was created and is editable.
  - If `.devforge/config.local.json` exists, **shallow-merge** it over `config.json`
    (per-slot overrides win) — use it, don't rewrite `config.json`.
  - **Validate** the resolved config against `.devforge/registry.json` (the rules
    `scripts/validate_config.py` encodes): every slot present; each `use` exists and its
    slot's role (`registry.slot_roles[slot]`) is in that use's `roles`; no duplicate
    `use` within `reviewers` / `final_reviewers`. On any error, **STOP** and print the
    exact problem — do not run with an invalid config.
  - Read `limits.inner_iterations` (default 3), `limits.final_review_rounds` (default
    2), and `plan_mode_gate` (default true). Record the resolved config in
    `progress.md`.

### Slot dispatch (one universal contract)

There are **no per-skill adapter files** — every slot runs through this one contract,
parameterized by data in `.devforge/registry.json`. To run slot **S** with value
`{ "use": U, "model": M }`:

1. Resolve `role = registry.slot_roles[S]`, and `engine = registry.uses[U].engine`,
   `scope = registry.uses[U].scope`.
2. Dispatch a **subagent on model M** whose entire instruction is the filled template:

   > You are filling devforge's **{role}** slot. Communicate only through `.devforge/`
   > files. **Read:** {role.reads}. **Do NOT read:** {role.blind}. **Method:** follow
   > `{engine}` — scoped as: {scope}. **Write:** `{role.writes}` in this format:
   > {role.format}.

**Role contract** (the `{role.*}` values above):

| role | reads | do NOT read | writes | format |
|------|-------|-------------|--------|--------|
| `validate` | the `<task>`/issue, codebase, `gh` | — | `task.md` + `validation.md` | claim ledger + one-line verdict |
| `architect` | `task.md`, `validation.md`, codebase | — | `design.md` | approach · files to change · test strategy (oracle) · risks |
| `implementer` | `design.md`, all prior `iter-*/review-*.md` + `final-review-*.md` | — | source edits + `iter-N/claim.md` | what done / skipped + specific reason / evidence — **never edit or delete tests, and never edit the spec (`task.md` / `validation.md` / `design.md`)** |
| `reviewer` | `task.md`, `design.md`, `iter-N/diff.patch`, `iter-N/test-results.txt` | `claim.md`, peer reviewers' output | `iter-N/review-<use>.md` | first line `VERDICT: PASS\|FAIL`, then severity-tagged findings (blocker/major/minor/nit). **`PASS` only if there are ZERO findings of ANY severity — a single nit means `FAIL`. Never PASS with findings listed.** |
| `final_reviewer` | `task.md`, `design.md`, `iter-N/diff.patch`, working tree | `claim.md`, peer reviewers' output | `iter-N/final-review-<use>.md` | first line `VERDICT: PASS\|FAIL`, then severity-tagged findings. **`PASS` only if there are ZERO findings of ANY severity (nit included); otherwise `FAIL`.** |

`<use>` in a filename is the value's `use` name (e.g. `review-staff-review.md`).

> **Approval auto-continues.** At each gate the human runs the human-only approval skill,
> which records the marker and then **hands straight back to `/devforge`** — the loop
> continues without the human re-invoking anything. Re-running `/devforge` also resumes
> from `state.json` (the fallback if a run is ever interrupted); it never restarts a run
> already in progress.

### 1. Validate — incl. claim & staleness check
**Run the `validate` slot** (dispatch per *Slot dispatch* — default `brainstorming`).
Confirm the task is specific enough to act on **and that its premises are still true.**
The steps below are the contract the slot fulfils.

**If the task references a GitHub issue (number/URL) or cites specific code locations,**
run a staleness check *before designing* — issues drift from the code (files move,
symbols get renamed, the bug may already be fixed):
1. **Fetch + timestamp:** `gh issue view <n> --json title,body,createdAt,comments,labels`.
   Record `createdAt` as the staleness baseline.
2. **Claim ledger:** from the body + comments, list code refs (paths, `symbols`,
   `file:line`, permalinks that pin a SHA), behavioral claims, causal claims
   ("introduced by #N"), and repro steps.
3. **Verify each against current HEAD:**
   - References: does the file/symbol still exist? `grep`/Read it; if a permalink
     pinned a SHA, check whether the file moved/changed since. Mark
     resolved / moved→<new> / gone.
   - Drift since filing: `git log --since="<createdAt>" --oneline -- <paths>` and
     `git log -S"<symbol>"` to see if the area changed after the issue was filed.
   - Already-fixed: `git log --grep="#<n>"` and merged PRs referencing the issue.
4. **Write `.devforge/validation.md`:** each claim → `VALID | STALE(→corrected ref) |
   LIKELY-FIXED | UNVERIFIABLE` with evidence (HEAD `file:line`, commit SHAs), plus a
   one-line verdict.
5. **Calibrated stop:** if core claims are STALE or it looks LIKELY-FIXED, STOP and
   surface to the human with a recommendation (re-scope / close as fixed / proceed with
   corrected references) before designing. Otherwise write `task.md` using the
   **corrected, current** references — never the stale ones.

Then restate the task, list any genuine ambiguities, and set `state.phase="explore"`.

### 2. Explore  *(orchestrator-owned — not a slot)*
Read the relevant parts of the codebase to ground the design. Note key files/patterns
in `progress.md`. Set `state.phase="architect"`.

### 3. Architect
**Run the `architect` slot** (default `writing-plans`, dispatched per *Slot dispatch*).
It writes `.devforge/design.md`: the approach, the specific files to change, the test
strategy (the oracle), and risks. This is the artifact reviewed at the design gate.
Set `state.phase="design-gate"`.

### 4. DESIGN GATE  — STOP
- **Self-enforce:** do **not** edit any source file until `.devforge/design.approved`
  exists. This gate is enforced by you following this skill — there are no hooks.
- **Plan-mode front-end (when `plan_mode_gate` is true AND running interactively in the
  CLI) — preferred, because reviewing raw markdown is hard:** show `design.md` in the
  native plan UI so the human gets a rendered, scrollable plan with approve/reject
  buttons. The design *is* the plan. Mechanics — `ExitPlanMode` only works **inside**
  plan mode, so you must enter it first:
  1. Call **`EnterPlanMode`** (the human consents to entering plan mode).
  2. **Mirror** the full contents of `.devforge/design.md` into the plan file named in
     the plan-mode system message (copy it verbatim — this is NOT editing the design,
     just rendering it; `design.md` remains the source of truth).
  3. Call **`ExitPlanMode`** — the human reviews the rendered design and approves or
     rejects natively.
  4. **On approval:** write `.devforge/design.approved` yourself and continue the loop.
     **On rejection / change requests:** re-run the **architect slot** to revise
     `design.md` (never hand-edit it yourself — see Rules), then re-present from step 1.
- **Otherwise** (`plan_mode_gate` false, or running on web/headless, or resuming, or if
  `EnterPlanMode`/`ExitPlanMode` is unavailable): tell the human to review
  `.devforge/design.md`, then run **`/devforge-approve-design`** — it records the marker
  and continues automatically. Then stop and wait.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/design.approved` exists.

### 5. Inner loop  (implement → oracle → reviewers), iteration N = 1, 2, …
For each iteration, make a fresh `.devforge/iter-N/` directory, then:
- **Implement** — run the `implementer` slot (default `feature-dev`, dispatched per
  *Slot dispatch*) on `slots.implementer.model`. It applies `design.md` and
  **addresses every finding from all of the prior iteration's `review-*.md` /
  `final-review-*.md` — blockers AND nits** (smallest proportionate fix; skip only with a
  specific recorded reason — "out of scope" alone is not a reason). It must **never edit
  or delete tests to pass**, and writes `iter-N/claim.md`.
- **Oracle** (orchestrator, not a slot): run the project's tests/lint; redirect output
  to `iter-N/test-results.txt`. Produce the ground-truth diff:
  `git add -A && git diff --cached -U10 > iter-N/diff.patch` (then unstage if needed).
- **Reviewers (parallel)** — dispatch **one subagent per entry in `reviewers`**
  concurrently (per *Slot dispatch*), each **blind to `claim.md` and to the other
  reviewers**. Each writes `iter-N/review-<use>.md` (first line `VERDICT: PASS|FAIL` —
  `PASS` only with **zero findings of any severity, nits included**; otherwise `FAIL`).
  Default: `staff-review` (correctness) only — the per-iteration set is kept lean for
  speed; maintainability (`thermonuclear`) runs once at final review (5b).
- **Decide**: converged only when the oracle is green **and every finding across ALL
  `iter-N/review-*.md` is resolved** — fixed or carrying an explicit skip-justification,
  **nits included**. Because a reviewer emits `FAIL` whenever any finding remains, a
  `PASS` is a genuine all-clear; you (the orchestrator, the only one who sees `claim.md`)
  may converge over a `FAIL` **only** by recording a specific, sound skip-justification
  for each remaining finding. Where two reviewers conflict (e.g. a structural restructure
  vs a minimal-diff preference), pick the resolution and record the reconciliation for
  the next `claim.md`. If the oracle is red or findings remain, feed the reviews into
  iteration N+1. After `inner_iterations` (default 3) without converging — or a genuine
  blocker the design can't resolve — STOP and escalate. Append a line to `progress.md`
  each iteration.

### 5b. Final review  (after the inner loop converges)
If `final_reviewers` is non-empty, dispatch **one subagent per entry** in parallel (per
*Slot dispatch*), blind to `claim.md` and to each other, each writing
`iter-N/final-review-<use>.md` (same verdict rule: `PASS` only with zero findings of any
severity). Default: `thermonuclear` (maintainability) **and** `code-review` (bug/quality
pass) — these heavier reviews run once here rather than every iteration, so the inner
loop stays fast.
- **If any final review has actionable findings**, they reopen the inner loop: run a
  fresh implement → oracle → reviewers iteration to resolve them, then re-run the final
  reviewers. This reopen-cycle is bounded by `final_review_rounds` (default 2); exceeding
  it STOPs and escalates.
- **If a final review flags a divergence between `design.md` and the implemented code**
  (the design drifted from what was built), do **not** edit `design.md` to match. Surface
  it to the human at the pre-merge gate with both options (update the design, or change
  the code) and let them decide — see Rules.
- **When all final reviews are clean** (or `final_reviewers` is empty), proceed to the
  pre-merge gate.

### 6. PRE-MERGE GATE — STOP
- **Self-enforce:** do not push / merge / open a PR until `.devforge/merge.approved`
  exists. Summarize the evidence for the human — the change, the oracle status, and
  confirm **every finding from all reviewers (per-iteration AND final) is resolved**
  (fixed or justified-skip, nits included; no "noted but unhandled"). Present the diff
  clearly: a `git diff --stat` summary plus the actual hunks, so the human reviews the
  real change. Then tell them the exact next step: review `.devforge/`, then run
  **`/devforge-approve-merge`** — it records approval and continues to commit + PR
  automatically. Then stop and wait.
- (Fallback) if interrupted, re-running `/devforge` resumes via step 0 once
  `.devforge/merge.approved` exists.

### 7. Finish
Commit, then push / open a PR as appropriate. Record the outcome in `progress.md`.

## Rules
- Only write inside `.devforge/` until `design.approved` exists.
- **The approved spec — `task.md`, `validation.md`, and `design.md` — is frozen, and
  each is written ONLY by its owning slot** (`task.md` + `validation.md` by the validate
  slot; `design.md` by the architect slot). Once approved (`task.md`/`validation.md` when
  the loop proceeds past validate; `design.md` once `design.approved` exists), **never
  hand-edit any of them** — not to fix a typo, not to reconcile a later finding, not for
  any reason — without **explicit human confirmation**. In particular the **implementer
  must never touch them**: the code conforms to the spec, never the spec to the code.
  They are what the human reviewed at the gate; silently changing them lets the
  implementer move the goalposts and breaks the gate. If a later review reveals the code
  diverged from the approved design (or that the task/validation was wrong), surface the
  divergence to the human and let them choose — update the artifact via its owning slot,
  or change the code — do not pick for them by editing the doc. Mirroring `design.md`
  into the plan file for the plan-mode gate is not an edit (it is a verbatim copy).
- Trust the oracle (tests/lint), not self-reports. Never weaken or delete tests.
- **A reviewer's `VERDICT: PASS` means zero findings of any severity (nits included).**
  Any finding — blocker, major, minor, or nit — is `FAIL`. Never accept a `PASS` that
  still lists findings.
- **Resolve every finding from every reviewer — per-iteration and final — before the
  pre-merge gate, including nits.** Each is fixed or skipped with a specific recorded
  reason; never carry an unhandled finding to the gate.
- Keep every reviewer blind to `claim.md` and to the other reviewers. Keep yourself the
  only component that sees every file.
- Use only the slots in the validated config. Never substitute an installed plugin for a
  vendored engine unless `config.local.json` explicitly says so.
