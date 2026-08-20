import re

from conftest import REPO_ROOT, load_json

ORCH = (REPO_ROOT / ".claude/skills/shepherd/SKILL.md").read_text()
APPROVE_DESIGN = (
    REPO_ROOT / ".claude/skills/shepherd-approve-design/SKILL.md"
).read_text()

TEMPLATES_DIR = REPO_ROOT / ".claude/skills/shepherd/templates"
STANDING = (TEMPLATES_DIR / "standing-checks.md").read_text()
DESIGN = (TEMPLATES_DIR / "design.md").read_text()
FORMATS = (TEMPLATES_DIR / "formats.md").read_text()
REGISTRY = load_json(REPO_ROOT / ".claude/skills/shepherd/registry.base.json")


def test_orchestrator_reads_config_and_registry():
    assert "config.json" in ORCH
    assert "registry.json" in ORCH


def test_orchestrator_skill_stays_compact():
    # Keep the orchestrator readable, but do not force removal of operational guidance.
    # A readability guard, not a budget: never pay for a new rule by deleting a rule's rationale.
    assert len(ORCH.splitlines()) <= 500


def test_orchestrator_documents_per_reviewer_files():
    assert "review-<use>.md" in ORCH
    assert "final-review-<use>.md" in ORCH


def test_orchestrator_has_plan_mode_gate():
    assert "ExitPlanMode" in ORCH
    assert "plan_mode_gate" in ORCH


def test_orchestrator_keeps_the_two_marker_gates():
    # Design (before source edits) and create-PR (before delivery) are the only markers.
    assert "_design.approved" in ORCH
    assert "_create_pr.approved" in ORCH


def test_no_git_rules_beyond_the_gate():
    # The gate times the PR; git itself is not shepherd's to manage. History does the
    # bookkeeping: the reviewed diff is anchored at the design-gate commit, so mid-run
    # commits are normal and no pre-run dirty-tree ledger exists.
    assert "No git rules beyond the gate" in ORCH
    assert "git diff <base_commit>" in ORCH
    assert "before any git write" not in ORCH
    assert "predirty" not in ORCH


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
    assert "Product first, implementation second" in DESIGN
    assert "## How it will work" in DESIGN
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
    assert "## Decisions" in DESIGN
    # Batched rounds; the orchestrator writes only the feedback transcript, verbatim.
    assert "Batch a round of answers" in ORCH
    assert "verbatim" in ORCH and "_design_feedback.md" in ORCH
    # Architect re-runs revise with prior context instead of re-drafting.
    assert "revision pass" in ORCH
    assert "every rewrite is a subagent's" in ORCH
    # Trivial runs adopt recommended answers on "no objections" instead of a revision pass.
    assert "recommended answers stand" in ORCH


def test_explorer_writes_a_reused_codebase_map():
    assert "_codebase_map.md" in ORCH
    assert "shepherd-code-explorer" in ORCH


def test_orchestrator_selects_review_panel_at_design_gate():
    assert "state.panel" in ORCH
    assert "_panel.json" in ORCH
    assert "subset of the configured roster" in ORCH
    # Pre-gate stages resolve auto at dispatch; the gate records them, humans edit post-gate picks.
    assert "record of what ran" in ORCH


def test_design_gate_approves_design_criteria_and_panel():
    assert "Approval covers all three" in ORCH
    assert "3-success-criteria.md" in APPROVE_DESIGN


def test_approve_design_records_the_approved_panel():
    assert "_panel.json" in APPROVE_DESIGN
    assert 'state["panel"] = panel' in APPROVE_DESIGN
    assert 'state["phase"] = "inner-loop"' in APPROVE_DESIGN
    assert 'state["iteration"] = 1' in APPROVE_DESIGN


def test_approve_design_has_no_review_only_routing():
    # Review-only mode was removed; approval always routes to the inner loop.
    assert "review-run" not in APPROVE_DESIGN
    assert "review_only" not in APPROVE_DESIGN


def test_orchestrator_tracks_resumable_phases():
    assert "`triage`, `verify`, `design`" in ORCH
    for phase in ("inner-loop", "final-review", "create-pr"):
        assert phase in ORCH
    assert 'state.phase="create-pr"' in ORCH
    # A finished run is terminal; resume must not re-commit.
    assert 'state.phase="done"' in ORCH
    # Resume before the marker must re-establish fulfillment, never assume the stop was earned.
    assert "`phase=create-pr` without the marker" in ORCH


