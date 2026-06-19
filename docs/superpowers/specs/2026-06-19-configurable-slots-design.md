# devforge — configurable phase slots (vendored skills + adapters)

**Date:** 2026-06-19
**Status:** Design — approved for planning
**Scope:** Turn devforge's skeleton phases into config-driven *slots* filled by real,
vendored skills, behind thin devforge-owned adapters. Add a two-reviewer flow, a
plan-mode front-end for the design gate, and a configuration catalog.

---

## 1. Problem & goal

Today the orchestrator (`.claude/skills/devforge/SKILL.md`) runs all phases as
inline skeleton steps. The README already commits to the target: a
`.devforge/config.json` of swappable slots, subagent dispatch on chosen models, and
real reused skills **vendored** into `.claude/skills/` (plugins can't be installed on
claude.ai/code).

This step delivers that for **five slots**, keeping the existing `.devforge/` file
contract and the two human gates exactly as they are. The implementer and reviewer
stay independent and coordinate only through files.

> **Hard requirement — zero plugin dependency.** Installing superpowers (or any
> plugin) is painful and must NOT be required to run devforge. Every engine these
> slots use is **vendored and committed in this repository** (`.claude/skills/`,
> `.claude/agents/`). A fresh clone — or attaching this repo on claude.ai/code — runs
> the full default config with nothing installed. Installed plugins are only ever an
> *optional* `config.local.json` override, never a default and never a prerequisite.

Chosen fillers (defaults):

| Slot | Default filler | Source | Default model |
|------|---------------|--------|---------------|
| `validate` | `brainstorming` | superpowers (`obra/superpowers`) | opus |
| `architect` | `writing-plans` | superpowers | opus |
| `implementer` | `feature-dev` | claude-plugins-official `feature-dev` | opus |
| `reviewers` (per iteration, ≥1) | `staff-review` + `thermonuclear` | `apify/agent-skills-internal`; local personal skill `~/.claude/skills/.thermo-nuclear-code-quality-review` | sonnet |
| `final_reviewers` (after convergence) | `code-review` | claude-plugins-official `code-review` | sonnet |

The `reviewers` and `final_reviewers` slots are **lists** — each runs as an
independent subagent (parallel, blind to `claim.md` and to each other), so multiple
lenses can review the same diff.

---

## 2. Key decisions (locked in brainstorming)

1. **Depth = vendor + dispatch (option B).** Chosen skills are copied into the repo
   so the loop runs unmodified on web; the orchestrator dispatches real subagents on
   configured models.
2. **Multiple reviewers, different lenses — over a correctness oracle.** Every inner
   iteration runs the deterministic **oracle** (tests/lint = correctness ground truth)
   plus the per-iteration `reviewers` list — by default **`staff-review`** (correctness,
   edge cases, test coverage) **and** **`thermonuclear`** (maintainability: abstraction
   quality, file-size limits, spaghetti-branch growth, "code-judo" simplification),
   running as independent parallel subagents. After the inner loop converges,
   **`code-review`** runs once as a fresh second-angle pass (bugs, CLAUDE.md compliance,
   historical/PR context, confidence-scored). Net coverage: oracle = *does it work*,
   staff-review = *is it correct & well-tested*, thermonuclear = *is it clean/simple*,
   code-review = *a final independent correctness/compliance sweep*.
3. **Final-review findings feed back into the loop (option A).** code-review is not
   advisory — actionable findings reopen the inner loop until it comes back clean,
   consistent with devforge's "nothing reaches the gate noted-but-unhandled" rule.
4. **Adapter pattern.** Each slot is a thin devforge-owned wrapper skill that reads
   `.devforge/` inputs, drives a *vendored engine scoped to devforge's job*, and writes
   the slot's contract output file. Engines that don't fit the contract are retargeted,
   not used verbatim (see §5).
