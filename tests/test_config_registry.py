import sys

from conftest import REPO_ROOT, load_json

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_config import validate  # noqa: E402

REGISTRY = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
CONFIG = REPO_ROOT / ".claude/skills/devforge/config.default.json"


def test_default_config_is_valid():
    assert validate(load_json(CONFIG), REGISTRY) == []


def test_unknown_use_reported():
    bad = load_json(CONFIG)
    bad["slots"]["implementer"] = {"use": "nope"}
    errs = validate(bad, REGISTRY)
    assert any("nope" in e for e in errs)


def test_use_not_allowed_in_slot_reported():
    bad = load_json(CONFIG)
    bad["slots"]["reviewers"] = [{"use": "feature-dev"}]
    errs = validate(bad, REGISTRY)
    assert any("feature-dev" in e and "reviewers" in e for e in errs)


def test_duplicate_use_in_list_reported():
    bad = load_json(CONFIG)
    bad["slots"]["reviewers"] = [{"use": "staff-review"}, {"use": "staff-review"}]
    errs = validate(bad, REGISTRY)
    assert any("duplicate" in e.lower() for e in errs)


def test_empty_final_reviewers_is_valid():
    ok = load_json(CONFIG)
    ok["slots"]["final_reviewers"] = []
    assert validate(ok, REGISTRY) == []
