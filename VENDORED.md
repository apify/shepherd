# Vendored engines

shepherd vendors optional stage engines under `.claude/skills/_vendored/` so a fresh
clone, plugin install, or claude.ai/code attachment works without installing additional
plugins.

Engines are opt-in: the default config assigns engines only to the reviewer stages;
the single stages (`verify`, `architect`, `implementer`, `success_criteria`,
`fulfillment`) run built-in unless a config assigns them a `use`. The
vendored files are treated as upstream instruction text. shepherd-specific behavior
lives in `.claude/skills/shepherd/registry.base.json`, where each `use` entry supplies a
scope for the engine, and every dispatched stage runs non-interactively (open questions
go into the output file, never to the human).

Vendored skills are named `ENGINE.md` instead of `SKILL.md` so Claude Code does not
auto-register them as slash commands; `feature-dev.md` and `code-review.md` keep their
upstream filenames, which never auto-register anyway.

| `use` | Path | Vendored from (exact source) | Shepherd adaptation |
|---|---|---|---|
| `brainstorming` | `_vendored/brainstorming/ENGINE.md` | superpowers 6.0.3, `skills/brainstorming/SKILL.md` (marketplace `claude-plugins-official`, repo github.com/obra/superpowers) | optional architect engine: clarifying-question discipline shapes the draft's open questions; shepherd owns the chat iteration and gates |
| `writing-plans` | `_vendored/writing-plans/ENGINE.md` | superpowers 6.0.3, `skills/writing-plans/SKILL.md` (same marketplace) | optional architect engine: writes the short design; shepherd owns execution and gates |
| `feature-dev` | `_vendored/feature-dev/feature-dev.md` + `agents/*.md` | claude-plugins-official `feature-dev` @ `85cce0381e78`, `commands/feature-dev.md` and `agents/*.md` | optional implementer engine: implements against approved shepherd files |
| `staff-review` | `_vendored/staff-review/ENGINE.md` | apify/agent-skills-internal 1.1.5, `staff-review/SKILL.md` (github.com/apify/agent-skills-internal) | reviews the pasted diff, blind to `claim.md` |
| `thermonuclear` | `_vendored/thermonuclear/ENGINE.md` | personal user skill, `~/.claude/skills/.thermo-nuclear-code-quality-review/SKILL.md` — unversioned, no public upstream | runs a strict maintainability review on the pasted diff |
| `code-review` | `_vendored/code-review/code-review.md` | claude-plugins-official `code-review` plugin, `commands/code-review.md` (unversioned by upstream) | reviews the shepherd diff/working tree instead of a PR diff; registry-only, off the default roster |
| `ponytail-review` | `_vendored/ponytail-review/ENGINE.md` | ponytail 4.7.0, `skills/ponytail-review/SKILL.md` (github.com/DietrichGebert/ponytail) | final reviewer: line-level deletion/leanness lens, design-aware, clarity-guarded |

Support files from `feature-dev` are also vendored. Two agents are re-registered as
project agents with shepherd-specific `name:` fields:

- `.claude/agents/shepherd-code-explorer.md` (also used as the `explorer` role for
  medium/large design drafts)
- `.claude/agents/shepherd-code-architect.md`

## Re-sync

0. Diff each `_vendored/` file against the source named in the table above
   (`diff <vendored> <upstream>`); a zero diff means the copy is verbatim and only
   the version pin needs bumping.
1. Re-copy upstream files into `_vendored/`.
2. Re-apply renamed project-agent `name:` values.
3. Update the table if versions, paths, or scopes changed.
4. Mirror the same files into `.agents/skills/_vendored/` (kept byte-identical).
5. Run `pytest -q`.
