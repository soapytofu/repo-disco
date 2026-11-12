# Fresh-pilot prerequisite-order diagnostic

November 12, 2026. **Verifier-only analyst diagnostic; zero new model calls.** The original [fresh map pilot](../map-development-pilot-002/RESULTS.md) remains **12/16 strict passes**. This separate experiment tests whether reordering existing calls is sufficient to repair its four deep restriction/merge failures. Verification results are pending.

## Exact scope

| Parent trial | Condition | Analyst edit | Expected result |
| --- | --- | --- | --- |
| map-balanced-04 | Deep/shared | Move one existing certificate call in HelperA | Strict success |
| map-balanced-08 | Deep/separate | Same move in both editable helpers | Strict success |
| map-balanced-09 | Deep/shared | Move one existing certificate call in HelperA | Strict success |
| map-balanced-11 | Deep/separate | Same move in both editable helpers | Strict success |

Each edit moves `O1.Certify(K.Restrict(m, keep), K.Restrict(n, keep));` immediately after the existing `O2.RestrictKeys(m, keep);` and `O2.RestrictKeys(n, keep);` calls. There are six edited bodies across four workspaces. No statement is added or removed; line bytes and statement multiplicities are preserved. All declarations, imports, contracts, providers, clients and frozen output policies remain unchanged. The unchanged guard admits all four reordered workspaces without a syntax projection or parser change.

The two shared candidates are byte-identical, as are the two separate candidates: **four parent-linked diagnostic checks, two unique repaired workspace contents**. They are not four independent problem instances. The original failures already have exact-source verification logs, copied into [parents](parents); no original failure is rerun. The diagnostic inputs live only in [fixtures](fixtures), and the pilot archives are read-only inputs.

## Validation and execution

[Four offline tests](offline-tests-001.log) check exact candidate reconstruction, line-multiset preservation, six protected helper-body boundaries, all unchanged files, bounded-grammar admission/rejection, strict refusal of an already-reordered or ambiguous mutation, fake-process staging and exact CSV bytes. They make no model calls or real Dafny invocations. The same four tests also [passed in Cannon's environment](remote-offline-tests.log) before submission.

[manifest.json](manifest.json) pins 154 source/runtime/parent files:
`84ddfb4499af4dfd7555ed0c07c0f4aa2e324162574833cced59466dac127ced`.
[provenance.json](provenance.json) binds source commit `f91576c95e0420d000efa013ff0a75d05b501479`, original results and the complete original model-file inventory. The verifier wrapper preserves UTF-8 CSV bytes, including line endings.

The job is prepared for nonpreemptible `test`, two CPUs, 8 GB, fifteen minutes, no requeue. Submission checks live partition status and exclusive output/submission locks; no duplicate or automatic retry is allowed. Dafny runs only on a compute node, verifies all includes and has a sixty-second timeout per candidate. No API client, connectivity check or credential handoff is involved.

The offline reviewer checks exact source/runtime hashes, four strict exit-zero results with 20 verified obligations each and no warnings/errors, raw CSV digests, byte-identical parent inputs and preservation of every original model-archive file. Unexpected outcomes must be archived before a deliberate correction.

Success would establish sufficiency of this analyst reorder on the four saved responses, not a new model success, minimal repair, necessary proof-depth bound or general causal sharing effect. No rescoring or promotion into the original pilot occurs. Full source, verification and scheduler evidence will be published separately here.
