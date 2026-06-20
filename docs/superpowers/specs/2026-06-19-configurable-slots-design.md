# devforge — configurable phase slots (design record)

**Date:** 2026-06-19 (built 2026-06-20)
**Status:** Built. Living docs: [`README.md`](../../../README.md),
[`docs/devforge-config.md`](../../devforge-config.md), [`VENDORED.md`](../../../VENDORED.md).

This is the *why* behind devforge's configurable slots. For *how it works now*, read the
living docs above — they are authoritative; this file only records the decisions.

## Goal

Turn devforge's phases into config-driven **slots** filled by real, reused skills, with
everything **shipped in-repo** so the loop runs with nothing installed.

## Decisions

1. **Vendor, don't depend.** Installing plugins (superpowers etc.) is painful and must
   never be required. Every slot engine is copied verbatim into
   `.claude/skills/_vendored/` and committed; installed plugins are only ever an optional
   `.devforge/config.local.json` override. A no-install guard test enforces this.

2. **Slots, chosen by config.** Each phase is a role defined by the files it reads/writes;
   what fills it is `.devforge/config.json` (`use` + `model`). The oracle (tests/lint) is
   not a slot — it's the deterministic ground truth.

3. **Default engines:** validate ← `brainstorming`, architect ← `writing-plans`,
   implementer ← `feature-dev`, reviewers ← `staff-review` + `thermonuclear`,
   final_reviewers ← `code-review`.

4. **Multiple reviewers, different lenses, over the oracle.** Every iteration runs the
   oracle plus the `reviewers` list in parallel (independent subagents, blind to
   `claim.md` and to each other): `staff-review` = correctness/edges/tests,
   `thermonuclear` = maintainability/structure. After convergence, `final_reviewers`
   (`code-review`) run a fresh second-angle pass whose findings **feed back** into the
   loop until clean — consistent with devforge's "nothing reaches the gate
   noted-but-unhandled" rule.

5. **One universal dispatch contract, not per-skill adapters.** The first cut wrote a
   wrapper skill per engine; they were structurally identical, differing only in the
   engine path and a one-line scope note. Collapsed into a single dispatch contract in the
   orchestrator, parameterized by `roles` + `uses` data in `.devforge/registry.json`.
   Adding/swapping an engine is a registry edit, not a new file.

6. **File-marker gate is the spine; plan-mode is an optional CLI front-end.** The design
   gate uses `ExitPlanMode` for native approval when interactive, but always writes the
   `design.approved` marker underneath, so resumability and web/headless still work.

## Out of scope

- Configurable `explore` (stays orchestrator-owned).
- Vendoring domain skills (e.g. `dig`) — they stay in their target repo, now wired via a
  repo-level `.devforge/registry.json` merged over the base. See
  [`2026-06-20-repo-registry-merge-design.md`](2026-06-20-repo-registry-merge-design.md).
- Changing the oracle, the file contract, or the two-gate structure.
