# Repo-level registry merge — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a target repo bring its own slot engines into devforge's gated loop by shallow-merging that repo's `.devforge/registry.json` over a base registry that ships with the skill — keeping all domain specifics out of the generic devforge repo.

**Architecture:** Add one pure-Python primitive, `merge_registry(base, repo)`, that overlays a repo's `uses` onto the shipped base (`slot_roles` always from base; repo wins on name collision; non-`uses` keys ignored). Relocate the base registry from `.devforge/registry.json` to `.claude/skills/devforge/registry.base.json` so it travels with the skill install. Teach the orchestrator (prose in `SKILL.md`) to load base → merge repo deltas → resolve engine paths against the install (base) vs the repo root (deltas) → validate the merged registry → log the fully-resolved registry. The Python helper and the prose stay in sync; tests cover the helper and assert the prose.

**Tech Stack:** Python 3.13 stdlib + `pytest` + `jsonschema` (already in `tests/requirements.txt`). No runtime code ships — the orchestrator is an LLM following `SKILL.md`; the Python is for tests/CI only.

## Global Constraints

- **No domain knowledge in this repo.** No `dig`, `mcpc-tester`, or "MCP" strings in any committed devforge file. The merge primitive is placement- and domain-agnostic.
- **No-install guard holds.** Committed `.claude/`/`.devforge/` files must never reference plugin-cache paths (`plugins/cache`, `.claude/plugins`). Base engine paths stay under `.claude/skills/_vendored/`.
- **Python is pure stdlib** (`validate_config.py` line 1–11 contract). Tests may use `pytest`/`jsonschema`.
- **`slot_roles` is fixed** and always comes from the base; a repo registry contributes `uses` only.
- **Keep the helper and the orchestrator prose in sync** (`validate_config.py` docstring rule).

---

### Task 1: `merge_registry()` primitive

**Files:**
- Modify: `scripts/validate_config.py` (add `merge_registry`)
- Test: `tests/test_registry_merge.py` (create)

**Interfaces:**
- Produces: `merge_registry(base: dict, repo: dict | None) -> dict` — returns `{"slot_roles": base["slot_roles"], "uses": {**base_uses, **repo_uses}}`. `slot_roles` always from `base`; `repo["uses"]` overlays `base["uses"]`; a falsy `repo` (or one without `uses`) yields the base `uses` unchanged; keys other than `uses`/`slot_roles` on `repo` are ignored.
- Consumes: the existing `validate(config, registry) -> list[str]` (unchanged) — `merge_registry` output is a valid `registry` argument to it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_registry_merge.py`:

```python
import sys

from conftest import REPO_ROOT, load_json

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_config import merge_registry, validate  # noqa: E402

# Task 1 loads the base from its current location; Task 2 relocates this path
# (and the four other loaders) to .claude/skills/devforge/registry.base.json.
BASE = load_json(REPO_ROOT / ".devforge/registry.json")


def test_repo_use_is_added_to_base():
    repo = {"uses": {"dig": {"roles": ["architect"], "engine": ".claude/skills/dig/SKILL.md", "scope": "x"}}}
    merged = merge_registry(BASE, repo)
    assert "dig" in merged["uses"]
    assert set(BASE["uses"]).issubset(merged["uses"])
    assert len(merged["uses"]) == len(BASE["uses"]) + 1


def test_repo_use_overrides_base_use_by_name():
    repo = {"uses": {"staff-review": {"roles": ["reviewer"], "engine": "repo/sr.md", "scope": "z"}}}
    merged = merge_registry(BASE, repo)
    assert merged["uses"]["staff-review"]["engine"] == "repo/sr.md"
    assert merged["uses"]["staff-review"]["roles"] == ["reviewer"]


def test_slot_roles_always_from_base():
    repo = {"slot_roles": {"validate": "BOGUS"}, "uses": {}}
    merged = merge_registry(BASE, repo)
    assert merged["slot_roles"] == BASE["slot_roles"]


def test_none_repo_returns_base_uses_unchanged():
    merged = merge_registry(BASE, None)
    assert merged["uses"] == BASE["uses"]
    assert merged["slot_roles"] == BASE["slot_roles"]


def test_comment_and_other_keys_are_ignored():
    repo = {"$comment": "MCP-only engines; generic engines come from the base.", "uses": {}}
    merged = merge_registry(BASE, repo)
    assert "$comment" not in merged
    assert set(merged) == {"slot_roles", "uses"}


