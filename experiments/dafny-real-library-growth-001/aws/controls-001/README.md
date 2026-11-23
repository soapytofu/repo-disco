# AWS extension controls 001

Nine verifier-only cases are constructed from the unchanged AWS draft controls
and current `cases-001` workspaces: seven bad function bodies, one unproved
parent with the exact reference child, and one omitted stage-two root. No
positive baseline or reference is duplicated as a new control.

Every workspace preserves the exact 102 upstream source files. Additions and
negative bodies are copied byte-for-byte from their existing artifacts. The
builder checks release blob/source identities, complete source maps, fixed
function prefixes/suffixes, explicit root order and literal include closure.
`cases.json` supplies full workspace hashes, complete native argv, expected
named targets and separate native-versus-coverage expectations.

An ordinary negative must produce a genuine failure for the named function,
with the qualified upstream obligations still covered. Frontend errors,
timeouts, resource failures, missing evidence and merely nonzero exits cannot
stand in for that expected proof failure. Exact CSV unit labels and unchanged
inventory requirements must be bound from the positive qualification.

For `unproved-parent-passing-child`, the parent is the unchanged
`stage1-always-failure` source and the child is the exact reference. The name is
inherited from the draft; it does not prescribe or claim the child's observed
outcome. The review must record both targets and reject the workspace whenever
the parent is unproved.

The omitted-root case stages and hashes both reference additions but removes
only `RepoDiscoContextEntry.dfy` from argv. No other selected file includes it.
The expected native scope is therefore the passing stage-one scope, while the
requested stage-two coverage must fail for every missing obligation from that
file. Hashing or staging a source does not establish verification coverage.

All cases are **gated pending successful AWS positive qualification and inventory
review**. The construction does not authorize dispatch or model calls. It pins
the current qualification command and limits without escalation; root must
submit any later controls in a separately reviewed, exclusive compute job.
Existing upstream trust assumptions and the selected-component scope remain
unchanged. These are source construction checks, not native proof results.
