from conftest import REPO_ROOT, load_json

REGISTRY = load_json(REPO_ROOT / ".devforge/registry.json")
CONFIG = load_json(REPO_ROOT / ".devforge/config.json")

SLOTS = {"validate", "architect", "implementer", "reviewers", "final_reviewers"}
ROLES = {"validate", "architect", "implementer", "reviewer", "final_reviewer"}


def test_slot_roles_cover_every_slot():
    assert set(REGISTRY["slot_roles"]) == SLOTS


def test_every_slot_role_is_known():
    assert set(REGISTRY["slot_roles"].values()) == ROLES


def test_every_use_declares_known_roles():
    for name, spec in REGISTRY["uses"].items():
        for role in spec["roles"]:
            assert role in ROLES, f"use '{name}' has unknown role '{role}'"


def test_every_config_use_exists_in_registry():
    slots = CONFIG["slots"]
    names = [slots[s]["use"] for s in ("validate", "architect", "implementer")]
    names += [e["use"] for s in ("reviewers", "final_reviewers") for e in slots[s]]
    for name in names:
        assert name in REGISTRY["uses"], f"config uses '{name}' but registry has no such entry"
