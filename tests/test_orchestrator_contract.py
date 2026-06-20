from conftest import REPO_ROOT

ORCH = (REPO_ROOT / ".claude/skills/devforge/SKILL.md").read_text()


def test_orchestrator_reads_config_and_registry():
    assert "config.json" in ORCH
    assert "registry.json" in ORCH


def test_orchestrator_documents_per_reviewer_files():
    assert "review-<use>.md" in ORCH
    assert "final-review-<use>.md" in ORCH


def test_orchestrator_has_plan_mode_gate():
    assert "ExitPlanMode" in ORCH
    assert "plan_mode_gate" in ORCH


def test_orchestrator_keeps_marker_gates():
    assert "design.approved" in ORCH
    assert "merge.approved" in ORCH


def test_orchestrator_dispatches_reviewers_in_parallel():
    assert "parallel" in ORCH.lower()
    assert "final_reviewers" in ORCH


def test_orchestrator_uses_universal_dispatch_not_per_skill_adapters():
    # The simplification: one contract driven by the registry, no per-skill adapters.
    assert "Slot dispatch" in ORCH
    assert "registry.slot_roles" in ORCH and "registry.uses" in ORCH
    assert "no per-skill adapter" in ORCH.lower() or "no per-skill adapters" in ORCH.lower()


def test_no_per_skill_adapter_dirs_remain():
    skills = REPO_ROOT / ".claude/skills"
    leftover = [p.name for p in skills.glob("devforge-review-*")]
    leftover += [p.name for p in skills.glob("devforge-impl-*")]
    leftover += [p.name for p in skills.glob("devforge-validate-*")]
    leftover += [p.name for p in skills.glob("devforge-architect-*")]
    assert leftover == [], f"per-skill adapter dirs should be gone: {leftover}"
