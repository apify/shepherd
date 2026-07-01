# devforge config

devforge configuration chooses the engine behind each stage, the model used for that
stage, the deterministic oracle commands, and the iteration limits for review loops.

The active config is `.devforge/config.json`. If it is missing, devforge copies the
default from `.claude/skills/devforge/config.default.json`. A local
`.devforge/config.local.json` may override values for one environment.

## Runtime files

Two files are intended for humans; the underscore-prefixed files are internal
context-routing state.

- `.devforge/1-triage.md`: cheap product decision, quick fact check, complexity, and
  approach sketch.
- `.devforge/2-design.md`: the living design — product first, open questions become
  decisions during chat iteration; once approved it is the implementation or review scope.
- `.devforge/_user_request.md`: raw task, written before triage.
- `.devforge/_codebase_map.md` (optional): explorer output for medium/large tasks,
  reused by the design draft and the implementer.
- `.devforge/_panel.json`: approved per-run reviewer subset and limits.
- `.devforge/_state.json`: resume state, including `state.panel` after design approval.
- `.devforge/_progress.md`: resolved config, run notes, oracle status, and final links.

The configured reviewer lists are a roster. The design gate selects the run-specific
panel from that roster and writes it to `_panel.json`.

### Why one file per stage

Each stage writes one file and each role reads only what it needs, so context stays
scoped and reviewers stay independent. Chat is ephemeral; every decision lands in its
file the moment it is made. Reviewers judge the diff against `2-design.md` and never see
`claim.md` or each other's reviews — they receive pasted content, not file access. That
blindness is what keeps a multi-reviewer panel's signal independent.

Collapsing the files would either pollute role context or break reviewer independence.

## Stages

| Stage | Default | Reads | Writes |
|---|---|---|---|
| `architect` | built-in (optional engine) | `_user_request.md`, `1-triage.md`, `_codebase_map.md` if present, codebase | `2-design.md` draft |
| `implementer` | built-in (optional engine) | `2-design.md`, `_codebase_map.md` if present, prior reviews | source edits, `claim.md` |
| `reviewers` | `staff-review` | pasted design, diff, test output | `review-<use>.md` |
| `final_reviewers` | `thermonuclear`, `code-review` | pasted design, diff, test output, working tree | `final-review-<use>.md` |

`architect` and `implementer` are optional in config: when absent, the built-in role
table in the skill drives the stage with no engine. The design iteration with the human
is always done by the orchestrator in chat, never by an engine.

`reviewers` run inside the implementation loop. `final_reviewers` run after the regular
loop is clean and can trigger bounded targeted fix rounds.

## Complexity defaults

Triage assigns the tier; the design gate proposes the panel from it. These defaults keep
small changes fast while still increasing scrutiny for broad or risky work.

| Tier | Use When | Default Panel |
|---|---|---|
| `trivial` | <=10 lines, 1 file, no logic change | 1 reviewer, no final, inner=1, rounds=0 |
| `small` | localized 1-3 file change | 1 reviewer, 1 final, inner=2, rounds=1 |
| `medium` | feature, shared helper, or multi-area fix | 1 reviewer, 2 final, inner=3, rounds=2 |
| `large` | core, many files, public API/response contract | full roster, inner=3, rounds=2 |

Core/shared or public-contract changes are `medium` at minimum regardless of line count.

## Default config

```json
{
  "stages": {
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

Add targeted checks only for touched surfaces: builds, widget checks, agent/skill checks,
or specific integration tests. Avoid `dev`, `start`, watchers, fixers, cleanup commands,
inspectors, and eval workflows.

## Registry overrides

The shipped registry is `.claude/skills/devforge/registry.base.json`. A repo may add
`.devforge/registry.json` with extra `uses`; repo `uses` shallow-override base uses.
Base engine paths resolve relative to the skill. Repo engine paths resolve relative to
the repo.

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

- `reviewers` and `final_reviewers` are present
- every configured `use` exists (`architect`/`implementer` are validated only when present)
- the `use` supports the stage role
- reviewer and final reviewer lists contain no duplicate `use`

`scripts/validate_config.py` checks the same rules for CI and local tests.