def test_design_gate_wait_state_is_resumable():
    # Waiting at the gate is phase=design-gate without the marker; resume re-presents.
    assert "re-present the design + panel" in ORCH


def test_orchestrator_checks_base_commit_on_resume():
    assert "base_commit" in ORCH


def test_orchestrator_archives_previous_run_on_fresh_start():
    assert ".shepherd/archive/" in ORCH


def test_setup_writes_run_gitignore():
    assert ".shepherd/.gitignore" in ORCH
    # Everything ignored, the .gitignore itself included — no untracked noise; sharing
    # config is a manual opt-out. Shepherd never stages .shepherd/ paths.
    assert "a single `*` line" in ORCH
    assert "never stages" in ORCH


def test_orchestrator_has_complexity_rubric_with_numbers():
    assert "Complexity rubric" in ORCH
    assert "Blast-radius override" in ORCH
    for tier in ("trivial", "small", "medium", "large"):
        assert tier in ORCH


def test_orchestrator_dispatches_reviewers_in_parallel():
    assert "parallel" in ORCH.lower()
    assert "final_reviewers" in ORCH
    # Fix rounds get fresh iter-N dirs; earlier rounds' evidence is never clobbered.
    assert "never overwrite an earlier round's files" in ORCH


def test_dispatched_stage_completion_is_disk_based():
    # A dispatched stage's output file on disk is the completion signal, independent of
    # dispatch mode (background vs blocking) and dispatch site (single or parallel fan-out) —
    # the orchestrator must never claim it's still waiting without checking disk first. When the
    # file is absent it reports the unknown honestly and never fabricates a status from turn count.
    assert "completion signal" in ORCH
    assert "output file on disk" in ORCH
    assert "Never report a dispatched stage as still running" in ORCH
    assert "status unknown; output not present" in ORCH
    assert 'Never infer "still running" or "stalled" from turn count or a human check-in' in ORCH


def test_dispatched_stages_run_non_interactively():
    assert "non-interactively" in ORCH
    assert "record open questions in your output file" in ORCH


def test_reviewers_receive_pasted_judgments_not_file_grants():
    # Blindness applies to judgments, not ground truth: .shepherd/ judgment
    # files are pasted into prompts, never granted; the repo stays readable.
    assert "pasted content" in ORCH
    assert "never granted" in ORCH
    assert "never to ground truth" in ORCH
    # The three always-on reviewer checks travel inside the dispatch template.
    assert "Standing checks:" in ORCH


def test_orchestrator_converges_on_zero_findings():
    # Every finding gets fixed, whatever its severity; nothing is skipped or deferred.
    assert "blocker" in ORCH and "major" in ORCH
    assert "every finding gets fixed" in ORCH
    assert "never skips or defers" in ORCH
    # Abandon is terminal: phase=done, and the tree is left for the human.
    assert "On abandon" in ORCH


def test_fulfillment_check_gates_the_pr():
    # An explicit criteria-vs-reality check runs before the create-PR confirm.
    assert "fulfillment.md" in ORCH
    assert "MET | NOT MET" in FORMATS
    assert "reopens the inner loop" in ORCH
    assert "No PR without fulfillment" in ORCH


def test_orchestrator_has_no_review_only_mode():
    # Review-only tasks are outside shepherd's implementation workflow. No dedicated
    # phase, triage field, or stage may remain.
    assert "review-run" not in ORCH
    assert "review-only" not in ORCH.lower()
    assert "review_only" not in ORCH


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
    # Engines are optional: a single stage with no `use` runs the built-in role.
    assert "with no `use`" in ORCH


def test_no_wrapper_skill_dirs_remain():
    skills = REPO_ROOT / ".claude/skills"
    leftover = [p.name for p in skills.glob("shepherd-review-*")]
    leftover += [p.name for p in skills.glob("shepherd-impl-*")]
    leftover += [p.name for p in skills.glob("shepherd-validate-*")]
    leftover += [p.name for p in skills.glob("shepherd-architect-*")]
    assert leftover == [], f"wrapper skill dirs should be gone: {leftover}"


def test_orchestrator_resolves_base_plus_repo_registry():
    assert "registry.base.json" in ORCH
    assert "fully-resolved registry" in ORCH
    assert ".shepherd/registry.json" in ORCH


def test_orchestrator_documents_oracle_commands():
    assert "oracle.commands" in ORCH
    assert "inferred fallback" in ORCH
    assert "non-mutating commands" in ORCH
    assert "lint:fix" in ORCH
    # The oracle's output is the test-results.txt reviewers and fulfillment read.
    assert "capturing output to `iter-N/test-results.txt`" in ORCH


