from conftest import REPO_ROOT, load_json

REGISTRY = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
CONFIG = load_json(REPO_ROOT / ".claude/skills/devforge/config.default.json")

STAGES = {"verify_request", "architect", "implementer", "reviewers", "final_reviewers"}
ROLES = {"verify_request", "architect", "implementer", "reviewer", "final_reviewer"}


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
    names = [stages[s]["use"] for s in ("verify_request", "architect", "implementer")]
    names += [e["use"] for s in ("reviewers", "final_reviewers") for e in stages[s]]
    for name in names:
        assert name in REGISTRY["uses"], f"config uses '{name}' but registry has no such entry"
