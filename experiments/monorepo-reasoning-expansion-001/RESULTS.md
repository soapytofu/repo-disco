# Reference validation complete; targeted controls pending

These are verifier-only results on authored development fixtures, not model
samples or evidence of model difficulty, sharing benefit or minimum proof depth.

| Family | Semantic instances | Reference workspaces verified | Empty-proof controls rejected |
|---|---:|---:|---:|
| Conditional | 2 | 8/8 | 8/8 |
| Sequence | 2 | 8/8 | 8/8 |
| Maps | 2 | 8/8 | 8/8 |
| Total | 6 | 24/24 | 24/24 |

Current sources are [revision-003](revision-003/README.md). Job 57106124 first
passed 20 references and rejected all 24 empty proofs, but failed four reverse
references at their final assertion. Those sources/results remain intact.
Job 57111126 verified the four deliberate reverse-proof corrections. The combined
[reference gate](revision-003/reference-gate.json) reuses the 44 unchanged outcomes
with exact source and evidence hashes; it does not rescore the failed versions.

Targeted-negative job **57112358** is pending: 96 expected ordinary proof failures,
8 termination failures and 12 hidden-export name-resolution failures. The complete
164-check fixture validation gate is not yet finished. No new model calls.

The separate [output guard](protocol/README.md) has nine offline test methods,
with byte-exact reconstruction, scope isolation and bypass rejection checks.
Revision tests additionally replay all current references through that same guard.
Guard admission is not verification; alternative alpha-renamed test sources still
have no independent Dafny evidence. Existing frozen model protocols are unchanged.

Shared vs separate still changes editable-body count and permits copied proofs.
Export-view depth describes the designed reference path, not proved minimal depth.
All six instances are development tasks, not held-out or model-generated data.
