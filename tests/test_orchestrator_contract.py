from conftest import REPO_ROOT

ORCH = (REPO_ROOT / ".claude/skills/devforge/SKILL.md").read_text()
APPROVE_DESIGN = (
    REPO_ROOT / ".claude/skills/devforge-approve-design/SKILL.md"
).read_text()


def test_orchestrator_reads_config_and_registry():
    assert "config.json" in ORCH
    assert "registry.json" in ORCH


def test_orchestrator_skill_stays_compact():
    # Keep the orchestrator readable, but do not force removal of operational guidance.
    assert len(ORCH.splitlines()) <= 300


def test_orchestrator_documents_per_reviewer_files():
    assert "review-<use>.md" in ORCH
    assert "final-review-<use>.md" in ORCH


def test_orchestrator_has_plan_mode_gate():
    assert "ExitPlanMode" in ORCH
    assert "plan_mode_gate" in ORCH


def test_orchestrator_keeps_the_two_marker_gates():
    # Design (before source edits) and create-PR (before git writes) are the only markers.
    assert "_design.approved" in ORCH
    assert "_create_pr.approved" in ORCH


def test_orchestrator_has_no_triage_gate():
    # Triage flows into design; it never waits on an approval marker.
    assert "triage.approved" not in ORCH
    assert "TRIAGE GATE" not in ORCH
    assert "Triage has no gate" in ORCH
    assert "DEFER or DECLINE" in ORCH


def test_orchestrator_has_triage_phase_before_design():
    assert "### 1. Triage" in ORCH
    assert "PROCEED | DEFER | DECLINE" in ORCH
    assert ORCH.index("### 1. Triage") < ORCH.index("### 2. Verify request")
    assert ORCH.index("### 1. Triage") < ORCH.index("### 5. Design gate")


def test_orchestrator_persists_raw_request_before_triage():
    assert "_user_request.md" in ORCH
    assert "Write it verbatim to" in ORCH
    assert ORCH.index("_user_request.md") < ORCH.index("### 1. Triage")
    assert "`verify_request` | `_user_request.md`, `1-triage.md`" in ORCH


def test_orchestrator_uses_flat_prefixed_layout():
    # Two human-facing files are numbered; internal routing files use an underscore.
    assert "1-triage.md" in ORCH
    assert "2-design.md" in ORCH
    for internal in ("_user_request.md", "_verified_task.md", "_request_fact_check.md",
                     "_state.json", "_panel.json", "_progress.md"):
        assert internal in ORCH


def test_orchestrator_documents_why_files_are_separate():
    # The per-stage file split is the context-routing / reviewer-independence mechanism.
    assert "context" in ORCH.lower()
    assert "independen" in ORCH.lower()


def test_orchestrator_selects_review_panel_at_design_gate():
    assert "state.panel" in ORCH
    assert "_panel.json" in ORCH
    assert "subset of the configured roster" in ORCH


def test_approve_design_records_the_approved_panel():
    assert "_panel.json" in APPROVE_DESIGN
    assert 'state["panel"] = panel' in APPROVE_DESIGN
    assert 'state["phase"] = "inner-loop"' in APPROVE_DESIGN
    assert 'state["iteration"] = 1' in APPROVE_DESIGN


def test_approve_design_routes_review_only_runs_to_review_mode():
    assert "state_review_only = state.get" in APPROVE_DESIGN
    assert "review-only" in APPROVE_DESIGN
    assert 'state["phase"] = "review-run"' in APPROVE_DESIGN
    assert 'state["phase"] = "inner-loop"' in APPROVE_DESIGN


def test_orchestrator_tracks_resumable_post_design_phases():
    for phase in ("inner-loop", "final-review", "final-reopen", "create-pr"):
        assert phase in ORCH
    assert 'state.phase="create-pr"' in ORCH


def test_implementer_reads_validated_spec_not_only_design():
    assert (
        "| `implementer` | `_verified_task.md`, `_request_fact_check.md`, `2-design.md`"
        in ORCH
    )


def test_orchestrator_has_complexity_rubric_with_numbers():
    assert "Complexity rubric" in ORCH
    assert "Blast-radius override" in ORCH
    for tier in ("trivial", "small", "medium", "large"):
        assert tier in ORCH


def test_orchestrator_reopen_reruns_only_final_reviewers():
    assert "re-runs ONLY the final" in ORCH


def test_orchestrator_dispatches_reviewers_in_parallel():
    assert "parallel" in ORCH.lower()
    assert "final_reviewers" in ORCH


def test_orchestrator_has_first_class_review_mode():
    # Review-only tasks skip implement, run the panel on the existing diff, stop at findings.
    assert "Review mode" in ORCH
    assert "review-only" in ORCH
    assert "do NOT implement" in ORCH


def test_orchestrator_accept_approves_revise_iterates_no_self_approve():
    # Contract: a human accepting the plan IS approval; reject/edit iterates the design;
    # the agent never self-approves, and a tool error / "continue" message is never approval.
    assert "Never self-approve a gate" in ORCH
    assert "accepting the plan" in ORCH
    assert "Revise" in ORCH
    assert "iterat" in ORCH.lower()
    assert "only approval signal" in ORCH
    assert "never infer" in ORCH.lower()


def test_orchestrator_create_pr_is_chat_confirm_not_plan_mode():
    assert "create-PR confirm" in ORCH
    assert "commit & open PR?" in ORCH
    assert "No plan mode" in ORCH


def test_orchestrator_design_is_short_major_changes_only():
    assert "What we're solving" in ORCH
    assert "never an exhaustive file list" in ORCH


def test_orchestrator_uses_universal_dispatch_not_wrapper_skills():
    assert "Stage dispatch" in ORCH
    assert "registry.stage_roles" in ORCH and "registry.uses" in ORCH
    assert "separate wrapper skill" in ORCH


def test_no_wrapper_skill_dirs_remain():
    skills = REPO_ROOT / ".claude/skills"
    leftover = [p.name for p in skills.glob("devforge-review-*")]
    leftover += [p.name for p in skills.glob("devforge-impl-*")]
    leftover += [p.name for p in skills.glob("devforge-validate-*")]
    leftover += [p.name for p in skills.glob("devforge-architect-*")]
    assert leftover == [], f"wrapper skill dirs should be gone: {leftover}"


def test_orchestrator_resolves_base_plus_repo_registry():
    assert "registry.base.json" in ORCH
    assert "fully-resolved registry" in ORCH
    assert ".devforge/registry.json" in ORCH


def test_orchestrator_documents_oracle_commands():
    assert "oracle.commands" in ORCH
    assert "inferred fallback" in ORCH
    assert "non-mutating commands" in ORCH
    assert "lint:fix" in ORCH


def test_orchestrator_documents_dirty_worktree_protection():
    assert "git status --porcelain" in ORCH
    assert "pre-existing unrelated changes" in ORCH


def test_orchestrator_finish_writes_plain_commit_and_pr():
    # Plain PR body: what / how / alternatives, never obvious-diff narration.
    assert "Alternatives considered" in ORCH
    assert "obvious from the diff" in ORCH
    assert "PR URL" in ORCH