5. **File-marker gate is the spine.** Plan mode and superpowers are layered on top:
   plan mode is an optional CLI front-end for the design gate; superpowers skills are
   vendored phase fillers with their own gate/commit steps stripped (the orchestrator
   owns the gate). This preserves resumability and web portability.

---

## 3. Configuration

### `.devforge/config.json` (committed default)

```json
{
  "slots": {
    "validate":       { "filler": "brainstorming",  "model": "opus" },
    "architect":      { "filler": "writing-plans",   "model": "opus" },
    "implementer":     { "filler": "feature-dev", "model": "opus" },
    "reviewers": [
      { "filler": "staff-review",  "model": "sonnet" },
      { "filler": "thermonuclear", "model": "sonnet" }
    ],
    "final_reviewers": [
      { "filler": "code-review",   "model": "sonnet" }
    ]
  },
  "limits": { "inner_iterations": 3, "final_review_rounds": 2 },
  "plan_mode_gate": true
}
```

- **`.devforge/config.local.json`** (already gitignored) shallow-merges over
  `config.json` for per-environment overrides — e.g. pointing a slot at a
  locally-installed skill instead of the vendored copy.
- The orchestrator loads config at setup, validates every `filler` against the
  **registry** (§4) for that slot, and **errors clearly** on an unknown filler or a
  filler not allowed in that slot (e.g. a reviewer filler in the implementer slot).
- Missing config → the defaults above (the orchestrator writes the default file on a
  fresh run so it's visible and editable).
- `plan_mode_gate: false` disables the plan-mode front-end (always falls back to the
  marker skill — required behavior on web/headless).

### Slot → filler registry

A small table the orchestrator consults to (a) reject invalid configs and (b) resolve
a filler name to its adapter skill directory.

| Slot | Allowed fillers |
|------|-----------------|
| `validate` | `brainstorming`, `builtin` |
| `architect` | `writing-plans`, `builtin` |
| `implementer` | `feature-dev`, `builtin` |
| `reviewers` (list) | `staff-review`, `thermonuclear`, `code-review`, `builtin` |
| `final_reviewers` (list) | `code-review`, `staff-review`, `thermonuclear` |

`builtin` = devforge's current inline skeleton step for that phase (always available,
no vendored engine). An **empty `final_reviewers` list** skips the final pass. A
duplicate filler within one list is rejected. Each reviewer entry resolves to the same
adapter regardless of which list it appears in.

---

## 4. Loop control (orchestrator)

```
validate (validate slot)  ─┐
explore  (orchestrator)    │ read-only — optional plan-mode front-end
architect (architect slot) ─┘ → design.md
        │
   DESIGN GATE  (plan mode ExitPlanMode in CLI, else /devforge-approve-design) → design.approved
        │
   ┌─ inner loop (iteration N = 1..inner_iterations) ───────────────────────┐
   │ implementer slot  → edits source, writes iter-N/claim.md               │
   │ orchestrator      → oracle (tests/lint) + git diff → diff.patch        │
   │ reviewers (∥)     → each reads diff.patch+results (blind to claim and  │
   │                     to each other) → iter-N/review-<filler>.md         │
   │ converged? green AND every finding across ALL review-*.md resolved     │
   └───────────────────────────────────────────────────────────────────────┘
        │ converged
   final_reviewers (∥) → each reads diff.patch + working tree → iter-N/final-review-<filler>.md
        │
   actionable findings in any? ── yes ──► reopen inner loop (counts against
        │                                 final_review_rounds; escalate if exceeded)
        │ none (or empty list)
   PRE-MERGE GATE  → rich diff presentation, /devforge-approve-merge → merge.approved
        │
   finish (commit, PR)
```

- **Reviewers run in parallel** each iteration, one independent subagent per entry in
  the `reviewers` list, each blind to `claim.md` and to the others. Each writes its own
  `iter-N/review-<filler>.md` (e.g. `review-staff-review.md`, `review-thermonuclear.md`),
  first line `VERDICT: PASS|FAIL`, severity-tagged findings. The orchestrator
  aggregates findings across all of them.
