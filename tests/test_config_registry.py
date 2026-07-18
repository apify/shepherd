import sys

from conftest import REPO_ROOT, load_json

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_config import validate  # noqa: E402

REGISTRY = load_json(REPO_ROOT / ".claude/skills/shepherd/registry.base.json")
CONFIG = REPO_ROOT / ".claude/skills/shepherd/config.default.json"


def test_default_config_is_valid():
    assert validate(load_json(CONFIG), REGISTRY) == []


def test_unknown_use_reported():
    bad = load_json(CONFIG)
    bad["stages"]["implementer"] = {"use": "nope"}
    errs = validate(bad, REGISTRY)
    assert any("nope" in e for e in errs)


def test_use_not_allowed_in_stage_reported():
    bad = load_json(CONFIG)
    bad["stages"]["reviewers"] = [{"use": "feature-dev"}]
    errs = validate(bad, REGISTRY)
    assert any("feature-dev" in e and "reviewers" in e for e in errs)


def test_duplicate_use_in_list_reported():
    bad = load_json(CONFIG)
    bad["stages"]["reviewers"] = [{"use": "staff-review"}, {"use": "staff-review"}]
    errs = validate(bad, REGISTRY)
    assert any("duplicate" in e.lower() for e in errs)


def test_empty_final_reviewers_is_valid():
    ok = load_json(CONFIG)
    ok["stages"]["final_reviewers"] = []
    assert validate(ok, REGISTRY) == []


def test_model_only_single_stage_is_valid():
    ok = load_json(CONFIG)
    ok["stages"]["implementer"] = {"model": "auto"}
    assert validate(ok, REGISTRY) == []


def test_single_stage_needs_use_or_model_reported():
    bad = load_json(CONFIG)
    bad["stages"]["implementer"] = {}
    errs = validate(bad, REGISTRY)
    assert any("implementer" in e for e in errs)


def test_reviewer_without_use_reported():
    bad = load_json(CONFIG)
    bad["stages"]["reviewers"] = [{"model": "sonnet"}]
    errs = validate(bad, REGISTRY)
    assert any("reviewers" in e and "use" in e for e in errs)


def test_default_config_pins_ponytail_to_sonnet():
    # A one-line deletion lens doesn't earn opus; sonnet stays the review floor because
    # under zero-findings convergence a hallucinated nit costs a full fix round.
    finals = {e["use"]: e.get("model") for e in load_json(CONFIG)["stages"]["final_reviewers"]}
    assert finals["ponytail-review"] == "sonnet"
