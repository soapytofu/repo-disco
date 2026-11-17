# Verifier controls and frozen pilot preparation

Completed November 16, 2026 (Eastern). **No model calls.** Four real-source task
sites, six fresh negative controls, and exact reuse of four reference sites from
two previously qualified positive runs. This is preparation evidence, not a
repair-model success rate.

## Fresh negative controls

Job **61338497** completed on the nonpreemptible `shared` partition in **15m41s**,
with eight allocated CPUs, 32 GB, no requeue and at most two concurrent commands.
The 50-file transfer contains full stdout/stderr, CSV/native JSON, command and
source bindings, runtime records and Slurm accounting. The protected-edit
interfaces did not change: each task exposes one fixed body in one file.

| Control | Required failed target | Exit | Command time | Peak RSS (KiB) |
| --- | --- | ---: | ---: | ---: |
| VMC sequence-swap seed | `Model.Swap` well-formedness/postcondition | 4 | 27.52s | 617,560 |
| VMC small-shuffle seed (empty proof) | `Equivalence.ShuffleElseClause` correctness | 4 | 34.46s | 589,224 |
| Vest blanket roundtrip seed | `C::theorem_serialize_parse_roundtrip` | 101 | 239.93s | 2,288,976 |
| Vest blanket roundtrip empty body | Same target | 101 | 223.32s | 2,288,736 |
| Vest Pair seed | `Pair::theorem_serialize_dps_parse_roundtrip` | 101 | 205.61s | 2,286,624 |
| Vest Pair empty body | Same target | 101 | 209.21s | 2,289,436 |

All **6/6** match ordinary proof-failure expectations, with actual failed named
targets. There were no frontend failures or timeouts in these controls. An empty
VMC function result is rejected by the edit policy offline and is not counted as
a seventh verifier observation.

The VMC runs each report 266 verified and one failed unit; all 267 expected units
are present. `Implementation.Trait.Swap` and `Implementation.Trait.Shuffle`
respectively still pass under the failed providers' contracts. The complete gate
rejects the workspaces. Thus these controls test the distinction between a
locally passing caller and a verified dependency, not a claim that the caller
itself must fail after every provider defect.

Each Vest run fails the selected library proof. Cargo then stops before verifying
`vest_dev`; those absent clients are **not** counted as passing. The recorded
`coverage_complete=false` is expected for these rejected dependency failures.
Successful future repairs must include the complete `vstd`, `vest_lib`, and
`vest_dev` inventories under the pinned default feature scope.

Both VMC failures retain the same three upstream trigger warnings. The Vest
roundtrip seed also records Cargo's “failed to save last-use data / database is
locked” bookkeeping warning. It still reaches the actual expected postcondition
failure. This warning is preserved in raw evidence and in that task's diagnostic
prompt; it is not a proof result, a reason to rescore, or a clean positive control.
The other three Vest negatives have zero warning blocks. A future bounded runner
should avoid concurrent shared-cache writes, and must not silently accept new
warnings or retry them.

## Exact reference and integrity review

[controls-review-001.json](controls-review-001.json) reconstructs all four original
upstream files byte-for-byte and checks their successful named targets and selected
client observations against the saved qualified baseline runs. Those observations
are reused, **not four new positive verifier invocations**. The original baseline
qualifications and all prior scores remain unchanged.

The review replays the raw native classifiers, validates every transferred hash,
checks exact commands, toolchains, source inventories before/after execution and
body boundaries, and binds every observation to its single job/case identifier.
Each VMC candidate binds all 91 upstream files; each Vest candidate binds all
3,481 upstream files. Hashing these files establishes identity, not proof coverage:
the separately qualified named inventories establish the declared proof scope.
Actual modified source bytes are retained in `fixtures/`; the remainder is the
pinned upstream archive and source manifest.

The initial job **61335974** failed before either verifier ran because two local
qualification review JSON files were absent from remote staging. Its four-file
failure transfer and original 30-file runtime are preserved. The deliberate
`runtime-002` correction includes those two exact review files and relocates
dependency lookup; all task, guard and scorer bytes are unchanged. The corrected
bundle passed its dependency check and 11 offline policy tests on Cannon before
its distinct single submission. This is not an automatic retry or a mathematical
failure of a candidate.

## Frozen proposal

The final [freeze](frozen-001/manifest.json) contains **27 artifacts**: eight exact
request payloads, four common prompt blocks, four source-context blocks, four
transformed feedback blocks and seven metadata files. Manifest
SHA-256:

`0b28485bde1d52137afe217db690e6c672f9444eb04a6300d069c3b0b4884556`

The proposed **16 new requests** comprise four sites × two feedback arms × two
independent responses. The paired prompts differ only in their feedback block.
All eight preparation tests pass against the actual freeze, including exact
reconstruction, balanced order, absence of each task's original body from its own
context, and rejection of stale/missing/changed evidence. All 11 edit-policy tests
passed locally and on Cannon. No extra model call or API availability check was
used to validate prompts.

The 16 prompts contain 1,254,142 input characters in total. A rough characters/5
to characters/3 heuristic gives **251k–418k input tokens**, not a tokenizer
measurement or price quote. Maximum output is **65,536 tokens**. Actual costs,
tokens and IDs would be recorded by a separately approved bounded runner.

This freeze is **not execution authorization**. No paid runner, authorization,
credential handoff, model response or model score exists for this pilot. The
older terminal paid ledger remains closed. See [README.md](README.md) for the
task definitions, protected edits, acceptance rule and research limitations.
