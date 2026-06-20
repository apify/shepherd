# Vendored engines

devforge ships every slot engine **in this repository** so the loop runs with nothing
installed (on a fresh clone and on claude.ai/code). Plugins are never required; they are
only ever an optional `.devforge/config.local.json` override.

Each engine below is copied **verbatim** into `.claude/skills/_vendored/`. devforge's
**single universal dispatch contract** (in the orchestrator) drives every engine scoped
to devforge's file contract. The resolved registry stores each engine path and scope
(`engine` + `scope`), so devforge does not need bespoke wrapper skills. The
engines themselves are unmodified, so a re-sync is a clean diff.

> **Why `ENGINE.md`, not `SKILL.md`.** A vendored skill named `SKILL.md` under
> `.claude/skills/` would be auto-registered by Claude Code as an invocable skill —
> colliding with an installed copy of the same name and letting the raw engine run
> outside devforge's dispatch contract. Vendored engines are *reference text devforge
> reads*, so they use a non-`SKILL.md` filename and never register. (`feature-dev.md` and
> `code-review.md` were already non-`SKILL.md` upstream.)

| Vendored path | Slot value (`use`) | Upstream | Source path | Version | Adaptation (registry `scope`) |
|---|---|---|---|---|---|
| `_vendored/feature-dev/feature-dev.md` | `feature-dev` | claude-plugins-official `feature-dev` | `commands/feature-dev.md` | cache tag `unknown` | Driven **implement-only**: skips Discovery / clarifying-questions / architecture (devforge already designed + got human approval). |
| `_vendored/feature-dev/agents/*.md` | (support) | same | `agents/{code-explorer,code-architect,code-reviewer}.md` | same | `code-explorer` + `code-architect` re-registered as project agents (see below) for grounding; `code-reviewer` kept for reference only — devforge uses the review slot instead. |
| `_vendored/staff-review/ENGINE.md` | `staff-review` | `apify/agent-skills-internal` | `skills/staff-review/SKILL.md` | 1.1.1 | Pointed at `iter-N/diff.patch`, writes `review-staff-review.md`, blind to `claim.md`. |
| `_vendored/thermonuclear/ENGINE.md` | `thermonuclear` | local personal skill | `~/.claude/skills/.thermo-nuclear-code-quality-review/SKILL.md` | local | Upstream sets `disable-model-invocation: true`; devforge feeds the text to a subagent as instructions (not Skill-invoked), so the flag is irrelevant. Writes `review-thermonuclear.md`. |
| `_vendored/code-review/code-review.md` | `code-review` | claude-plugins-official `code-review` | `commands/code-review.md` | marketplace | Retargeted from an existing PR (`gh pr diff`) to `iter-N/diff.patch` + working tree; drops PR-eligibility and the `gh pr comment` step; writes `final-review-code-review.md`. |
| `_vendored/brainstorming/ENGINE.md` | `brainstorming` | claude-plugins-official `superpowers` | `skills/brainstorming/SKILL.md` | 6.0.3 | Keeps the clarifying-question discipline but strips the spec-doc write/commit and its own approval gate (orchestrator owns the gate); writes `task.md` + `validation.md`. |
| `_vendored/writing-plans/ENGINE.md` | `writing-plans` | claude-plugins-official `superpowers` | `skills/writing-plans/SKILL.md` | 6.0.3 | Keeps the planning discipline, strips the file-layout/gate steps; writes `design.md`. |

## Re-registered agents

| Project agent | Copied from | Change |
|---|---|---|
| `.claude/agents/devforge-code-explorer.md` | `_vendored/feature-dev/agents/code-explorer.md` | `name:` → `devforge-code-explorer` (avoids colliding with the plugin's agent). |
| `.claude/agents/devforge-code-architect.md` | `_vendored/feature-dev/agents/code-architect.md` | `name:` → `devforge-code-architect`. |

## Re-sync procedure

1. Re-copy the file(s) from the upstream source path above into `_vendored/`.
2. Re-apply the renamed `name:` for the two project agents.
3. Bump the **Version** column and note any upstream changes that affect the registry `scope` notes.
4. Run `cd tests && python -m pytest` — the no-install guard and vendoring-integrity
   tests must stay green.
