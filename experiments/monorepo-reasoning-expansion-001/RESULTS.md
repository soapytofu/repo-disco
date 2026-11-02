# All 164 final fixture outcomes matched

**Verifier-only validation is complete. Zero model requests.** These results are
on authored development fixtures; they do not measure model difficulty or a
causal effect of proof sharing/dependency depth.

| Family | Semantic instances | Reference passes | Ordinary proof failures | Termination failures | Hidden-export failures | Matched total |
|---|---:|---:|---:|---:|---:|---:|
| Conditional | 2 | 8 | 40 | 0 | 4 | 52/52 |
| Sequence | 2 | 8 | 40 | 8 | 4 | 60/60 |
| Maps | 2 | 8 | 40 | 0 | 4 | 52/52 |
| Total | 6 | 24 | 120 | 8 | 12 | 164/164 |

The 120 ordinary failures include 24 empty-helper cases and 96 targeted controls.
The eight termination controls explicitly report a nondecreasing `decreases`
clause. All 12 visibility controls report an unresolved exported helper; related
method-call resolution errors are retained. No parse error is counted as a proof
failure. All runs use strict exit categories, not legacy substring success scores.

Current source is [revision-003](revision-003/README.md). Each instance has four
shallow/deep × shared/separate variants. Full source, commands, stdout/stderr,
source hashes and review inventories are saved alongside these records:

| Job | Purpose | Outcome | Elapsed |
|---|---|---|---|
| 57104220 | Initial runtime | Missing import before any Dafny call; preserved | 7s |
| 57106124 | First reference/empty phase | 44/48 expected; four reverse references failed | 4m12s |
| 57111126 | Explicit reverse proof correction | 4/4 revised references passed | 1m50s |
| 57112358 | Targeted negatives | 116/116 expected categories | 6m32s |

The correction changes only reverse-helper bodies, making base identities,
induction use and sequence reassociation explicit. It changes no client/provider
bytes, contracts or decreases clauses. The [reference gate](revision-003/reference-gate.json)
reuses 44 earlier outcomes whose exact sources match the final revision. It does
not rescore the failed versions or create independent repeated trials. There
were **168 actual Dafny invocations** across the history, including four failed
original references, plus one startup failure with zero verifier calls.

The [complete acceptance review](revision-003/completion-review.json) maps all
164 final conditions to individual raw records and source hashes. The complete
raw archives are [first semantic pass](runtime-002/verification-001),
[corrected references](revision-003/verification-001) and
[targeted negatives](revision-003/verification-002). Earlier failure evidence
remains available and published.

The separate [output guard](protocol/README.md) has nine offline test methods;
final-revision tests replay all 24 current references exactly. Admission preserves
contracts and immutable source; each future candidate must still be verified.
Alternative alpha-renamed test sources remain syntax-only. No new model protocol
or paid pilot is frozen or authorized.

Separate conditions retain two editable bodies and permit copied proofs; shared
primitive definitions remain in both conditions. Depth is the designed reference
path, not proved minimal depth. A later separately approved model pilot is needed
to learn whether the new obligations avoid the previous ceiling effect.
