# shepherd

shepherd is a Claude Code plugin for running coding work through a controlled,
human-gated loop. `/shepherd <task>` separates product triage, request verification,
design, success criteria, implementation, review, tests, fulfillment, and create-PR
approval into durable files under `.shepherd/`.

<p align="center">
  <img src="docs/assets/shepherd-overview.svg" width="920"
       alt="shepherd overview — the orchestrator routes, subagents judge, and files are the only handoff; the run flows from /shepherd <task> through triage, verify, design, and human iteration to the design gate, then an implement/review loop, final reviewers, and a fulfillment check, ending at a create-PR confirm before commit.">
</p>

The core principle: **the orchestrator routes; subagents judge; files are the only
handoff.** Every judgment — the claim ledger, the design, the success criteria, each
review, the fulfillment check — is a subagent writing one file with a narrow read set.
The orchestrator never authors a judgment file; it dispatches, shows you the results,
and records your feedback verbatim.

Three properties matter most:

- **The design is shaped with you.** After a cheap triage and an always-on fact check,
  subagents draft a product-first design and independent success criteria. shepherd then
  iterates with you in chat — one question at a time, each with a recommended answer,
  product questions first. Your answers go verbatim into a feedback file and the
  architect revises its own draft in a cheap revision pass. The design gate becomes a
  quick confirmation of something you already shaped.
- **Judgments are blind.** The architect never sees the success criteria; the criteria
  author never sees the proposed solution; reviewers get pasted design + criteria + diff
  + tests plus read access to the repository itself — never the implementer's claims or
  each other's findings. Blindness applies to judgments, never to ground truth.
- **"Done" is checked, not claimed.** Before the create-PR confirm, a fulfillment
  subagent judges the diff and tests against the success criteria written before the
  solution existed — `MET | NOT MET` per criterion, with evidence.

## Flow

The diagram above is the map; the block below is the same run as a quick text
reference, and the collapsible holds a Mermaid version for editing.

<details>
<summary>Mermaid flow diagram</summary>

```mermaid
flowchart TD
    Start["/shepherd <task>"] --> Triage["Triage (orchestrator)<br/>PROCEED / DEFER / DECLINE"]
    Triage -->|PROCEED| Verify["Verify (subagent, always)<br/>claim ledger"]
    Triage -->|DEFER or DECLINE| Stop["Stop with recommendation"]
    Verify -->|claims hold| Draft["Architect drafts 2-design.md<br/>then success criteria (blind)"]
    Verify -->|stale / already fixed| Stop
    Draft --> Iterate["Iterate with the human<br/>feedback file + revision passes"]
    Iterate --> Gate{"Design gate<br/>approve design + criteria + panel"}
    Gate -->|approved| ReviewOnly{"Review-only task?"}
    Gate -->|revise| Iterate
    ReviewOnly -->|yes| ExistingDiff["Build diff from branch/PR"]
    ExistingDiff --> ReviewPanel["Run approved reviewers"]
    ReviewPanel --> Findings["Report findings"]
    ReviewOnly -->|no| Implement["Implement approved design"]
    Implement --> Oracle["Run oracle commands"]
    Oracle --> Reviewers["Run blind reviewers"]
    Reviewers --> Clean{"Oracle green,<br/>all findings fixed?"}
    Clean -->|no| Implement
    Clean -->|yes| FinalReview["Final reviewers (if configured)"]
    FinalReview -->|findings| Implement
    FinalReview -->|clean| Fulfillment["Fulfillment check<br/>criteria vs reality"]
    Fulfillment -->|NOT MET| Implement
    Fulfillment -->|MET| CreatePrConfirm{"Create-PR confirm<br/>commit & open PR?"}
    CreatePrConfirm -->|yes| Finish["Commit / push / PR"]
    CreatePrConfirm -->|no| Hold["Wait"]
```

</details>

```text
/shepherd <task>
  triage (orchestrator product screen; no gate, stops only on DEFER/DECLINE)
  verify (subagent, always)      -> claim ledger; stops if the request is stale
  architect + success criteria   -> blind drafts
  iterate with the human         -> feedback file + revision passes
                                 -> DESIGN GATE: approve design + criteria + panel
  implement -> oracle -> blind reviewers -> final reviewers
                                    (loop until every finding is fixed)
  fulfillment (subagent)         -> every criterion MET, or reopen / ask
  create-PR confirm (plain chat) -> commit / PR
```

