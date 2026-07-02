"""Validate devforge config against the resolved registry.

Pure stdlib. Used by tests and CI; the orchestrator follows the same rules in prose
because it has no Python runtime on web. Keep both rule sets in sync.

Config stage values are objects like `{ "use": "<name>", "model": "<model>" }`. The
registry maps each stage to a role (`stage_roles`) and each `use` name to the roles it
may fill plus its engine and scope (`uses`). A `use` is valid in a stage when that
stage's role is listed in the use's `roles`.
"""
from __future__ import annotations

SINGLE_STAGES = (  # optional: absent means built-in, no engine
    "verify", "architect", "implementer", "success_criteria", "fulfillment",
)
LIST_STAGES = ("reviewers", "final_reviewers")


def merge_registry(base: dict, repo: dict | None) -> dict:
    """Overlay repo registry entries onto the shipped base.

    `stage_roles` always comes from the base because the stage-to-role map is fixed. A
    repo contributes `uses` only; entries with the same name shallow-override base
    entries. Other repo keys, such as `$comment`, are ignored.
    """
    uses = dict(base["uses"])
    if repo:
        uses.update(repo.get("uses", {}))
    return {"stage_roles": base["stage_roles"], "uses": uses}


def _check_use(stage: str, name: str, registry: dict, errs: list[str]) -> None:
    uses = registry["uses"]
    if name not in uses:
        errs.append(f"unknown use '{name}' in stage '{stage}'")
        return
    role = registry["stage_roles"][stage]
    roles = uses[name]["roles"]
    if role not in roles:
        errs.append(
            f"use '{name}' is not allowed in stage '{stage}' "
            f"(stage role '{role}'; use supports {roles})"
        )


def validate(config: dict, registry: dict) -> list[str]:
    """Return a list of human-readable error strings; empty means valid."""
    errs: list[str] = []
    stages = config.get("stages", {})
    for stage in SINGLE_STAGES:
        entry = stages.get(stage)
        if not entry:
            continue  # optional stage: built-in behavior, nothing to validate
        _check_use(stage, entry["use"], registry, errs)
    for stage in LIST_STAGES:
        entries = stages.get(stage)
        if entries is None:
            errs.append(f"missing stage '{stage}'")
            continue
        seen: set[str] = set()
        for entry in entries:
            name = entry["use"]
            if name in seen:
                errs.append(f"duplicate '{name}' in stage '{stage}'")
            seen.add(name)
            _check_use(stage, name, registry, errs)
    return errs


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    here = Path(__file__).resolve().parent.parent
    repo_cfg = here / ".devforge/config.json"
    default_cfg = here / ".claude/skills/devforge/config.default.json"
    cfg = json.loads((repo_cfg if repo_cfg.is_file() else default_cfg).read_text())
    base = json.loads((here / ".claude/skills/devforge/registry.base.json").read_text())
    repo_path = here / ".devforge/registry.json"
    repo = json.loads(repo_path.read_text()) if repo_path.is_file() else None
    reg = merge_registry(base, repo)
    problems = validate(cfg, reg)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("config OK")
