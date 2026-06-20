---
name: staff-review
description: Staff Engineer Code Review — deep review of PRs or branch diffs with verified findings. Re-evaluates severity after verification, and (with `apply`) auto-applies surgical fixes for every finding that is a real improvement — including low/nit — skipping only fixes that are unnecessary or too complex for their severity. Use when you want a thorough code review that checks correctness, types, performance, edge cases, and test coverage.
argument-hint: "[pr-number-or-url] [apply]"
context: fork
---

## Staff Engineer Code Review

You are a staff engineer reviewing code for a new feature or bug fix.

### 1. Parse invocation arguments

Your raw arguments are between the markers below. The harness substitutes them in; if you see the literal placeholder string `<dollar>ARGUMENTS` (no substitution), the mechanism did not fire and you must instead read args from the user's invocation message in your conversation context.

`<ARGS>$ARGUMENTS</ARGS>`

**Before anything else, echo what you found between those markers as your first user-facing line:**

```
Invocation args: "<exact string between the markers above, or empty>"
```

Then tokenize the args by whitespace and apply these rules independently:

- **apply flag** — set `apply=true` if **any** whitespace-separated token equals the word "apply" (case-insensitive, exact match). Order does not matter. Position does not matter. Otherwise `apply=false`.
  - `apply` → true
  - `apply 7693` → true
  - `7693 apply` → true
  - `https://github.com/org/repo/pull/123 apply` → true
  - `applying` / `apply-fix` / `--apply` → false (not an exact token match)
- **PR reference** — set `pr=#<number>` if any token is either a bare positive integer or a `github.com/.../pull/<number>` URL. Otherwise `pr=none`.

**Then output the parsed state as your next user-facing line**, in exactly this format:

```
Parsed: apply=<true|false>, pr=<#number|none>
```

This is a commitment, not a comment. If `apply=true`, step 7 is fixed: you will apply fixes without asking. Do not re-litigate this at the end of the review. If the echoed args contain the word "apply" as a standalone token but you wrote `apply=false`, you have made a parsing error — stop and re-parse before continuing.

### 2. Gather the diff

**Prefer the local working tree whenever possible.** A fresh checkout under `/tmp` is a last resort — only reach for it when the current directory genuinely cannot serve the review (wrong repo, or you need a clean tree and the user has unrelated uncommitted changes).

Decision order:

1. **No PR reference, in a git repo** — review the local branch. Detect an open PR via `gh pr view --json number,url` for context, but read the diff from the working tree: `git diff <base>...HEAD` (where `<base>` is the PR base or `origin/HEAD`), plus `git diff` and `git diff --cached` for any uncommitted changes. Mention uncommitted changes explicitly in the report.
2. **PR reference provided, and we are inside the matching repo** — verify by comparing `gh repo view --json nameWithOwner` to the PR's repo. If they match:
   - If the PR's head branch is currently checked out (`git branch --show-current` matches `gh pr view <n> --json headRefName`), review the local tree as in (1).
   - Otherwise, read the diff via `gh pr diff <number>` and PR metadata via `gh pr view <number>` — no checkout, no `/tmp`.
3. **PR reference provided, and we are NOT in the matching repo (or not in a git repo at all)** — only then fall back to a fresh checkout under `/tmp` (`gh pr checkout` into a temp clone). State this in the first user-facing line so the user knows why you're leaving the current directory.

Never `cd /tmp` or clone anywhere when steps (1) or (2) apply. If you're unsure which case you're in, run the detection commands above before fetching anything.

### 3. Identify potential issues

Correctness, types, performance, edge cases, test coverage, security, API design. Assign an **initial** severity: `critical` / `high` / `medium` / `low` / `nit`.

### 4. Verify each finding

Use subagents to verify each finding against the actual code. **Discard** any finding that cannot be verified.

### 5. Re-evaluate severity (important)

Initial severities are frequently wrong — assign them under uncertainty, then revisit once verification has surfaced the real shape of the bug. For every verified finding, reconsider in light of what verification revealed:

- Does it actually break correctness, or is it stylistic / cosmetic?
- Blast radius: one call site vs. whole subsystem? Hot path or one-shot setup?
- Existing safeguards: does a test, type, or runtime check already cover it?
- Is this on a public API boundary, or internal-only?
- Is the failure mode silent data corruption (bump up) or a loud crash already caught by tests (bump down)?

Adjust severity up or down accordingly. When severity changes, record both in the report (e.g. `high → medium`) and explain the reason in one short line.

### 6. Report

Present verified findings grouped by **final** severity with `file:line` references. Include a summary table:

| # | File:line | Issue | Initial | Final | Δ reason (if changed) |
|---|-----------|-------|---------|-------|----------------------|

### 7. Apply or ask

Branch on the `apply=` value you committed to at step 1 — do not re-derive it from the args here, do not second-guess it.

- **`apply=true`**: proceed directly to fixes. **Do not** summarize-and-ask. **Do not** phrase as "want me to fix?" / "shall I apply?" — the user already said yes when they typed `apply`. Apply the smallest surgical fix for every verified finding that is a real improvement, **regardless of severity** — `nit` and `low` count too. The user explicitly wants the trivial cleanups handled, not deferred. Skip a finding only when the fix would be **unnecessary** (e.g. the "issue" is stylistic and the current code is fine as-is) or **disproportionately complex for its severity** (e.g. a nit that would require a non-trivial refactor). When you skip, name the specific reason — "low severity" alone is not a reason. Reuse existing patterns; no refactors or scope creep. If a fix attempt fails (test breaks, type error, etc.), **try harder** — the right fix may need a different approach. Reverting to "skipped" with an "out of scope" excuse is not acceptable when the user said apply. After fixes, run the relevant tests / lint / build for the files you touched. Report which findings were applied, which were skipped (with the specific reason — unnecessary or too complex), and any test/build failures.
- **`apply=false`**: ask the user whether to implement fixes.