def test_merged_registry_validates_a_config_that_picks_a_repo_use():
    repo = {"uses": {"dig": {"roles": ["architect"], "engine": ".claude/skills/dig/SKILL.md", "scope": "x"}}}
    merged = merge_registry(BASE, repo)
    cfg = load_json(REPO_ROOT / ".devforge/config.json")
    cfg["slots"]["architect"] = {"use": "dig", "model": "opus"}
    assert validate(cfg, merged) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jirka/github/jirispilka/devforge && python -m pytest tests/test_registry_merge.py -v`
Expected: FAIL — `ImportError: cannot import name 'merge_registry'`. The import error confirms the function is missing.

- [ ] **Step 3: Add `merge_registry` to `scripts/validate_config.py`**

Insert directly after the module docstring's imports (after line 14, the `LIST_SLOTS = (...)` line), before `_check_use`:

```python
def merge_registry(base: dict, repo: dict | None) -> dict:
    """Overlay a repo's registry deltas onto the shipped base.

    `slot_roles` always comes from the base (the slot->role map is fixed). A repo
    contributes `uses` only; its entries shallow-override base entries with the same
    name. Other keys on `repo` (e.g. `$comment`) are ignored.
    """
    uses = dict(base["uses"])
    if repo:
        uses.update(repo.get("uses", {}))
    return {"slot_roles": base["slot_roles"], "uses": uses}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_registry_merge.py -v`
Expected: all six tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/validate_config.py tests/test_registry_merge.py
git commit -m "feat: add merge_registry primitive for base + repo registry overlay

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Relocate the base registry to ship with the skill

**Files:**
- Rename: `.devforge/registry.json` → `.claude/skills/devforge/registry.base.json` (via `git mv`, content unchanged)
- Modify: `scripts/validate_config.py:54-66` (the `__main__` block)
- Modify: `tests/test_config_registry.py:8` (registry load path)
- Modify: `tests/test_registry_shape.py:3` (registry load path)
- Modify: `tests/test_vendoring.py:5` (registry load path)
- Modify: `tests/test_config_schema.py:42` (registry load path in catalog test)
- Modify: `tests/test_registry_merge.py` (the `BASE = ...` load path from Task 1)

**Interfaces:**
- Consumes: `merge_registry` (Task 1).
- Produces: base registry resolvable at `.claude/skills/devforge/registry.base.json`; `python scripts/validate_config.py` loads base + optional `.devforge/registry.json` delta, merges, validates `.devforge/config.json`.

- [ ] **Step 1: Move the base registry file (content unchanged)**

```bash
cd /home/jirka/github/jirispilka/devforge
git mv .devforge/registry.json .claude/skills/devforge/registry.base.json
```

- [ ] **Step 2: Run the suite to see what the move broke**

Run: `python -m pytest tests -q`
Expected: FAIL — `test_config_registry.py`, `test_registry_shape.py`, `test_vendoring.py`, and the catalog test in `test_config_schema.py` raise `FileNotFoundError` on `.devforge/registry.json`. This lists exactly the loaders to update.

- [ ] **Step 3: Point the `__main__` block at base + optional repo delta**

Replace `scripts/validate_config.py:54-66` (the `if __name__ == "__main__":` block) with:

```python
if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    here = Path(__file__).resolve().parent.parent
    cfg = json.loads((here / ".devforge/config.json").read_text())
    base = json.loads((here / ".claude/skills/devforge/registry.base.json").read_text())
    repo_path = here / ".devforge/registry.json"
    repo = json.loads(repo_path.read_text()) if repo_path.is_file() else None
    reg = merge_registry(base, repo)
    problems = validate(cfg, reg)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("config OK")
```

- [ ] **Step 4: Update the four test loaders**

In `tests/test_config_registry.py:8`, change:
```python
REGISTRY = load_json(REPO_ROOT / ".devforge/registry.json")
```
to:
```python
REGISTRY = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
```

In `tests/test_registry_shape.py:3`, change:
```python
REGISTRY = load_json(REPO_ROOT / ".devforge/registry.json")
```
to:
```python
REGISTRY = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
```

In `tests/test_vendoring.py:5`, change:
```python
REGISTRY = load_json(REPO_ROOT / ".devforge/registry.json")
```
to:
```python
REGISTRY = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
```

In `tests/test_config_schema.py:42`, change:
```python
    registry = load_json(REPO_ROOT / ".devforge/registry.json")
```
to:
```python
    registry = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
