~1 page, no code blocks, no file:line dumps. Product first, implementation second. A design that
unifies a style/format/template must pin it with one fully-worked example (a complete sentence or
instance showing placement and punctuation), not only named parts:

```
## What we're solving      (product: the problem and who hits it)
## How it will work        (product: user-visible behavior after the change)
## Proposed solution       (implementation approach)
## Alternatives + the call
## Major changes           (key files/areas only — never an exhaustive file list)
## Scope split             (This PR · Prerequisite refactor · Follow-ups)
## Risks
## Open questions          (real decisions only — each: options + recommended answer; no filler)
## Decisions               (from _design_feedback.md when it exists; otherwise starts empty)
```

`## Decisions`: This is an index, not a store: one line of gist plus a pointer, and the detail
lives in exactly one place.

Facts verifiable in the repo or issue belong in the design body, not Open questions — ask as
many decisions as the design needs, no minimum or maximum.

Scope split partitions the work: This PR (what the diff will contain), Prerequisite refactor
(restructuring the change needs — lands first, as its own PR, never as a commit inside the
main PR), Follow-ups (adjacent debt or gaps found during exploration that this PR
deliberately leaves). Ticket a Follow-up when you can state the question precisely now; when you
cannot yet phrase it that sharply, record it as fog — a not-yet-sharp known-unknown is a
Follow-up, never a forced Open question. Before declaring Prerequisite refactor empty, check the
repo's refactor-separation policy (CLAUDE.md / CONTRIBUTING): where the repo mandates
refactor-lands-first, any "refactor first, then the change" structure IS a non-empty
prerequisite — calling it internal commit sequencing is a design defect.