There are two human gates: the **design gate** before source edits and the **create-PR
confirm** before any git write. Triage is deliberately cheap and continues unless it
recommends `DEFER` or `DECLINE`.

At the design gate, shepherd writes `_panel.json` so each run gets the right reviewer
set for its risk: a small bug can use a small panel, while a core or public-contract
change can use the full roster. The panel also pins the model for each stage — every
`auto` is resolved to a concrete model by role and complexity tier and shown to you to
bump up or down before approving. Approval covers the design, the success criteria, and
the panel together.

Convergence is zero-findings: every finding gets fixed, whatever its severity — nits too;
nothing is skipped and nothing waits on your nudge. You only hear about open findings if
the iteration limits run out first. No PR happens without fulfillment: every criterion
`MET`, or you explicitly accept the recorded exception.

On web/mobile/remote sessions the human sees only the chat stream, so shepherd surfaces
everything into the conversation: the full `2-design.md` and `3-success-criteria.md` are
pasted or rendered as an Artifact (not just linked on disk), and run progress shows as a
one-line status at each phase transition — never assume the human can open `.shepherd/`
files or type a slash-command.

Review-only work is first-class. For a task like "review PR/branch X", shepherd runs
triage, verify, design (the review scope), the approved review panel against the
existing diff, and a findings summary. It only enters the implementation loop if you ask
it to fix those findings.

## Commands

- `/shepherd <task>` starts a new run.
- `/shepherd` resumes the run recorded in `.shepherd/_state.json`.
- `/shepherd-approve-design` is the human-only command for approving
  `.shepherd/2-design.md`, `.shepherd/3-success-criteria.md`, and `.shepherd/_panel.json`
  (records the panel and writes the marker).
- `/shepherd-approve-create-pr` is the human-only fallback for recording approval
  before commit, push, and PR creation.

The design gate is generic and portable: shepherd presents the design, criteria, and
panel and waits for one of two human-driven outcomes. **Approve** — a chat "yes" or
`/shepherd-approve-design` — writes `_design.approved` and proceeds. **Revise** — any
change request — goes back to the design iteration (feedback file + revision passes) and
re-presents, iterating until you approve. For any agent that has a plan mode (Claude
Code, Cursor, Codex, …), `plan_mode_gate: true` (the default) presents this through plan
mode as an adapter: accepting the plan is Approve, rejecting or editing it is Revise; if
the plan tool errors or is unavailable (remote, headless, web sessions) it falls back to
the chat gate. The agent never self-approves — a plan-tool error or a "continue" message
is never approval. Creating the PR uses a chat yes/no or `/shepherd-approve-create-pr`.
The on-disk `_design.approved` / `_create_pr.approved` markers are the only approval
signals.

## Install

```text
/plugin marketplace add apify/shepherd
/plugin install shepherd@shepherd
```

For local development, load the plugin directory directly:

```bash
claude --plugin-dir /path/to/shepherd/.claude
```

On claude.ai/code, attach this repo. In another repo, copy `.claude/skills/` or install
the plugin. Use the commands without a `shepherd:` prefix.

### Prompt reads during a run

During a run, shepherd may read engine files under `.claude/skills/_vendored/` as
instruction text. These read-only prompts are expected.

If you copied `.claude/skills/` into your repo or attached this repo, allowlist the
prompt reads in `.claude/settings.json`:

```json
{ "permissions": { "allow": ["Read(.claude/skills/_vendored/**)", "Read(.claude/skills/shepherd/**)"] } }
```

When installed as a plugin, the files live under the plugin path, so that glob will not
match. Approve the prompts once in that environment.

## Files

Run data lives in `.shepherd/`; plugin tooling lives in `.claude/skills/`. Each run
writes a `.shepherd/.gitignore` that keeps everything ignored except `config.json` and
`registry.json` — committable, shareable team config (shepherd itself never commits
`.shepherd/` paths); run evidence is summarized in the PR body instead.

Human-facing files:

