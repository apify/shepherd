## verify

claim ledger: every request claim tagged `VALID | STALE | LIKELY-FIXED | UNVERIFIABLE` with
evidence (claims resting on facts outside the repo: check current upstream sources, not model memory),
plus a one-line verdict — never empty

## explorer

≤1 page: key files · patterns · data flow · risks

## success_criteria

numbered, testable criteria — each verifiable by a command or an observable behavior; no
solution details

## implementer

what done · every finding fixed, none skipped or deferred · for a behavior change, add a
regression test — ideally shown red before the fix and green after, with the red→green noted in
`claim.md` — never weaken/delete tests

## reviewer

first line `VERDICT: PASS|FAIL` (PASS = zero findings, `pre-existing`-tagged ones excepted), then
findings tagged `blocker|major|minor|nit`; a defect in adjacent code that predates the diff
carries the extra tag `pre-existing` — reported, never silenced, routed to step 7 (Fulfillment +
create-PR confirm); then a `Questions:` section — every suspicion you could not ground, or
`none` — which never blocks PASS and is surfaced to the human at the same gate

## final_reviewer

same verdict format as reviewer

## fulfillment

first line `VERDICT: PASS|FAIL`, then each criterion `MET | NOT MET` with evidence

## followups

ledger: item · origin (`scope-split` | review file | `question-verification`) · proposed
disposition `fix-here | issue | pr-note | drop` · one-line why; include every pre-existing,
human-accepted open, and confirmed-question finding; never empty — "none" explicitly.
This is an index, not a store: one line of gist plus a pointer, and the detail lives in exactly
one place.