def test_orchestrator_finish_writes_plain_commit_and_pr():
    # Short PR body: template headings filled briefly, else ≤3 bullets; no essay / diff narration.
    assert "three short bullets" in ORCH
    assert "What / Why / Notes" in ORCH
    assert "obvious from the diff" in ORCH
    assert "one short clause" in ORCH
    assert "PR URL" in ORCH


def test_open_questions_are_real_decisions():
    assert "real decisions only" in DESIGN
    assert "no filler" in DESIGN
    assert "no minimum or maximum" in DESIGN
    assert "Facts verifiable" in DESIGN


def test_design_iterate_grills_decisions():
    assert "Grill decisions" in ORCH
    assert "Look up facts yourself" in ORCH
    assert "Only decisions go to the human" in ORCH
    assert "a convention that settles" in ORCH
    assert "miss a real fork" in ORCH


def test_standing_checks_include_ai_slop():
    assert "comments longer than the" in STANDING
    assert "abnormal defensive" in STANDING
    assert "type-escape casts" in STANDING
    assert "early returns" in STANDING


def test_triage_defers_underspecified_requests():
    assert "DEFER an under-specified request" in ORCH
    assert "design settles solutions, not triage" in ORCH


def test_verify_checks_external_spec_claims():
    assert "facts outside the repo" in ORCH
    assert "not model memory" in FORMATS


def test_step_references_name_their_target():
    # Bare "step N" is ambiguous against numbered list items inside sections; every
    # cross-reference must name its target: "step 4 (Design gate)" or "(step 9, Finish)".
    # Dotted refs (step 5.3) are already unambiguous and exempt.
    bare = re.findall(r"step \d+(?!\.\d)(?!\s*[(,])", ORCH)
    assert bare == [], f"bare step references found: {bare}"


def test_step_headings_declare_their_phase():
    # Each procedure heading carries its _state.json phase so the prose vocabulary
    # and the state machine stay one system.
    headings = re.findall(r"^### \d+\..*$", ORCH, flags=re.M)
    assert len(headings) == 8
    missing = [h for h in headings if "`phase=" not in h]
    assert missing == [], f"headings without a phase annotation: {missing}"


def test_standing_checks_cover_new_arms_and_disclosure():
    assert "these three checks" in STANDING
    assert re.search(r"test-exercised on both\s+sides", STANDING)
    assert "input classes the old path handled" in STANDING
    assert "silently invert" in STANDING
    assert "conventions doc" in STANDING


def test_scope_split_and_followups_ledger():
    # Retained inline: the explicit gate-decision obligation on a non-empty Prerequisite
    # refactor, plus the followups ledger / approval pins — orchestrator-obeyed procedure.
    assert "Prerequisite refactor" in ORCH
    assert "explicit gate decision" in ORCH
    assert "never as the default" in ORCH
    assert "followups.md" in ORCH
    assert "pre-existing" in ORCH
    assert "never instructs reviewers not to report" in ORCH
    assert "only on human approval" in ORCH
    assert "never an issue without approval" in ORCH


def test_design_scope_split_wording_and_fog_test():
    # The scope-split explanatory paragraph (minus the gate-decision sentences above) and the
    # fog-test wayfinder borrowing live in the architect's format template.
    assert "## Scope split" in DESIGN
    assert "Prerequisite refactor" in DESIGN
    assert "refactor-separation" in DESIGN
    assert "record it as fog" in DESIGN
    assert "never a forced Open question" in DESIGN


def test_followups_stage_is_integrated_with_configuration_and_resume():
    assert "`fulfillment`, `followups`) may be absent" in ORCH
    assert "fulfillment or followups" in ORCH
    assert "`iter-N/followups.md`" in ORCH
    assert "fulfillment, followups)" in ORCH
    assert '"followups": "sonnet"' in ORCH


def test_pr_body_claims_are_verified():
    assert "must match the final oracle run" in ORCH
    assert "stale count or nonexistent reference" in ORCH


def test_verify_delta_mode_on_rerun():
    assert "delta mode" in ORCH
    assert "narrowed, never skipped" in ORCH


def test_gate_panel_lens_fit_nudge():
    assert "lens-fit assessment" in ORCH
    assert "never edits the panel itself" in ORCH