- `.shepherd/1-triage.md`: product decision, complexity, approach sketch (orchestrator).
- `.shepherd/2-design.md`: product-first design with open questions (architect subagent).
- `.shepherd/3-success-criteria.md`: testable "done", written blind to the solution
  (success-criteria subagent).

Internal files:

- `.shepherd/_user_request.md`: raw task text.
- `.shepherd/_request_fact_check.md`: authoritative claim ledger (verify subagent).
- `.shepherd/_codebase_map.md` (optional): explorer output for medium/large tasks.
- `.shepherd/_design_feedback.md`: the human's iteration answers, verbatim
  (orchestrator-written; triggers architect/criteria revision passes).
- `.shepherd/_panel.json`: approved reviewer panel, resolved per-stage models, and
  iteration limits.
- `.shepherd/_state.json`: resumable phase and iteration state.
- `.shepherd/_progress.md`: run log and resolved configuration notes.
- `.shepherd/_design.approved`, `.shepherd/_create_pr.approved`: human approval markers.
- `.shepherd/iter-N/`: per-iteration `claim.md`, review files, `fulfillment.md`, diff,
  and test output (plus `baseline.txt` in `iter-1/`, the pre-change oracle metrics).

### Why one file per stage

The files are not bookkeeping; they are the context-routing mechanism. Each stage writes
one file, and each role reads only what it needs. Chat is ephemeral — your feedback goes
verbatim into `_design_feedback.md`, and subagents fold it into their files, so a run can
resume from disk at any point. The architect never reads the success criteria; the
criteria author never sees the solution; reviewers judge pasted judgment files (design,
criteria, diff, tests) while reading the repository itself for ground truth, and stay
blind to `claim.md` and to each other. Fulfillment reads `claim.md` for the claimed test
deltas but never the reviews. Blindness applies to judgments, never to ground truth: only
`.shepherd/` judgment files are gated — the repository stays readable to every role.

That split is what makes multiple judgments produce independent signal. Collapsing the
run into one shared context would either pollute each role or break that independence.

## Configuration

Stages are configured in `.shepherd/config.json`; defaults ship beside the skill in
`.claude/skills/shepherd/config.default.json`. The base registry maps each `use` name to
a vendored engine under `.claude/skills/_vendored/`.

Default config:

```json
{
  "stages": {
    "reviewers": [{ "use": "staff-review", "model": "auto" }],
    "final_reviewers": [
      { "use": "thermonuclear", "model": "auto" },
      { "use": "ponytail-review", "model": "auto" }
    ]
  },
  "oracle": { "commands": [] },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

Single stages (`verify`, `architect`, `implementer`, `success_criteria`, `fulfillment`)
are optional: when absent, the built-in role table in the skill drives the stage with no
engine. Assign an engine (`writing-plans`, `feature-dev`, `brainstorming`, or a repo
`use` such as `dig`) only when you want its specific methodology.

Each stage entry takes a `model`. `auto` (the default) lets shepherd pick per role and
triage tier — `haiku`/`sonnet`/`opus`, scaling up for larger changes and down for smaller
ones; a concrete name pins the stage. All `auto` picks are resolved and shown at the
design gate, where you can adjust any before approving. A local
`.shepherd/config.local.json` shallow-overrides `config.json` for one environment.

Use finite, non-mutating oracle commands such as type checks, lint checks, builds, unit
tests, and targeted integration tests. Avoid dev servers, watchers, fixers, cleanup
commands, inspectors, and eval workflows.

More detail:

- Config reference: [docs/shepherd-config.md](docs/shepherd-config.md)
- Vendored engine provenance: [VENDORED.md](VENDORED.md)

## Vendored engines

shepherd vendors optional stage engines (`brainstorming`, `writing-plans`,
`feature-dev`, `staff-review`, `thermonuclear`, `code-review`, and `ponytail-review`)
under `_vendored/` so a fresh clone or plugin install works without extra plugin
dependencies. `code-review` ships in the registry but is off the default final-reviewer
roster; assign it explicitly in config to opt in.

Vendored engines are named `ENGINE.md`, not `SKILL.md`, so Claude Code does not register
them as slash commands. The registry's `scope` field adapts each engine to shepherd's
file protocol, and every dispatched stage runs non-interactively: it records open
questions in its output file instead of asking the human. See [VENDORED.md](VENDORED.md).
