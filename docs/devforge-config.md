# devforge config

Config chooses which engine fills each stage and which model it uses. The oracle is separate:
`oracle.commands` is the deterministic check list.

## Runtime Files

Two files are human-facing; the underscore-prefixed rest is internal context-routing plumbing.

- `.devforge/1-triage.md`: cheap product decision and complexity (you read).
- `.devforge/2-design.md`: short human-reviewed plan, major changes only (you read).
- `.devforge/_user_request.md`: raw task, written before triage.
- `.devforge/_verified_task.md`, `.devforge/_request_fact_check.md`: verified task and its evidence ledger.
- `.devforge/_panel.json`: approved per-run reviewer subset and limits.
- `.devforge/_state.json`: resume state, including `state.panel` after design approval.

The configured reviewer lists are a roster. The design gate selects the run-specific panel
from that roster.

### Why one file per stage

Each stage writes one file and each role reads **only** what it needs, so context stays scoped
and reviewers stay independent. The implementer reads the distilled `_verified_task.md`, not the raw
`_request_fact_check.md`; reviewers judge the diff against `2-design.md` and never see `claim.md` or each
other's reviews — that blindness is what keeps a multi-reviewer panel's signal independent.
Collapsing the files would pollute roles or break that independence.

## Stages

| Stage | Default `use` | Reads | Writes |
|---|---|---|---|
| `verify_request` | `brainstorming` | `_user_request.md`/issue, `1-triage.md`, codebase | `_verified_task.md`, `_request_fact_check.md` |
| `architect` | `writing-plans` | `_verified_task.md`, `_request_fact_check.md`, `1-triage.md`, codebase | `2-design.md` |
| `implementer` | `feature-dev` | `_verified_task.md`, `_request_fact_check.md`, `2-design.md`, prior reviews | source edits, `claim.md` |
| `reviewers` | `staff-review` | `_verified_task.md`, `2-design.md`, diff, test output | `review-<use>.md` |
| `final_reviewers` | `thermonuclear`, `code-review` | `_verified_task.md`, `2-design.md`, diff, working tree | `final-review-<use>.md` |

## Complexity Defaults

| Tier | Use When | Default Panel |
|---|---|---|
| `trivial` | <=10 lines, 1 file, no logic change | 1 reviewer, no final, inner=1, rounds=0 |
| `small` | localized 1-3 file change | 1 reviewer, 1 final, inner=2, rounds=1 |
| `medium` | feature, shared helper, or multi-area fix | 1 reviewer, 2 final, inner=3, rounds=2 |
| `large` | core, many files, public API/response contract | full roster, inner=3, rounds=2 |

Core/shared or public-contract changes are `medium` at minimum regardless of line count.

## Default Config

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

`oracle.commands` should be finite and non-mutating. Good defaults for JS/TS repos are:

```json
{
  "oracle": {
    "commands": ["pnpm run check", "pnpm run test:unit"]
  }
}
```

Add targeted checks only for touched surfaces: `build`, widget checks, agent/skill checks,
or specific integration tests. Avoid `dev`, `start`, watchers, fixers, cleanup commands,
inspectors, and eval workflows.

## Registry Overrides

The shipped registry is `.claude/skills/devforge/registry.base.json`. A repo may add
`.devforge/registry.json` with extra `uses`; repo `uses` shallow-override base uses. Base
engine paths resolve relative to the skill; repo engine paths resolve relative to the repo.

Example:

```json
{
  "uses": {
    "dig": {
      "roles": ["architect"],
      "engine": ".claude/skills/dig/SKILL.md",
      "scope": "follow as instructions; write 2-design.md only"
    },
    "live-contract": {
      "roles": ["reviewer", "final_reviewer"],
      "engine": ".claude/agents/live-contract.md",
      "scope": "probe the live server; emit VERDICT then findings"
    }
  }
}
```

Then reference those `use` names in `.devforge/config.json`.

## Validation

On each run devforge validates:

- every stage is present
- every `use` exists
- the `use` supports the stage role
- reviewer/final reviewer lists contain no duplicate `use`

`scripts/validate_config.py` checks the same rules for CI/tests.
