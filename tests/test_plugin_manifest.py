"""Guard the plugin packaging: manifests valid, source resolves, skills present.

The repo ships as a Claude Code plugin via a marketplace whose single plugin uses
`source: "./.claude"` (so `.claude/` is the plugin root). These checks fail loudly if
a rename or manifest edit breaks discovery.
"""
from conftest import REPO_ROOT, load_json

MARKETPLACE = load_json(REPO_ROOT / ".claude-plugin/marketplace.json")
PLUGIN = load_json(REPO_ROOT / ".claude/.claude-plugin/plugin.json")

EXPECTED_SKILLS = {"devforge", "devforge-approve-design", "devforge-approve-merge"}


def test_plugin_manifest_names_devforge():
    assert PLUGIN["name"] == "devforge"


def test_marketplace_has_required_fields():
    assert MARKETPLACE["name"]
    assert MARKETPLACE["owner"]["name"]
    assert MARKETPLACE["plugins"], "marketplace lists no plugins"


def test_marketplace_entry_points_at_dot_claude():
    entry = next(p for p in MARKETPLACE["plugins"] if p["name"] == "devforge")
    assert entry["source"] == "./.claude"


def test_plugin_source_dir_holds_the_skills():
    # source is ./.claude → that dir is the plugin root → its skills/ holds the skill dirs.
    root = REPO_ROOT / ".claude"
    for skill in EXPECTED_SKILLS:
        assert (root / "skills" / skill / "SKILL.md").is_file(), \
            f"plugin skill '{skill}' missing under {root}/skills/"


def test_base_registry_ships_inside_the_plugin_root():
    # registry.base.json must sit beside the devforge skill so its ../_vendored paths resolve.
    assert (REPO_ROOT / ".claude/skills/devforge/registry.base.json").is_file()


def test_default_config_and_schema_ship_inside_the_plugin_root():
    skill = REPO_ROOT / ".claude/skills/devforge"
    assert (skill / "config.default.json").is_file()
    assert (skill / "config.schema.json").is_file()


def test_repo_does_not_duplicate_shipped_config_files():
    assert not (REPO_ROOT / ".devforge/config.json").exists()
    assert not (REPO_ROOT / ".devforge/config.schema.json").exists()
