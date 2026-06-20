# devforge configuration

devforge's phases are **slots**. A *slot* is a role defined only by the files it reads
and writes; what *fills* it — which vendored skill, on which model — is config you set in
`.devforge/config.json`. Swap a slot's `use` value and the loop runs a different engine
without any change to the orchestrator. The **oracle** (your project's tests/lint) is the
deterministic ground truth and is **not** a slot.

Every engine is **vendored in this repo** (`.claude/skills/_vendored/`) and driven by a
single universal dispatch contract in the orchestrator — there are no per-skill adapter
files. Each `use` maps (in `.devforge/registry.json`) to the roles it can fill, its
vendored engine path, and a one-line scope note; the orchestrator fills one template
from that. Nothing needs installing — see [`VENDORED.md`](../VENDORED.md).

## The slots

| Slot | Runs | Reads | Writes | `use` options (default **bold**) | Model |
|------|------|-------|--------|----------------------------------|-------|
| `validate` | once, first | the task / issue, codebase | `task.md`, `validation.md` | **`brainstorming`** | opus |
| `architect` | once, after explore | `task.md`, `validation.md`, codebase | `design.md` | **`writing-plans`** | opus |
| `implementer` | every iteration | `design.md`, prior reviews | source edits, `claim.md` | **`feature-dev`** | opus |
| `reviewers` (list) | every iteration, parallel | `diff.patch`, `test-results.txt`, spec | `review-<use>.md` each | **`staff-review`**, `thermonuclear`, `code-review` | sonnet |
| `final_reviewers` (list) | after convergence, parallel | `diff.patch` + working tree, spec | `final-review-<use>.md` each | **`thermonuclear`** + **`code-review`**, `staff-review` | sonnet |

### What each engine does

- **`brainstorming`** — clarifying-question discipline to pin down purpose/constraints
  (devforge strips its spec-doc/gate steps; keeps the issue staleness check).
- **`writing-plans`** — concrete, file-level plan → `design.md`.
- **`feature-dev`** — codebase-aware implementation (driven implement-only against the
  approved design).
- **`staff-review`** — correctness / edge cases / test coverage.
- **`thermonuclear`** — strict maintainability: abstraction quality, 1k-line file
  ceiling, spaghetti-branch growth, "code-judo" simplification.
- **`code-review`** — multi-agent bug / CLAUDE.md / git-history pass with confidence
  scoring (retargeted from a PR to the iteration diff).

To add an option, vendor its engine and add a row to `.devforge/registry.json`
(`use` → roles + engine + scope). No new skill file needed.

Each reviewer runs as an independent subagent, **blind to `claim.md` and to the other
reviewers**, so the lenses stay genuinely independent.

## Limits & gate

```json
{ "limits": { "inner_iterations": 3, "final_review_rounds": 2 }, "plan_mode_gate": true }
```

- `inner_iterations` — implement→oracle→reviewers rounds before escalating.
- `final_review_rounds` — how many times a final review may reopen the inner loop.
- `plan_mode_gate` — when true and running interactively in the CLI, the design gate
  renders `design.md` in Claude Code's plan-mode for native approve/reject (the
  orchestrator calls `EnterPlanMode`, mirrors the design into the plan file, then
  `ExitPlanMode`); otherwise (and always on web/headless) it falls back to
  `/devforge-approve-design`. The marker file is the source of truth either way.

## Example configs

