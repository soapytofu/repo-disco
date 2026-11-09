# Four varied development calibration tasks

**First core verified: 32/32 expected outcomes. Zero model calls.** These implement the four C1
proposals in [the active corpus plan](../../docs/corpus-family-split-plan.md).
All reserved tree/transition-family tasks remain untouched.

| Task | Semantic target | Interface contrast |
| --- | --- | --- |
| D3-C1 bounded allocation | Choose two bounded integers with a fixed total | Direct numeric witness certificate versus bounds/join/balance certificates |
| D4-C1 map swap | Swapping present keys twice restores the map, including aliasing | Whole-map observation versus domain and individual-value observations |
| D1-C1 clamp distance | Clamping cannot increase the distance between two inputs | Guarded value facts versus opaque region certificates followed by value recovery |
| D2-C1 prefix split | Split a bounded prefix aggregate across a sequence slice | Direct prefix unfolding versus an opaque step fact followed by exposure, plus explicit induction |

Each task has shallow/deep × shared/separate variants (16 workspaces). Shared mode
has one editable helper plus a fixed forwarding helper; separate mode has two
copyable helper bodies. Both modes use the same protected providers, clients and
contracts within each task. The wrapper changes graph depth and output workload;
this is not an equal-work cognition comparison. Numerical minimum proof depth is
unknown. The interface labels describe reference-relative factorization, pending
verifier and ablation review.

The four tasks have **124 planned controls**: 16 reference successes, 88 ordinary
proof failures, four termination failures and 16 hidden-export resolution failures.
The first phase checks 16 references and 16 empty bodies (32 checks); only after a
reviewed passing core gate may the distinct remaining 92 controls be submitted.
No model output guard or paid prompt freeze is claimed by this construction.

Seven offline test methods passed: exact source reconstruction, immutable scope,
unique controls, shared/separate structure, finite-domain specification sanity,
diagnostic-category separation, and isolated imports with a fake verifier process.
These are not Dafny verification evidence. The reference and negative bodies alter
only the permitted helper proof regions; all contracts and other source bytes are
preserved. Full compute sources, raw diagnostics and scheduler logs will be
published whether expected outcomes pass or fail. Fixes will be versioned with
failed evidence retained; no automatic retries or duplicate jobs.

Verification is restricted to compute nodes, with live-confirmed nonpreemptible
`test`, exact Dafny 4.11.0/Z3 4.12.1, `--verify-included-files`, strict warnings and
one verifier invocation per control. The bounded SSH tools use the user-created
socket `repodisco-codex-12.sock`; no API key is needed or accessed.

November 9: job **59351309** completed on nonpreemptible `test` in 2m05s.
All 16 references verified strictly and all 16 empty proofs failed with proof
diagnostics. [The reproducible review](verification-001-review.json) checked the
full archived manifest and exact source hashes. All inputs, raw diagnostics and
relevant scheduler logs are retained under `verification-001/` and the job logs.
Unrelated projects' queue rows are omitted from public scheduler receipts only;
[scheduler-redactions.json](scheduler-redactions.json) records before/after hashes.

The remaining 92 original controls have **not** been submitted. A source audit
identified that the map reference's granular interface need not lengthen its
contract-application path versus the bundled interface (both have a three-stage
reference path). A deliberate revision will add a required domain certificate,
then validate the changed map sources before the targeted negatives. This first
core run remains unchanged; its 24 non-map outcomes can be reused only after
exact source and verifier-code comparisons. No model difficulty or minimal-depth
claim follows from the verifier results.
