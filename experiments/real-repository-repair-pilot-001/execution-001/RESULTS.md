# Real-source repair pilot results — November 17, 2026

**16 returned responses, 16 unique request IDs, zero SDK retries.** Seven outputs
meet the prespecified qualified-scope acceptance policy. An eighth proves the
complete required inventory but has an additional build-cleanup warning. Seven
outputs are rejected by the frozen body guard before verification; one admitted
output has a native Rust type error. There are no observed mathematical proof
failures among the nine verified candidates. This does not classify the seven
unverified outputs as mathematically correct or incorrect.

| Real upstream task | Responses | Guard admitted | Full proof passes | Qualified accepts | Other outcomes |
| --- | ---: | ---: | ---: | ---: | --- |
| Dafny-VMC sequence swap | 4 | 0 | 0 | 0 | 4 guard rejections |
| Dafny-VMC small shuffle | 4 | 3 | 3 | 3 | 1 guard rejection |
| Vest blanket roundtrip | 4 | 4 | 4 | 3 | 1 proof pass with new cleanup warning |
| Vest Pair roundtrip | 4 | 2 | 1 | 1 | 2 guard rejections; 1 type error |
| **Total** | **16** | **9** | **8** | **7** | **7 guard; 1 frontend; 1 warning-policy exclusion** |

“Full proof pass” requires the entire qualified inventory and native consistency
checks. “Qualified accept” additionally requires exactly the reviewed upstream
warning set: three Dafny warnings or five Vest warnings. No successful baseline
or candidate here is a zero-warning pass. These columns overlap and must not be
added together. The primary frozen result is **7/16**, not a retrospectively
relaxed 8/16. Detailed rows are in [JSON](results-001.json) and [CSV](results-001.csv).

## Matching and limitations

| Arm | Responses | Admitted | Full proof passes | Qualified accepts |
| --- | ---: | ---: | ---: | ---: |
| Verifier diagnostics | 8 | 5 | 4 | 3 |
| Failure notice | 8 | 4 | 4 | 4 |

This pilot does not establish a feedback advantage. The raw proof-pass counts
tie, admission differs, and the extra cleanup warning occurs in the diagnostics
arm. Conditional rates among admitted outputs are selected subsets, not a causal
feedback estimate. Source context and instructions are fixed within each task;
the feedback block is the sole prompt difference. Context policies differ between
repositories, so this is not a controlled Dafny-versus-Verus comparison.

There are four induced development failures clustered within two inspected
upstream repositories, with two fresh responses per task-arm. The sixteen outputs
contain ten distinct replacement bodies, nine admitted trials contain seven
distinct candidate files, and seven qualified accepts contain six distinct files.
Repeated samples are not new tasks or independent repository families. These
results show constrained repairs on real source, not discovered upstream bugs,
unrestricted repository generation, necessary multi-file editing or held-out
generalization.

## What the failures tell us

All sixteen JSON envelopes are valid. The separate [syntax audit](syntax-audit-001.json)
identifies limitations of our frozen guard:

- Slots 1/2/15/16 use `s[i := s[j]][j := s[i]]`. The generic assignment check
  mistakes an index in a sequence-update expression for assignment to an input.
- Slot 12 uses `assert !(...);`. The generic macro check mistakes Dafny logical
  negation after `assert` for a macro invocation.
- Slots 7/10 use Verus `=~=`; the frozen lexer does not include `~`.

No relaxed guard or verifier replay was applied to those seven outputs. Their
mathematical status remains unmeasured. These exclusions must be addressed before
using this protocol for a larger collection; they are not evidence of seven
reasoning failures.

Slot 8 passes the guard but Rust reports **E0599**: it calls
`self.1.lemma_serialize_dps_len(v.1, obuf)` even though the fixed `B: SPRoundTripDps`
bound does not supply that method. The missing trait is `NonTailFmt`. The model
cannot repair this by strengthening the protected type bound. This is a concrete
failure to respect an API's available capabilities, caught by native checking.