### `default`
```json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers": [
      { "use": "staff-review",  "model": "sonnet" }
    ],
    "final_reviewers": [
      { "use": "thermonuclear", "model": "sonnet" },
      { "use": "code-review",   "model": "sonnet" }
    ]
  },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

The per-iteration set is deliberately lean (correctness only) so the loop stays fast;
the heavier maintainability/quality lenses (`thermonuclear`, `code-review`) run once at
final review. Move a lens into `reviewers` if you want it on every iteration.

### `fast-cheap` — one reviewer, no final pass, fewer rounds
```json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "haiku" },
    "architect":   { "use": "writing-plans", "model": "sonnet" },
    "implementer": { "use": "feature-dev",   "model": "sonnet" },
    "reviewers": [
      { "use": "staff-review", "model": "haiku" }
    ],
    "final_reviewers": []
  },
  "limits": { "inner_iterations": 2, "final_review_rounds": 0 },
  "plan_mode_gate": true
}
```

### `max-rigor` — all three lenses per iteration, on opus
```json
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "writing-plans", "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers": [
      { "use": "staff-review",  "model": "opus" },
      { "use": "thermonuclear", "model": "opus" },
      { "use": "code-review",   "model": "opus" }
    ],
    "final_reviewers": [
      { "use": "code-review", "model": "opus" }
    ]
  },
  "limits": { "inner_iterations": 5, "final_review_rounds": 3 },
  "plan_mode_gate": true
}
```

## Base + repo registries

The registry is **layered**, just like the config:

- The **base registry** ships beside the skill at `registry.base.json` — the generic engines
  (`brainstorming`, `writing-plans`, `feature-dev`, `staff-review`, `thermonuclear`,
  `code-review`). It travels with the install, so its engine paths resolve relative to the
  devforge install.
- A target repo may add `.devforge/registry.json` listing **only its own extra engines**.
  devforge shallow-merges its `uses` over the base (the repo wins on a name collision;
  `slot_roles` always comes from the base). A repo `use`'s engine path resolves relative to the
  **repo root**. A repo with no `.devforge/registry.json` runs on the base alone.

So "what engines exist here?" = base + this repo's deltas. To keep a small delta file from
reading as the whole story, two things help:

- a `$comment` key in the repo's `registry.json` (ignored by the merge) saying it is partial;
- devforge logs the **fully-resolved registry** (every engine → resolved path) to
  `.devforge/progress.md` at startup, so each run leaves a complete, concrete view.

### Recipe: add a domain engine in a target repo

To plug a repo's own skill/agent into a slot — e.g. a planning skill at `.claude/skills/dig`
and an end-to-end verifier at `.claude/agents/mcpc-tester.md`:

```jsonc
// <target-repo>/.devforge/registry.json   — committed in that repo, deltas only
{
  "$comment": "Domain engines only. Generic engines come from devforge's base registry.",
  "uses": {
    "dig": {
      "roles": ["architect"],
      "engine": ".claude/skills/dig/SKILL.md",
      "scope": "follow as instruction text; plan using its resources + conventions; STRIP its own gate and issue-creation; write design.md only"
    },
    "mcpc-tester": {
      "roles": ["reviewer", "final_reviewer"],
      "engine": ".claude/agents/mcpc-tester.md",
      "scope": "follow as instruction text; build + probe the live server; emit VERDICT then findings"
    }
  }
}
```

Then wire them in `<target-repo>/.devforge/config.json` — a `use` with both reviewer roles can
sit in `reviewers` (probe every iteration), `final_reviewers` (one final probe), or both,
depending on the feature:

```jsonc
{
  "slots": {
    "validate":    { "use": "brainstorming", "model": "opus" },
    "architect":   { "use": "dig",           "model": "opus" },
    "implementer": { "use": "feature-dev",   "model": "opus" },
    "reviewers":       [ { "use": "staff-review",  "model": "sonnet" } ],
    "final_reviewers": [ { "use": "thermonuclear", "model": "sonnet" },
                         { "use": "code-review",   "model": "sonnet" },
                         { "use": "mcpc-tester",   "model": "sonnet" } ]
  },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

No devforge change is needed to add a domain engine — only these two files in the target repo.

## Overrides & validation

- `.devforge/config.json` is the committed default (devforge writes it on first run if
  missing).
- `.devforge/config.local.json` (gitignored) **shallow-merges** over it for
  per-environment tweaks — e.g. pointing a slot at a locally-installed skill instead of
  the vendored copy. This is the **only** place an installed plugin may be referenced.
- On every run the orchestrator validates the resolved config against
  `.devforge/registry.json`: every slot present; each `use` allowed in its slot; no
  duplicate `use` within a list. An invalid config **stops the run** with the exact
  error and the allowed list. `scripts/validate_config.py` encodes the same rules for
  CI.
