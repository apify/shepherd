import sys

from conftest import REPO_ROOT, load_json

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate_config import merge_registry, validate  # noqa: E402

BASE = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")


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


def test_stage_roles_always_from_base():
    repo = {"stage_roles": {"verify_request": "BOGUS"}, "uses": {}}
    merged = merge_registry(BASE, repo)
    assert merged["stage_roles"] == BASE["stage_roles"]


def test_none_repo_returns_base_uses_unchanged():
    merged = merge_registry(BASE, None)
    assert merged["uses"] == BASE["uses"]
    assert merged["stage_roles"] == BASE["stage_roles"]


def test_comment_and_other_keys_are_ignored():
    repo = {"$comment": "MCP-only engines; generic engines come from the base.", "uses": {}}
    merged = merge_registry(BASE, repo)
    assert "$comment" not in merged
    assert set(merged) == {"stage_roles", "uses"}


def test_merged_registry_validates_a_config_that_picks_a_repo_use():
    repo = {"uses": {"dig": {"roles": ["architect"], "engine": ".claude/skills/dig/SKILL.md", "scope": "x"}}}
    merged = merge_registry(BASE, repo)
    cfg = load_json(REPO_ROOT / ".claude/skills/devforge/config.default.json")
    cfg["stages"]["architect"] = {"use": "dig", "model": "opus"}
    assert validate(cfg, merged) == []
