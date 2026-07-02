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
    assert len(ORCH.splitlines()) <= 340


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
    # Triage flows onward; it never waits on an approval marker.
    assert "triage.approved" not in ORCH
    assert "TRIAGE GATE" not in ORCH
    assert "Triage has no gate" in ORCH
    assert "DEFER or DECLINE" in ORCH


def test_pipeline_order_triage_verify_design_gate():
    assert "### 1. Triage" in ORCH
    assert "PROCEED | DEFER | DECLINE" in ORCH
    assert (ORCH.index("### 1. Triage")
            < ORCH.index("### 2. Verify")
            < ORCH.index("### 3. Design")
            < ORCH.index("### 4. Design gate"))


def test_orchestrator_routes_subagents_judge():
    # Core principle: the orchestrator never authors a judgment file.
    assert "The orchestrator routes; subagents judge" in ORCH
    assert "never writes a judgment file" in ORCH


def test_verify_stage_owns_the_claim_ledger():
    # Always-on verify subagent; ledger is authoritative and never empty.
    assert "_request_fact_check.md" in ORCH
    assert "VALID | STALE | LIKELY-FIXED | UNVERIFIABLE" in ORCH
    assert "never empty" in ORCH
    assert "Verify runs on every run" in ORCH


def test_orchestrator_persists_raw_request_before_triage():
    assert "_user_request.md" in ORCH
    assert "Write it verbatim to" in ORCH
    assert ORCH.index("_user_request.md") < ORCH.index("### 1. Triage")
    assert "| `architect` | `_user_request.md`, `1-triage.md`" in ORCH


def test_orchestrator_uses_flat_prefixed_layout():
    # Numbered files are human-facing; internal routing files use an underscore.
    assert "1-triage.md" in ORCH
    assert "2-design.md" in ORCH
    assert "3-success-criteria.md" in ORCH
    for internal in ("_user_request.md", "_request_fact_check.md", "_codebase_map.md",
                     "_design_feedback.md", "_state.json", "_panel.json", "_progress.md"):
        assert internal in ORCH


def test_orchestrator_documents_why_files_are_separate():
    # The per-stage file split is the context-routing / judgment-independence mechanism.
    assert "context" in ORCH.lower()
    assert "independen" in ORCH.lower()


def test_design_is_product_first():
    assert "Product first, implementation second" in ORCH
    assert "## How it will work" in ORCH
    assert "product questions first" in ORCH


def test_success_criteria_are_blind():
    # Architect never reads criteria; criteria author never sees the solution.
    assert "architect never reads it" in ORCH
    assert "never sees the solution" in ORCH
    # Criteria author gets only the pasted product sections.
    assert "\"What we're solving\" and \"How it will work\" sections" in ORCH


def test_design_iteration_uses_feedback_file_and_revision_passes():
    assert "### 3. Design" in ORCH
    assert "one question at a time" in ORCH
    assert "recommended answer" in ORCH
    assert "Open questions is empty" in ORCH
    assert "Decisions" in ORCH
    # Batched rounds; the orchestrator writes only the feedback transcript, verbatim.
    assert "Batch a round of answers" in ORCH
    assert "verbatim" in ORCH and "_design_feedback.md" in ORCH
    # Architect re-runs revise with prior context instead of re-drafting.
    assert "revision pass" in ORCH
    assert "every rewrite is a subagent's" in ORCH


def test_explorer_writes_a_reused_codebase_map():
    assert "_codebase_map.md" in ORCH
    assert "devforge-code-explorer" in ORCH


def test_orchestrator_selects_review_panel_at_design_gate():
    assert "state.panel" in ORCH
    assert "_panel.json" in ORCH
    assert "subset of the configured roster" in ORCH


def test_design_gate_approves_design_criteria_and_panel():
    assert "Approval covers all three" in ORCH
    assert "3-success-criteria.md" in APPROVE_DESIGN


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


def test_approve_design_review_only_parse_accepts_colon_and_question_mark():
    assert "review-only[?:]" in APPROVE_DESIGN


def test_orchestrator_tracks_resumable_phases():
    assert "`triage`, `verify`, `design`" in ORCH
    for phase in ("inner-loop", "final-review", "review-run", "create-pr"):
        assert phase in ORCH
    assert 'state.phase="create-pr"' in ORCH
    # A finished run is terminal; resume must not re-commit.
    assert 'state.phase="done"' in ORCH


def test_design_gate_wait_state_is_resumable():
    # Waiting at the gate is phase=design-gate without the marker; resume re-presents.
    assert "re-present the design + panel" in ORCH


def test_orchestrator_checks_approved_commit_on_resume():
    assert "approved_commit" in ORCH


def test_orchestrator_archives_previous_run_on_fresh_start():
    assert ".devforge/archive/" in ORCH


def test_setup_writes_run_gitignore():
    assert ".devforge/.gitignore" in ORCH


def test_orchestrator_has_complexity_rubric_with_numbers():
    assert "Complexity rubric" in ORCH
    assert "Blast-radius override" in ORCH
    for tier in ("trivial", "small", "medium", "large"):
        assert tier in ORCH


def test_orchestrator_dispatches_reviewers_in_parallel():
    assert "parallel" in ORCH.lower()
    assert "final_reviewers" in ORCH


def test_dispatched_stages_run_non_interactively():
    assert "non-interactively" in ORCH
    assert "record open questions in your output file" in ORCH


def test_reviewers_receive_pasted_content_not_file_access():
    assert "pasted content" in ORCH
    assert "never file access" in ORCH


def test_orchestrator_converges_on_severity():
    # No open blocker/major; minor/nit fixed or skipped with a reason, skips shown at confirm.
    assert "blocker" in ORCH and "major" in ORCH
    assert "skipped with a specific reason" in ORCH
    assert "every skipped finding with its reason" in ORCH


def test_fulfillment_check_gates_the_pr():
    # An explicit criteria-vs-reality check runs before the create-PR confirm.
    assert "fulfillment.md" in ORCH
    assert "MET | NOT MET" in ORCH or "MET \\| NOT MET" in ORCH
    assert "reopens the inner loop" in ORCH
    assert "No PR without fulfillment" in ORCH


def test_orchestrator_has_first_class_review_mode():
    # Review-only tasks skip implement, run the panel on the existing diff, stop at findings.
    assert "Review mode" in ORCH
    assert "review-only" in ORCH
    assert "do NOT implement" in ORCH
    # A follow-up fix run must not collide with the review-run artifacts.
    assert "next free `iter-N`" in ORCH


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
    assert "no plan mode" in ORCH.lower()


def test_orchestrator_design_is_short_major_changes_only():
    assert "What we're solving" in ORCH
    assert "never an exhaustive file list" in ORCH


def test_orchestrator_uses_universal_dispatch_not_wrapper_skills():
    assert "Stage dispatch" in ORCH
    assert "registry.stage_roles" in ORCH and "registry.uses" in ORCH
    assert "separate wrapper skill" in ORCH
    # Engines are optional: a stage without a configured use runs built-in.
    assert "no configured `use`" in ORCH


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
    # The run's own .devforge files must not trip the check.
    assert "ignore `.devforge/`" in ORCH


def test_orchestrator_finish_writes_plain_commit_and_pr():
    # Plain PR body: what / how / alternatives, never obvious-diff narration.
    assert "Alternatives considered" in ORCH
    assert "obvious from the diff" in ORCH
    assert "PR URL" in ORCH
