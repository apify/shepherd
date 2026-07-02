from conftest import REPO_ROOT, load_json

REGISTRY = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
CONFIG = load_json(REPO_ROOT / ".claude/skills/devforge/config.default.json")

SINGLE_STAGES = ("verify", "architect", "implementer", "success_criteria", "fulfillment")
STAGES = set(SINGLE_STAGES) | {"reviewers", "final_reviewers"}
ROLES = set(SINGLE_STAGES) | {"reviewer", "final_reviewer"}


def test_stage_roles_cover_every_stage():
    assert set(REGISTRY["stage_roles"]) == STAGES


def test_every_stage_role_is_known():
    assert set(REGISTRY["stage_roles"].values()) == ROLES


def test_every_use_declares_known_roles():
    for name, spec in REGISTRY["uses"].items():
        for role in spec["roles"]:
            assert role in ROLES, f"use '{name}' has unknown role '{role}'"


def test_every_config_use_exists_in_registry():
    stages = CONFIG["stages"]
    names = [stages[s]["use"] for s in SINGLE_STAGES if s in stages]
    names += [e["use"] for s in ("reviewers", "final_reviewers") for e in stages[s]]
    for name in names:
        assert name in REGISTRY["uses"], f"config uses '{name}' but registry has no such entry"


def test_no_scope_references_a_retired_run_filename():
    # Scope strings drift when run files get renamed; catch retired names early.
    import re

    retired = ("_verified_task.md", "design.md", "task.md")
    for name, spec in REGISTRY["uses"].items():
        scope = spec.get("scope", "")
        for stale in retired:
            # allow current names that end the same way, e.g. 2-design.md
            hits = re.findall(rf"(?<![\w/-]){re.escape(stale)}", scope)
            assert not hits, f"use '{name}' scope references retired file '{stale}'"
