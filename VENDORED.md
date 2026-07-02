# Vendored engines

devforge vendors optional stage engines under `.claude/skills/_vendored/` so a fresh
clone, plugin install, or claude.ai/code attachment works without installing additional
plugins.

Engines are opt-in: the default config assigns engines only to the reviewer stages;
the single stages (`verify`, `architect`, `implementer`, `success_criteria`,
`fulfillment`) run built-in unless a config assigns them a `use`. The
vendored files are treated as upstream instruction text. devforge-specific behavior
lives in `.claude/skills/devforge/registry.base.json`, where each `use` entry supplies a
scope for the engine, and every dispatched stage runs non-interactively (open questions
go into the output file, never to the human).

Most vendored skills are named `ENGINE.md` instead of `SKILL.md` so Claude Code does not
auto-register them as slash commands. `feature-dev.md` and `code-review.md` keep their
upstream filenames because their directories are already nested under `_vendored/`.

| `use` | Path | Upstream | Devforge adaptation |
|---|---|---|---|
| `brainstorming` | `_vendored/brainstorming/ENGINE.md` | superpowers 6.0.3 | optional architect engine: clarifying-question discipline shapes the draft's open questions; devforge owns the chat iteration and gates |
| `writing-plans` | `_vendored/writing-plans/ENGINE.md` | superpowers 6.0.3 | optional architect engine: writes the short design; devforge owns execution and gates |
| `feature-dev` | `_vendored/feature-dev/feature-dev.md` | claude-plugins-official | optional implementer engine: implements against approved devforge files |
| `staff-review` | `_vendored/staff-review/ENGINE.md` | apify/agent-skills-internal 1.1.1 | reviews the pasted diff, blind to `claim.md` |
| `thermonuclear` | `_vendored/thermonuclear/ENGINE.md` | local personal skill | runs a strict maintainability review on the pasted diff |
| `code-review` | `_vendored/code-review/code-review.md` | claude-plugins-official | reviews the devforge diff/working tree instead of a PR diff |

Support files from `feature-dev` are also vendored. Two agents are re-registered as
project agents with devforge-specific `name:` fields:

- `.claude/agents/devforge-code-explorer.md` (also used as the `explorer` role for
  medium/large design drafts)
- `.claude/agents/devforge-code-architect.md`

## Re-sync

1. Re-copy upstream files into `_vendored/`.
2. Re-apply renamed project-agent `name:` values.
3. Update the table if versions, paths, or scopes changed.
4. Run `pytest -q`.
