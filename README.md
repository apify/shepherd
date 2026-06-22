# devforge

A human-gated coding loop for Claude Code. `/devforge <task>` keeps product decisions,
implementation, review, tests, and merge approval separated through files in `.devforge/`.
Reviewers judge the diff and test output, not the implementer's claim.

## Flow

```text
/devforge <task>
  triage product decision        (no gate; stops only on DEFER/DECLINE)
  verify request + explore + design -> DESIGN GATE (plan mode): approve design + review panel
  implement -> oracle -> blind reviewers -> final reviewers   (loop until zero findings, incl. nits)
  merge confirm (plain chat)   -> commit / PR
```

There is exactly one hard gate — the **design gate**, in plan mode, before any source edit.
Triage is cheap and flows straight into design (it only stops to recommend against a
`DEFER | DECLINE`). Merge is a plain chat "commit & open PR?" confirm, not a plan-mode gate.
The design stays about one page and lists only the major changes. At the design gate devforge
writes `_panel.json` so a small bug can use a small review panel and a risky change the full
roster.

A review-only task ("review PR/branch X") is first-class: devforge runs triage → design (review
scope) → the review panel against the existing diff → a findings summary, and only enters the
implement loop if you then ask for fixes.

## Commands

- `/devforge <task>` starts a run.
- `/devforge` resumes a run from `.devforge/_state.json`.
- `/devforge-approve-design` and `/devforge-approve-merge` are human-only headless fallbacks for
  the design gate and merge confirm; each records its marker and auto-continues. Interactively,
  the design gate uses plan mode and the merge confirm is a chat yes/no.

## Install / Use

```text
/plugin marketplace add jirispilka/devforge
/plugin install devforge@devforge
```

For local development, load the plugin dir directly:

```bash
claude --plugin-dir /path/to/devforge/.claude
```

On claude.ai/code, attach this repo. In another repo, copy `.claude/skills/` or install as
a plugin. Use the commands without a `devforge:` prefix.

### Read prompts during a run

A run reads engine files under `.claude/skills/_vendored/` on demand. These read-only
prompts are expected. If you copied `.claude/skills/` into your repo (or attached the repo),
allowlist them in `.claude/settings.json`:

```json
{ "permissions": { "allow": ["Read(.claude/skills/_vendored/**)", "Read(.claude/skills/devforge/**)"] } }
```

When installed as a plugin the files live under the plugin path, so this glob won't match —
just approve the prompts once.

## Files

Run data lives in `.devforge/`; tooling lives in `.claude/skills/`. Two files are yours to read
— `1-triage.md` and `2-design.md`. Everything else is underscore-prefixed internal plumbing
(`_user_request.md`, `_verified_task.md`, `_request_fact_check.md`, `_panel.json`, `_state.json`, `_progress.md`,
`_design.approved`, `_merge.approved`) plus per-iteration `iter-N/` files.

### Why one file per stage

The files are not bookkeeping — they are how devforge routes context. Each stage writes one file
and each role reads **only** the files it needs, so a subagent's context stays scoped to its job
and reviewers stay independent. The implementer reads the distilled `_verified_task.md`, not the raw
`_request_fact_check.md` evidence; reviewers judge the diff against `2-design.md` and are deliberately
blind to the implementer's `claim.md` and to each other's reviews. That blindness is what makes a
multi-reviewer panel give independent signal instead of groupthink — collapsing the files into
one shared context would either pollute each role or break that independence.

Durable evidence is committed; regenerable files are ignored (`iter-*/diff.patch`,
`iter-*/test-results.txt`).

## Configuration

Stages are configured in `.devforge/config.json`; defaults ship beside the skill in
`.claude/skills/devforge/config.default.json`. The base registry maps each `use` name to a
vendored engine under `.claude/skills/_vendored/`.

### Why the engines are vendored

Stages are driven by upstream skills (`brainstorming`, `writing-plans`, `feature-dev`,
`staff-review`, `code-review`). devforge vendors a copy of each under `_vendored/` so a
fresh clone or plugin install works without those plugins. Relative paths
(`../_vendored/...`) keep the tree self-contained. They are named `ENGINE.md`, not
`SKILL.md`, so Claude Code does not register them as slash commands — they are instruction
text the stages read on demand, kept verbatim and adapted via the registry `scope` field.
See [VENDORED.md](VENDORED.md).

Default roster:

```json
{
  "stages": {
    "verify_request": { "use": "brainstorming", "model": "opus" },
    "architect": { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev", "model": "opus" },
    "reviewers": [{ "use": "staff-review", "model": "sonnet" }],
    "final_reviewers": [
      { "use": "thermonuclear", "model": "sonnet" },
      { "use": "code-review", "model": "sonnet" }
    ]
  },
  "oracle": { "commands": [] },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

Use finite, non-mutating oracle commands such as type checks, lint checks, builds, unit
tests, and targeted integration tests. Avoid dev servers, watchers, fixers, cleanup
commands, inspectors, and eval workflows.

More detail:

- Config reference: [docs/devforge-config.md](docs/devforge-config.md)
- Vendored engine provenance: [VENDORED.md](VENDORED.md)
