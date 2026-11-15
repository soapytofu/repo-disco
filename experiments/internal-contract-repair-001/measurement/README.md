# Prospective two-method measurement gate

This is offline measurement preparation. It makes no model or verifier calls,
does not authorize execution, and does not change the earlier experiments.
The two new dual-fault seeds still need their compute-node verification gate.

`score_candidate(task_id, files, trusted_source_sha256, guard_receipt, record,
raw_files)` checks a candidate for the **fixed new** internal contract. It
replays the pinned method-body guard using the exact body strings, then compares
the complete reconstructed sources and receipt. Canonicalizing the surrounding
JSON does not alter a body string. A receipt must match the pinned policy code,
registry, dependency hashes, task, seed, candidate, syntax and call inventory;
an arbitrary acceptance Boolean cannot grant a pass.

The measurement wrapper independently checks the exact public and target helper
headers and closing spans, the immutable kernel and include host, and the four
source hashes. The guard owns full bounded-body syntax and type validation.
The trusted host must bind the captured verifier record to this reconstructed
candidate and pin the compute allocation, Dafny/Z3 versions and command. These
hash checks are not cryptographic attestation of where a process executed.

The named CSV parser and diagnostic classifier are byte-exact copies of the
reviewed propagation study. `input-provenance.json` records their origin, and
`inputs-manifest.json` binds their transitive local inputs. The copied v2 scope
permits only the exact `Kernel.Endpoint` definition to be absent from CSV; that
absence is labelled **unlogged**, never counted as a passing provider unit.
The three map-provider well-formedness units are mandatory. Both
`Helper.Transfer` and `Client.Target` correctness units are mandatory for a
completed proof-level outcome. Unknown, missing, duplicate, mixed or malformed
units fail the measurement gate.

Strict workspace success requires exit zero, no errors or warnings, coherent
named evidence and both method units passing. A client passing under a helper
contract that the helper failed to establish is not repository success.
Envelope rejection, body-guard rejection, Dafny parse failure, combined
resolution/type failure, ordinary proof failure, termination failure, warning,
timeout and verifier execution error remain distinct. A combined Dafny
resolution/type footer is not guessed into a finer category. CSV captured by an
incomplete frontend/timeout run remains raw evidence and receives no local proof
score. Incoherent source, stream, base64, hash, logger or exit evidence raises
`MeasurementError`; it must not become a model proof failure or permission to
retry.

`H.Transfer` is optional. Its call inventory describes syntactic occurrences,
not dynamic execution, necessary reuse, data dependence or a reasoning path.
Transparent-kernel direct implementations remain eligible when they satisfy the
same guard and contracts.

`replay_controls()` is a separate exact-hash path over the 18 published verifier
observations. It includes old-API controls solely to reproduce their recorded
outcomes. It cannot admit old contracts through `score_candidate`. The replay
retains six strict successes, twelve proof failures and nine unlogged Endpoint
observations. These are reused observations, not new Dafny trials or model
results. The synthetic tests also use fabricated verifier records; a synthetic
pass is not mathematical validation of its candidate.

Run the offline tests with `python3 -B -m unittest -v test_measure`. The isolated
bundle test copies only `measurement-manifest.json` pins, imports in an isolated
Python process, blocks verifier/network calls, replays all 18 saved records and
checks a guarded synthetic candidate. No live paid handler implements this new
two-method protocol yet. A future prompt freeze must bind the reviewed policy,
measurement manifest and actual seed-verification evidence separately.
