import json
import re

import jsonschema
import pytest
from conftest import REPO_ROOT, load_json

SCHEMA = load_json(REPO_ROOT / ".devforge/config.schema.json")
CONFIG = REPO_ROOT / ".devforge/config.json"


def test_default_config_matches_schema():
    jsonschema.validate(load_json(CONFIG), SCHEMA)


def test_schema_rejects_unknown_slot_key():
    bad = load_json(CONFIG)
    bad["slots"]["bogus"] = {"use": "x"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_schema_rejects_empty_reviewers_list():
    bad = load_json(CONFIG)
    bad["slots"]["reviewers"] = []
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)


def test_schema_allows_empty_final_reviewers_list():
    ok = load_json(CONFIG)
    ok["slots"]["final_reviewers"] = []
    jsonschema.validate(ok, SCHEMA)


def test_catalog_examples_are_valid():
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from validate_config import validate

    registry = load_json(REPO_ROOT / ".claude/skills/devforge/registry.base.json")
    catalog = REPO_ROOT / "docs/devforge-config.md"
    if not catalog.is_file():
        pytest.skip("catalog not written yet")
    md = catalog.read_text()
    blocks = re.findall(r"```json\n(.*?)```", md, re.S)
    cfgs = [json.loads(b) for b in blocks if '"slots"' in b]
    assert cfgs, "no example configs found in catalog"
    for c in cfgs:
        jsonschema.validate(c, SCHEMA)
        assert validate(c, registry) == []
