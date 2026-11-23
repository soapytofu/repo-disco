# UInt component and raw frame-pair revision 002

This is a new, narrower development component following the failed 102-source
AWS qualification, job `63088520`. The earlier run exposed legacy arithmetic
precondition failures and an array-initialization determinism error, reached
the 900-second native wall bound, and was recorded by Slurm as out of memory
under its 4GB allocation. Its original sources and complete evidence remain
unchanged and are linked by hashes in `revision.json`. It has not been repaired,
rescored, or promoted to a successful baseline.

The new baseline is exactly `StandardLibrary/src/UInt.dfy`,
`libraries/src/BoundedInts.dfy`, and `libraries/src/Wrappers.dfy` from the same
pinned release. The three files form the selected dependency-closed component;
all three are explicit verification roots. Their bytes and inherited contracts
remain unchanged. This qualification makes no full AWS/MPL repository claim.

Stage one retains `RepoDiscoU16Frame.ReadU16Frame`: parse one uint16-length-prefixed
raw-byte field and return its payload plus suffix. Its contract and reference
body are unchanged. The blank template is the exact existing common-policy
template with `BEGIN REPLACEMENT` / `END REPLACEMENT` comments.

Stage two adds `RepoDiscoFramePair.ReadFramePair`, returning `Pair(left,right,rest)`.
Its fixed contract requires success exactly when two complete frames exist,
the exact two payloads and remaining suffix, both uint16 length bounds, and
reconstruction of the whole input from the two length prefixes, payloads and
suffix. The reference calls stage one's API twice. For example,
`[0,1,65,0,1,66,99]` returns `([65],[66],[99])`.

These are raw byte fields: byte 255 is admissible, with no UTF-8 or encryption
context requirement. The specification also permits direct correct
implementations; API reuse is descriptive. A later model chain must pass its
actual accepted stage-one bytes into stage two. Analyst references are not
accepted model parents.

`cases.json` contains three positive cases (`baseline`, `stage1-reference`,
`stage2-reference`) and nine gated controls: three unchanged stage-one bad
bodies, four frame-pair bad bodies, an unproved parent with the exact reference
child, and an omitted child root. The omission case keeps the bad child staged
and hashed while excluding it from both argv and the include closure. It must
fail requested coverage even if the remaining scope verifies.

Only the three positives are candidates for the first new native job. Every
control remains gated on successful source-bound reference and complete unit
inventory review. Parent failure cannot be masked by a locally passing child;
the child's actual outcome must be recorded. Frontend, resource and process
failures do not satisfy ordinary proof-failure expectations.

The resource policy is unchanged: Dafny 4.9.1, the pinned compatible Z3 4.12.1,
one CPU, determinism enforcement, 500,000,000 resource units, 300-second verifier
limit, 900-second outer wall cap and 4GB. No upstream patch, trust change,
resource escalation, model call or automatic retry is introduced.

`build.py` verifies source blob identities and reconstructs all marked bodies;
`manifest.json` pins the result. Offline tests check source/interface identity,
coverage construction and finite decoding examples, not native correctness.
All new native outcomes remain **unknown** until root's compute qualification.
