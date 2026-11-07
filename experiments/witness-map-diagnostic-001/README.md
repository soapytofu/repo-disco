# Separate analyst diagnostics for the witness/map pilot

**Zero new model calls. Original primary score remains 8/16.** This is a verifier-only investigation of two saved map responses, not an automatic retry, model repair attempt, or rescore. Original response/candidate/result bytes are copied under `parents/` and pinned to their published paths.

| Parent | Analyst change | Question |
| --- | --- | --- |
| Trial 06, deep/shared proof failure | Add `if q != j { O2.PutAt(m,k,x,q); }` after `DropAt(outer,k,q)` in each of the two quantified proof blocks | Does the omitted inner-update value fact suffice under the existing key-set facts and contracts? |
| Trial 15, shallow/separate warning-only exit | Replace the two concrete left-hand map comprehensions per helper with the equivalent `K.Drop(K.Put(K.Put(m,k,x),j,y),k)` expression | Can the existing observation lemmas support a representation with stable triggers, without additional lemma calls or relaxed warning flags? |

The first edit has two textual sites in one body. The second has two sites in each of two identical bodies; all `ObservePut`, `ObserveDrop`, and `Equal` call counts remain unchanged. These are targeted sufficient-edit hypotheses, not minimum repairs or new model successes. All signatures, contracts, export views, clients and provider sources are unchanged. Both candidates pass the already frozen task guard and envelope without modifying those policies.

Three offline test methods pass, checking exact edits, complete source reconstruction, original failure status, unchanged lemma-call counts for the warning case, and isolated runtime imports. Before any job submission, a metadata review found that the JSON writer's final newline was absent from the raw hash recorded by the preparation code. The extraction records/test were aligned with the exact archived bytes; `metadata-correction-initial/` and `metadata-correction.json` preserve the initial records and both manifest hashes. No candidate proof bytes changed and no compute retry occurred.

## Results

Both analyst candidates passed on Cannon job **58545377**, nonpreemptible `test`, in 10 seconds. Each returned **16 verified, 0 errors, no warnings, exit 0**. Dafny was invoked once per candidate with `verify --verify-included-files All.dfy`; there were no retries, model calls or relaxed warning flags.

- **Trial 06 diagnostic:** the two added inner-update observations suffice for the unchanged pointwise obligations. This supports the missing-value-fact diagnosis; it does not establish a minimum repair or award credit to the model response.
- **Trial 15 diagnostic:** replacing the four concrete comprehensions with the existing `K.Put`/`K.Drop` representation removes the trigger warnings while preserving every lemma-call count and contract. This confirms a warning-free formulation for this response, not a general guarantee about quantifier triggers.

The inner-update observation can be applied using key-set facts already in scope, before the outer-update value observation. Accordingly, the frozen map reference's four-stage path is an explanatory proof route, not a lower bound on necessary contract-application depth. The original reference annotation and pilot inputs are preserved.

The review checked all **514 original model-archive files**, 46 parent inputs, the unchanged frozen guard/envelope, exact compute source hashes and diagnostics. The original **8/16** primary score, its proof failures and warning-only result remain unchanged. These two checks are analyst diagnostics, not two new model trials or a 10/16 rescore.

## Evidence

- [Exact edits and protected-file review](preservation-review.json), [candidate definitions](cases.json)
- [Compute source and full verifier output](verification-001/), [outcome review](verification-001-review.json), [archive hashes](verification-001-sha256.json)
- [Scheduler stdout](verify-58545377.log), [stderr](verify-58545377.err), [accounting](accounting-58545377.txt), [submission and live partition settings](submission.json)
- [Transfer inventory](transfer.json), [local tests](offline-tests.log), [Cannon offline tests](remote-offline-tests.log)
- [Original pilot results](../witness-map-calibration-pilot-001/RESULTS.md)

The outcome review is offline: `python3 -B experiments/witness-map-diagnostic-001/review.py verification-001`. It does not call Dafny or a model. `prepare.py` intentionally refuses to overwrite the existing diagnostic inputs.