```

In `tests/test_registry_merge.py`, change the `BASE = ...` line:
```python
BASE = load_json(REPO_ROOT / ".devforge/registry.json")
```
to:
```python
BASE = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
```
(and drop the two-line `# Task 1 loads...` comment above it — the relocation is now done).

- [ ] **Step 5: Run the full suite + the CLI**

Run: `python -m pytest tests -q && python scripts/validate_config.py`
Expected: all tests PASS (including all six in `test_registry_merge.py`); the CLI prints `config OK`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: ship base registry beside the skill as registry.base.json

The base now travels with the skill install instead of living in .devforge/;
a repo's .devforge/registry.json becomes an optional delta merged over it.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Teach the orchestrator the base + repo merge (prose)

**Files:**
- Modify: `.claude/skills/devforge/SKILL.md` (intro blockquote, File contract table, Setup "Load + validate config" bullet, Slot dispatch step 1)
- Test: `tests/test_orchestrator_contract.py` (add one assertion test)

**Interfaces:**
- Consumes: the behavior from Tasks 1–2 (base + repo merge, two-root path resolution).
- Produces: orchestrator prose that names `registry.base.json`, describes the merge, the two-root path resolution, and logging the fully-resolved registry — asserted by the contract test.

- [ ] **Step 1: Write the failing contract test**

Append to `tests/test_orchestrator_contract.py`:

```python
def test_orchestrator_resolves_base_plus_repo_registry():
    assert "registry.base.json" in ORCH
    assert "fully-resolved registry" in ORCH
    # repo deltas are still the .devforge/registry.json the existing test checks for
    assert ".devforge/registry.json" in ORCH
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_orchestrator_contract.py::test_orchestrator_resolves_base_plus_repo_registry -v`
Expected: FAIL — `assert "registry.base.json" in ORCH` is False (SKILL.md not yet updated).

- [ ] **Step 3: Update the intro blockquote**

In `.claude/skills/devforge/SKILL.md`, find:
```
> contract (see *Slot dispatch*) drives every engine, parameterized by
> `.devforge/registry.json`. The default slots: validate ← `brainstorming`, architect ←
```
Replace the first sentence's tail so it reads:
```
> contract (see *Slot dispatch*) drives every engine, parameterized by the **resolved
> registry**: a base registry shipped beside this skill (`registry.base.json`) shallow-merged
> with an optional `.devforge/registry.json` the current repo may add. The default slots:
> validate ← `brainstorming`, architect ←
```

- [ ] **Step 4: Update the File contract table**

Find the row:
```
| `registry.json` | tool | orchestrator | yes |
```
Replace with two rows:
```
| `registry.base.json` (ships beside the skill) | tool | orchestrator | installed |
| `registry.json` (repo deltas, optional) | repo owner | orchestrator | yes |
```

- [ ] **Step 5: Update the Setup "Load + validate config" bullet**

Find the sub-bullet:
```
  - **Validate** the resolved config against `.devforge/registry.json` (the rules
```
Insert a new sub-bullet immediately before it, and change the validate target. The block becomes:
```
  - **Resolve the registry (base + repo deltas):** load the **base registry** shipped beside
    this skill at `registry.base.json` — its `uses` engine paths resolve relative to the
    devforge **install**. If the current repo has `.devforge/registry.json`, **shallow-merge
    its `uses` over the base** (repo wins on name collision; `slot_roles` always comes from the
    base; non-`uses` keys such as `$comment` are ignored). A repo `use`'s engine path resolves
    relative to the **repo root**. A repo with no `registry.json` runs on the base alone.
  - **Validate** the resolved config against the **resolved (merged) registry** (the rules
```
Then find the Setup bullet's closing line:
```
    plan_mode_gate` (default true). Record the resolved config in
    `progress.md`.
```
Replace with:
```
    plan_mode_gate` (default true). Record the resolved config **and the fully-resolved
    registry** (every `use` → its resolved engine path) in `progress.md`.
```

- [ ] **Step 6: Update Slot dispatch step 1**

Find:
```
1. Resolve `role = registry.slot_roles[S]`, and `engine = registry.uses[U].engine`,
   `scope = registry.uses[U].scope`.
```
Replace with:
```
1. Resolve `role = registry.slot_roles[S]`, and `engine = registry.uses[U].engine`,
   `scope = registry.uses[U].scope` (against the **resolved** registry). `engine` resolves
   relative to the devforge **install** for a base `use`, or relative to the **repo root** for
   a `use` that came from the repo's `.devforge/registry.json`.
```

- [ ] **Step 7: Run the contract suite**

