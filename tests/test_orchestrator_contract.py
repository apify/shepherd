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


def test_orchestrator_uses_universal_dispatch_not_wrapper_skills():
    # The simplification: one contract driven by the registry, no wrapper skill per engine.
    assert "Slot dispatch" in ORCH
    assert "registry.slot_roles" in ORCH and "registry.uses" in ORCH
    assert "separate wrapper skill" in ORCH


def test_orchestrator_resolves_base_plus_repo_registry():
    assert "registry.base.json" in ORCH
    assert "fully-resolved registry" in ORCH
    # repo deltas are still the .devforge/registry.json the existing test checks for
    assert ".devforge/registry.json" in ORCH


def test_no_wrapper_skill_dirs_remain():
    skills = REPO_ROOT / ".claude/skills"
    leftover = [p.name for p in skills.glob("devforge-review-*")]
    leftover += [p.name for p in skills.glob("devforge-impl-*")]
    leftover += [p.name for p in skills.glob("devforge-validate-*")]
    leftover += [p.name for p in skills.glob("devforge-architect-*")]
    assert leftover == [], f"wrapper skill dirs should be gone: {leftover}"


def test_orchestrator_documents_oracle_commands():
    assert "oracle.commands" in ORCH
    assert "inferred fallback" in ORCH
    assert "non-mutating commands" in ORCH
    assert "lint:fix" in ORCH


def test_orchestrator_documents_dirty_worktree_protection():
    assert "git status --porcelain" in ORCH
    assert "pre-existing unrelated changes" in ORCH


def test_orchestrator_finish_step_is_specific():
    assert "Commit with a concise message derived from `task.md`" in ORCH
    assert "PR URL" in ORCH
