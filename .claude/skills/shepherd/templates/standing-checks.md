committed code must not reference run-internal artifacts
(`.shepherd/`, plan files, session paths); cruft preserved by a faithful migration is still a
finding — "byte-identical" instructions cover assertions/behavior, not carried-over dead code;
a comment the diff adds, edits, or moves must still be true of the code it now describes —
stale references, wrong claims, comments restating the obvious, and comments longer than the
code they describe are findings; also flag AI-slop — abnormal defensive try/catch (defensive
code at trust boundaries is fine), type-escape casts (`any` or equivalent), deep nesting that
should be early returns, and other patterns inconsistent with the surrounding file. Also require
these three checks: a conditional branch or guard the diff adds must be test-exercised on both
sides, and a rewritten path must be exercised against the input classes the old path handled —
an untested new arm is a finding; a behavior delta versus design or base that the design leaves
unstated is a finding, including a changed helper whose default/no-arg semantics silently invert;
and whatever the diff names, places, or exports must follow the repo's stated conventions doc,
with a new module importing no heavier layer than its role needs. Every finding carries evidence
checked against the repository, and every identifier it relies on must exist; a suspicion you
cannot ground is a question, not a finding — it belongs in your `Questions:` section, never as a
finding and never dropped.