Run: `python -m pytest tests/test_orchestrator_contract.py -v`
Expected: all PASS, including the existing `test_orchestrator_reads_config_and_registry` (still true — `.devforge/registry.json` is named) and the new test.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/devforge/SKILL.md tests/test_orchestrator_contract.py
git commit -m "feat: orchestrator resolves base + repo registry merge

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Document the layering + per-repo domain-engine recipe

**Files:**
- Modify: `docs/devforge-config.md` (add a "Base + repo registries" section + a domain-engine recipe)
- Modify: `docs/superpowers/specs/2026-06-19-configurable-slots-design.md` (out-of-scope line → point here)
- Test: `tests/test_config_schema.py::test_catalog_examples_are_valid` (must stay green — see note)

**Interfaces:**
- Consumes: behavior from Tasks 1–3.
- Produces: living-doc coverage for the merge, `$comment`, the resolved-registry log, and the recipe. No new code.

- [ ] **Step 1: Add the "Base + repo registries" section to `docs/devforge-config.md`**

Insert this section immediately before the existing `## Overrides & validation` section:

````markdown
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
````

> **Note for the implementer:** the two examples above are fenced as ` ```jsonc `, NOT ` ```json `. This is deliberate — `test_catalog_examples_are_valid` only extracts ` ```json ` blocks and validates them against the **base** registry, where `dig`/`mcpc-tester` do not exist. Keeping these as `jsonc` keeps that test green. Do not change the fence to `json`.

- [ ] **Step 2: Update the configurable-slots design record**

In `docs/superpowers/specs/2026-06-19-configurable-slots-design.md`, find the out-of-scope bullet:
```
- Vendoring domain skills (e.g. `dig`) — they stay in their target repo as optional
  `config.local.json` swaps.
```
Replace with:
```
- Vendoring domain skills (e.g. `dig`) — they stay in their target repo, now wired via a
  repo-level `.devforge/registry.json` merged over the base. See
  [`2026-06-20-repo-registry-merge-design.md`](2026-06-20-repo-registry-merge-design.md).
```

- [ ] **Step 3: Verify the catalog test still passes**

Run: `python -m pytest tests/test_config_schema.py -v`
Expected: PASS — `test_catalog_examples_are_valid` validates only the generic ` ```json ` examples already in the doc against the base; the new ` ```jsonc ` domain examples are not extracted.

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest tests -q && python scripts/validate_config.py`
Expected: all PASS; CLI prints `config OK`.

- [ ] **Step 5: Commit**

```bash
git add docs/devforge-config.md docs/superpowers/specs/2026-06-19-configurable-slots-design.md
git commit -m "docs: document base + repo registry layering and domain-engine recipe

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage** (against `2026-06-20-repo-registry-merge-design.md`):
- Decision 2 (base + repo shallow-merge, uses-only, repo wins) → Task 1 (`merge_registry`) + Task 3 (prose).
- Decision 3 (two-root path resolution) → Task 3 (Setup + Slot dispatch prose). *Note: path resolution is orchestrator prose, not Python — the LLM resolves paths at runtime; there is no code to unit-test, so it is covered by the contract test asserting the prose exists.*
- Decision 4 (minimal footprint + `$comment` + resolved-registry log) → Task 1 (`$comment` ignored), Task 3 (log line + contract assertion), Task 4 (docs).
- "Relocate base registry to ship with the skill" → Task 2.
- Schema/validation (`$comment` tolerated; validate the merged registry) → Task 1 tests + Task 2 `__main__`.
- Docs + configurable-slots out-of-scope update → Task 4.
- `mcpc-tester` multi-spot placement → Task 4 recipe (reviewers/final_reviewers/both). It is config-only and needs no devforge code, consistent with the spec.

**Placeholder scan:** No TBD/TODO; every code/prose step shows the exact content. The one spec deferral (base-file location) is now resolved to `.claude/skills/devforge/registry.base.json`.

**Type consistency:** `merge_registry(base, repo)` signature and its `{"slot_roles", "uses"}` return shape are used identically in Task 1's tests, Task 2's `__main__`, and Task 3's prose. The base file path `.claude/skills/devforge/registry.base.json` is identical across Tasks 1, 2, and 3.

## Out of scope (this plan)

- Authoring `apify-mcp-server`'s actual `.devforge/registry.json` + `config.json` — a follow-up in that repo (it can itself be run through devforge), and the placement choices are the user's per-feature call.
- Any change to the oracle, the file contract beyond the registry row, the two gates, or `config.local.json` behavior.