def test_reviewer_questions_slot_keeps_ungrounded_suspicion_visible():
    # Findings must be grounded, but grounding must not become a silent-drop channel: PASS is
    # defined as zero findings, so an ungroundable suspicion needs its own slot in the reviewer
    # format and a route to the human, or the zero-findings convergence rule is trivially gamed.
    assert "every identifier it relies on must exist" in STANDING
    assert "a question, not a finding" in STANDING
    assert "`Questions:` section" in STANDING
    assert "never blocks PASS" in FORMATS
    assert "every reviewer `Questions:` entry" in ORCH


def test_docs_only_round_decays_to_pr_note():
    # Run #1140 iters 5-9 burned ~1.2M tokens on comment polish that changed no behavior and
    # introduced new wrong comments; after a doc/comment-only round the orchestrator proposes
    # pr-note instead of another fix round, and the human decides.
    assert "Decay rule" in ORCH
    assert "all doc/comment-only" in ORCH
    assert "comment-polish rounds churn new wrong comments" in ORCH
    assert "for routing only" in ORCH
    assert "followups must carry them verbatim" in ORCH
    assert "convergence with only human-accepted open findings" in ORCH
    # The decay rule replaced the light re-review path (see issue #20); it must stay gone.
    assert "delta-focused" not in ORCH


def test_reviewer_questions_are_verified_never_applied():
    # Run #1140: a reviewer question's suggestion was relayed as a fix, built, then reverted
    # (~500k tokens, net-zero diff). Questions route to the implementer only for verification.
    assert "question, not an instruction" in ORCH
    assert "verification-only" in ORCH
    assert "no source edits and no normal implementer write contract" in ORCH
    assert "question-verification.md" in ORCH
    assert "review, question-verification, or fulfillment files" in ORCH
    assert "NO DEFECT | CONFIRMED FINDING" in ORCH
    assert ORCH.index("question-verification.md`, tagging each") < ORCH.index(
        "Only after that artifact is complete,"
    )


def test_followups_reads_the_issue_tracker():
    # Run #1140: followups dropped items with open issues and filed a duplicate — three of 27
    # ledger rows wrong for the price of one API call.
    assert "`gh issue list`, `gh pr list`" in ORCH
    assert "duplicates or extends" in ORCH


def test_dispatch_records_start_time_for_liveness():
    # Run #1140: an implementer died with a 110-byte transcript and surfaced ~9h later.
    # File presence cannot distinguish still-working from dead; elapsed time is the signal.
    assert "dispatch's start time" in ORCH
    assert "time since dispatch" in ORCH


def test_new_files_are_diffed_with_no_index():
    # git diff <ref> -- <path> is silent for untracked files; a per-file check on five new
    # files reported "unchanged" and masked a leftover workaround (run #1140).
    assert "git diff --no-index /dev/null <file>" in ORCH


def test_skill_names_all_three_template_paths():
    # issue #27: the dispatch section must name each bundled template file by path, so the
    # source of {role.standing} and {role.format} is discoverable by reading SKILL.md alone.
    assert "templates/standing-checks.md" in ORCH
    assert "templates/design.md" in ORCH
    assert "templates/formats.md" in ORCH


def test_template_files_exist_and_are_non_empty():
    # Loading each as a module-level constant above already enforces existence (a missing file
    # raises FileNotFoundError at collection); assert non-emptiness explicitly too, cheaply.
    for name in ("standing-checks.md", "design.md", "formats.md"):
        path = TEMPLATES_DIR / name
        assert path.stat().st_size > 0


def test_no_template_references_another_template():
    # References stay one level deep: no bundled template may point at another (or at any
    # templates/ path) — the architect's format is templates/design.md pasted directly, stated
    # in SKILL.md, never as a pointer inside a template.
    for content in (STANDING, DESIGN, FORMATS):
        assert "templates/" not in content


def test_formats_has_a_section_per_registry_role_except_architect():
    roles = set(REGISTRY["stage_roles"].values())
    roles.discard("architect")
    assert roles, "expected at least one non-architect role"
    for role in roles:
        assert f"## {role}" in FORMATS
    # architect's format is design.md pasted directly, not a formats.md section
    assert "## architect" not in FORMATS


def test_index_not_a_store_wayfinder_borrowing():
    # Design's ## Decisions section and the followups ledger are each documented as an index,
    # not a store: one-line gist plus a pointer, detail lives in exactly one place.
    sentence = "This is an index, not a store"
    assert sentence in DESIGN
    assert sentence in FORMATS


def test_hitl_sentence_in_hard_rules():
    # Hard rules carry a one-sentence HITL summary: no dispatched agent, nor the orchestrator
    # itself, answers on the human's behalf at a gate.
    assert "The agent never stands in for the human's side of a" in ORCH