- **Inner-loop convergence:** oracle green **and** every finding across **all**
  `review-*.md` fixed-or-explicitly-justified (nits included). Where two reviewers
  pull in opposite directions (e.g. thermonuclear wants a structural restructure that a
  correctness reviewer would keep minimal), the orchestrator records the reconciliation
  in the next `claim.md`. Escalate after `inner_iterations` without converging.
- **Final review** runs once after convergence: each entry in `final_reviewers` as a
  parallel subagent → `iter-N/final-review-<filler>.md` (same format and independence
  rule — reads `diff.patch` + working tree, never `claim.md`). Actionable findings from
  any of them become the finding set for a fresh inner iteration (implement → oracle →
  reviewers), after which the final reviewers re-run. Bounded by `final_review_rounds`;
  exceeding it escalates. An empty `final_reviewers` list skips this stage.

---

## 5. Vendoring & adapters

### Layout

```
.claude/skills/
  devforge/                      orchestrator — reads config, dispatches slots, plan-mode front-end
  devforge-approve-design/       (existing, unchanged)
  devforge-approve-merge/        (existing, unchanged)
  devforge-validate-brainstorm/  adapter → vendored brainstorming, gate/commit stripped
  devforge-architect-plans/      adapter → vendored writing-plans, writes design.md
  devforge-impl-feature-dev/     adapter → feature-dev implement-only, fed approved design.md
  devforge-review-staff/         adapter → staff-review (correctness) on diff.patch → review-staff-review.md
  devforge-review-thermo/        adapter → thermonuclear (maintainability) on diff.patch → review-thermonuclear.md
  devforge-review-code/          adapter → code-review engine retargeted PR→diff.patch → final-review-code-review.md
  _vendored/                     faithful upstream copies the adapters delegate to
.claude/agents/
  devforge-code-explorer.md      feature-dev's agents, vendored so they're dispatchable on web
  devforge-code-architect.md
VENDORED.md                      provenance per entry: upstream repo + path + version/commit + adaptation notes
docs/devforge-config.md          configuration catalog (§6)
```

### Adapter contract

Each adapter SKILL.md:
1. **Reads** its slot inputs from `.devforge/` (e.g. reviewer reads `task.md`,
   `design.md`, `iter-N/diff.patch`, `iter-N/test-results.txt`).
2. **Drives** the vendored engine in `_vendored/…`, scoped to devforge's job.
3. **Writes** the contract output (`claim.md`, `review-<filler>.md`, or
   `final-review-<filler>.md`) in the required format.

Adapters are thin (instructions only); `_vendored/` holds untouched engines so a
re-sync is a clean diff. Per-slot scoping notes:

- **`validate` ← brainstorming:** keep its clarifying-question discipline; **strip**
  its spec-doc write/commit and its own approval gate (devforge's validate writes
  `task.md`/`validation.md` and the orchestrator owns the gate). Still runs devforge's
  GitHub-issue staleness / claim-ledger check.
- **`architect` ← writing-plans:** produce `design.md` in devforge's format (approach,
  files to change, test strategy/oracle, risks); **strip** writing-plans' own file
  layout/gate steps.
- **`implementer` ← feature-dev:** feed it the *already-approved* `design.md` as the
  spec; **skip** feature-dev's Discovery / clarifying-questions / architecture phases
  (devforge already did those and got human approval). Reuse its `code-explorer` /
  `code-architect` agents for grounding only. Address prior `review-*.md` /
  `final-review-*.md` findings; write `claim.md`. Never edit/delete tests.
- **`reviewers[*]` ← staff-review:** clean fit — reviews the branch/working-tree diff
  for correctness / edge cases / test coverage, emits severity-tagged findings. Adapter
  points it at `diff.patch` and writes `review-staff-review.md` (`VERDICT:` first line),
  blind to `claim.md`.