Slot 13 is byte-identical to qualified slot 4. It has exit zero, complete proof
coverage and zero proof errors, but adds an incremental-compilation garbage
collection warning: `Directory not empty (os error 39)`. Its primary acceptance
remains false; its full-proof result remains true. This operational warning is
neither a mathematical failure nor an analyst-rescored success.

## A successful cross-module repair

The Pair seed serializes its first component onto `serialized1`, but invokes the
first component's roundtrip theorem with `obuf`. Slot 9 aligns the theorem with
the actual serialization context and establishes length/remainder facts using
the existing APIs:

```rust
// Induced starting call
self.0.theorem_serialize_dps_parse_roundtrip(v.0, obuf);

// Corrected call in the accepted model output
self.0.theorem_serialize_dps_parse_roundtrip(v.0, serialized1);
```

This excerpt is one part of the accepted body, not a minimality claim. The proof
uses trait contracts in the core module, Pair's specifications in another module,
and child-format theorems. The accepted source keeps all signatures, contracts
and other files fixed. Complete sources and the manual reviews are available in
[the saved response](model-001/slot-09/response.json),
[candidate](model-001/slot-09/candidate.txt),
[native observation](verification-vest-001/slot-09/observation.json),
[Dafny review](manual-dafny-review-001.json) and [Vest review](manual-vest-review-001.json).

## Scope, resources and provenance

Dafny candidates verify all 28 declared inputs and 267 required named obligations;
91 upstream file hashes are protected. Vest candidates run the default `vest_dev`
scope including `vest_lib` and `vstd`; 3,481 upstream files are protected. Successful
native crate summaries report 340, 3,279 and 2,102 verified obligations respectively,
with the qualified inventory and label multiplicities checked separately. This
does not imply every file or optional feature in either Git repository is verified.
Existing upstream trust exemptions remain explicit. No live upstream branch was
promoted; acceptance records identify the reviewed candidate artifacts.

| Job/stage | CPUs | Elapsed | Slurm total CPU | Job-level CPU efficiency | Peak batch RSS |
| --- | ---: | ---: | ---: | ---: | ---: |
| 61582770 collection | 1 | 2m09s | 2.751s | 2.1% | 52,324 KiB |
| 61583898 Dafny | 1 | 2m14s | 1m33.549s | 69.8% | 619,804 KiB |
| 61584032 Vest | 4 | 52m05s | 32m57.594s | 15.8% | 2,435,292 KiB |

All three submissions were unique, nonrequeued, on live-confirmed nonpreemptible
`test`. Collection spent most time waiting for the provider and reserved only one
CPU. Dafny native commands used 90–94% of one core. Vest retained the frozen three
verifier threads/four Cargo build workers; native commands averaged about
1.29–1.89 active cores. Whole-job efficiency was much lower, with substantial time
outside the timed native commands in source preparation/integrity work. The four
cores were not fully utilized. Future scheduling should isolate preparation at
one CPU and qualify any lower-core verifier setting before larger collections.
One local read-only monitoring query timed out; SSH was healthy and the existing
job continued without cancellation or resubmission.

Token use: **479,940 input + 3,447 output = 483,387 total**. All sixteen approved
slots are consumed. There were no availability calls, model retries, reassignment,
automatic repairs or new requests after collection. The old terminal paid ledgers,
prior scores, frozen prompts and runtime remain unchanged.

The three transfers contain **198 files**, including raw native stdout/stderr,
Dafny CSV, Verus JSON inventories, resource logs, ledger, full model responses,
candidate files, source/profile bindings and scheduler accounting. All nine native
observations replay under the unchanged scorer. Start with
[collection review](collection-review-001.json), [Dafny review](review-dafny-vmc-001.json)
and [Vest review](review-vest-001.json); the transfer inventories bind every fetched
file. Guard fixes, diagnostics on excluded outputs, and resource changes require
separate versioned work; none silently changes this result.
