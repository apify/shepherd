---
name: shepherd-evaluate
description: Post-run analysis of one or more shepherd runs in the current session — per-stage cost, signal-per-stage counterfactuals, reviewer overlap, gate calibration, and ranked improvements. Run after a run reaches phase=done. Invoke as /shepherd-evaluate.
---

Evaluate the shepherd session end-to-end. Ground every claim in session evidence — `.shepherd/`
run files (including the `_progress.md` cost ledger and `archive/<run>/` for earlier runs),
findings files, git history, stage completion reports. Cite the source next to each number; say
"unmeasured" rather than estimate silently.

1. **Cost** — per-stage table (stage · engine · model · tokens · duration · dispatches), per-run
   and combined totals, stating what they exclude (e.g. orchestrator context). Wall-clock per run
   vs. total agent-compute.
2. **Signal** — per stage: what did it change about the outcome, and the counterfactual — skipped,
   what ships differently? "Nothing" puts it on a cut-candidates list with its cost.
3. **Overlap** — findings caught by multiple reviewers (duplication) vs. uniquely by one
   (irreplaceable lens). For zero-finding reviewers: clean code, or redundant/filtered lens?
4. **Gates** — every human stop: question asked, answer given, did it differ from the
   recommendation? Always-accepted gates are calibration signals — which stops should become
   defaults?
5. **Health & friction** — did orchestrator context compact, and what were its biggest context
   consumers? Every infra failure or wasted round-trip (tool errors, retries, hook noise), each
   with its cost in turns.
6. **Improvements** — ranked by expected savings or quality gain; each traced to an observation
   above and naming the exact change (file + before/after text or config diff). Separate
   skill-text vs. config/roster vs. infra-shepherd-can't-fix. End with a **keep list**: what
   earned its cost, with the finding that proves it.

Format: 5-line executive summary first (total cost, verdict, top 3 improvements), tables for
numbers, prose for judgments, no praise padding — if a stage was waste, say so plainly.