- **`reviewers[*]` ← thermonuclear:** an unusually strict *maintainability* review
  (abstraction quality, 1k-line file ceiling, spaghetti-branch growth, "code-judo"
  simplification). Clean fit — already reviews the current branch's changes. Adapter
  points it at `diff.patch` and maps its prioritized findings + approval-bar
  presumptive-blockers onto `review-thermonuclear.md` (`VERDICT:` first line,
  severity-tagged), blind to `claim.md`. Note: thermonuclear sets
  `disable-model-invocation: true` upstream; the adapter does not invoke it as a Skill
  — it feeds the vendored instruction text to the reviewer subagent, so the flag is
  irrelevant to dispatch (recorded in `VENDORED.md`).
- **`final_reviewers[*]` ← code-review:** keep its parallel multi-agent +
  confidence-score engine; **retarget** it from "an existing PR via `gh pr diff`" to
  **`diff.patch` + the working tree**, and **redirect** its output from a `gh pr
  comment` into `final-review-code-review.md`. Drop the PR-eligibility and `gh`-posting
  steps.

### `VENDORED.md`

One entry per vendored engine/agent: upstream repo, source path, version or commit
pinned at vendor time, and the adaptation notes above — so re-sync is deliberate.

---

## 6. Configuration catalog — `docs/devforge-config.md`

A human-facing doc that makes the slots and their options clear. Contents:

1. **What a slot is** — a role defined by the files it reads/writes; the filler is
   config. The oracle (tests/lint) is *not* a slot.
2. **Per-slot table** — for each slot (`validate`, `architect`, `implementer`,
   `reviewers`, `final_reviewers`): what it reads, what it writes, the allowed fillers,
   a one-line description of each filler, and the recommended model.
3. **Example configs (ready to paste):**
   - **`default`** — the schema in §3 (reviewers = staff-review + thermonuclear; final
     = code-review).
   - **`fast-cheap`** — smaller models, single per-iteration reviewer
     (`reviewers: [staff-review]`), empty `final_reviewers`, `inner_iterations: 2`.
   - **`max-rigor`** — opus across review slots, all three lenses per iteration
     (`reviewers: [staff-review, thermonuclear, code-review]`), `final_review_rounds: 3`.
   - **`builtin-only`** — every slot `builtin` / empty final list (the current skeleton;
     no vendored engines) for a dependency-free smoke test.
4. **How overrides work** — `config.local.json` shallow-merge; the validation/error
   behavior.

The README's "Planned — enrichment" section is updated to "Built" and points here.

---

## 7. Out of scope

- Configurable `explore` phase (stays orchestrator-owned).
- Vendoring domain skills (e.g. `dig`) — they stay in their target repos as optional
  local slot swaps.
- Changing the oracle, the file contract, or the two-gate structure.
- Auto re-sync tooling for vendored engines (manual, guided by `VENDORED.md`).

---

## 8. Testing strategy (the oracle for this change)

devforge is skills (markdown), so "tests" are structural + a dogfood run:

1. **Config validation** — unit-style checks (the existing `tests/` Python harness or a
   small script): valid config parses; unknown filler errors; a filler not allowed in a
   slot errors (e.g. `feature-dev` in `reviewers`); `reviewers`/`final_reviewers` accept
   lists; a duplicate filler within one list errors; an empty `final_reviewers` list is
   valid and skips the final stage; `config.local.json` overrides merge correctly;
   missing config yields defaults.
2. **Vendoring integrity** — every `filler` in the registry resolves to an existing
   adapter dir; every adapter references an existing `_vendored/` engine; `VENDORED.md`
   has an entry per vendored item. **No-install guard:** no committed skill/adapter
   references a `plugins/`, `~/.claude/plugins`, or plugin-cache path — every default
   path resolves inside the repo (grep-based check), and all vendored files are
   git-tracked (not gitignored).
3. **Dogfood** — run `/devforge` on a small task in this repo end-to-end with the
   `default` config and again with `builtin-only`, confirming both gates fire, the
   multi-reviewer flow runs, and `final-review-*.md` is produced.
```
