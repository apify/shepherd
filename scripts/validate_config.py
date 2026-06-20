"""Validate a devforge config against the registry.

Pure stdlib. Used by tests/CI; the orchestrator follows the same rules in prose
(it has no Python runtime on web). Keep the two in sync.

Config slot values are objects `{ "use": "<name>", "model": "<model>" }`. The registry
maps each slot to a role (`slot_roles`) and each `use` name to the roles it may fill
plus its engine + scope (`uses`). A `use` is valid in a slot when that slot's role is in
the use's `roles`.
"""
from __future__ import annotations

SINGLE_SLOTS = ("validate", "architect", "implementer")
LIST_SLOTS = ("reviewers", "final_reviewers")


def _check_use(slot: str, name: str, registry: dict, errs: list[str]) -> None:
    uses = registry["uses"]
    if name not in uses:
        errs.append(f"unknown use '{name}' in slot '{slot}'")
        return
    role = registry["slot_roles"][slot]
    roles = uses[name]["roles"]
    if role not in roles:
        errs.append(f"'{name}' is not allowed in slot '{slot}' (role '{role}'; "
                    f"it fills roles {roles})")


def validate(config: dict, registry: dict) -> list[str]:
    """Return a list of human-readable error strings; empty means valid."""
    errs: list[str] = []
    slots = config.get("slots", {})
    for slot in SINGLE_SLOTS:
        entry = slots.get(slot)
        if not entry:
            errs.append(f"missing slot '{slot}'")
            continue
        _check_use(slot, entry["use"], registry, errs)
    for slot in LIST_SLOTS:
        entries = slots.get(slot)
        if entries is None:
            errs.append(f"missing slot '{slot}'")
            continue
        seen: set[str] = set()
        for entry in entries:
            name = entry["use"]
            if name in seen:
                errs.append(f"duplicate '{name}' in slot '{slot}'")
            seen.add(name)
            _check_use(slot, name, registry, errs)
    return errs


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    cfg = json.loads((root / ".devforge/config.json").read_text())
    reg = json.loads((root / ".devforge/registry.json").read_text())
    problems = validate(cfg, reg)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("config OK")
