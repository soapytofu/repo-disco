# Reordering fixes all four deep restriction/merge failures

**Confirmed November 12, 2026: all four analyst-reordered workspaces strictly verify.** Job **60085443** completed on nonpreemptible `test` / `holy8a24301` in **44 seconds**, without requeue or automatic retry. **Zero model calls.** Each diagnostic verifies **20 obligations, zero errors and zero warnings**, exit code 0.

| Parent response | Original saved result | Reordered diagnostic |
| --- | --- | --- |
| map-balanced-04, deep/shared | 19 verified, one certificate-precondition error | 20 verified, zero errors/warnings |
| map-balanced-08, deep/separate | 18 verified, two certificate-precondition errors | 20 verified, zero errors/warnings |
| map-balanced-09, deep/shared | 19 verified, one certificate-precondition error | 20 verified, zero errors/warnings |
| map-balanced-11, deep/separate | 18 verified, two certificate-precondition errors | 20 verified, zero errors/warnings |

Original results above are reused from their exact saved verifier records, not rerun. There are four parent-linked diagnostics but only **two unique repaired workspace contents**: the shared pair is identical, as is the separate pair. These checks are not four independent semantic instances.

## What changed

In each of six editable bodies, the analyst moved this existing call:

```dafny
O1.Certify(K.Restrict(m, keep), K.Restrict(n, keep));
```

after these two existing prerequisite calls:

```dafny
O2.RestrictKeys(m, keep);
O2.RestrictKeys(n, keep);
```

All statement text and multiplicities are preserved. No new assertion, lemma call, assumption, signature, contract, import, provider or client is added. All reordered bodies pass the same frozen output guard; there is no parser change or syntax projection. The original certificate calls failed because their restricted-map disjointness precondition was not yet supported by the key-set facts.

The successful verifier results establish that **this reorder alone is sufficient for the four saved failures**. They support a concrete prerequisite-ordering explanation within the decomposed interface. They do not establish minimal repairs, unavoidable reasoning depth, general causal effects of depth/sharing, or improved model performance. The earlier partial-cohort [diagnostic](../map-order-diagnostic-001/RESULTS.md) remains a separate experiment.

## Original model score and evidence stay unchanged

The [fresh pilot](../map-development-pilot-002/RESULTS.md) remains **12/16 strict model successes**. These four analyst repairs are not rescored as model successes and are not written into its candidates, responses, accepted records, policies or ledgers.

The independent [review](results-review.json) verified all **812 original model-archive files** unchanged, the original structured score hash, and **72 copied parent files** byte-for-byte. Exact reconstruction and source-hash checks cover every diagnostic input; six editable body boundaries and all thirty other source files are protected by the mutation tests. The original failures, including their precondition diagnostics, remain available under [parents](parents).

## Full logs and reproducibility

- [cases.json](cases.json), [exact reordered sources](fixtures), [parent/score provenance](provenance.json), and [154-file source/runtime manifest](manifest.json), SHA-256 `84ddfb4499af4dfd7555ed0c07c0f4aa2e324162574833cced59466dac127ced`.
- [Verification archive](verification-001): exact staged inputs, toolchain/environment, all four verifier stdout/stderr records and raw CSV bytes. [Archive digests](verification-001-sha256.json) cover 165 files; the [transfer inventory](transfer-core.json) validates all 171 received files.
- [Independent review log](review-001.log) and [structured reviewed outcomes](results-review.json).
- [Submission](submission-core.json), [live partition and exclusive lock](submission-core.lock), [accounting](accounting-60085443.txt), [job stdout](verify-60085443.log), and [job stderr](verify-60085443.err).
- Four offline mutation/guard/staging tests passed [locally](offline-tests-001.log) and [on Cannon](remote-offline-tests.log) before submission, with no actual verifier or API calls in those tests.

Reproduce the evidence review locally without running Dafny or any model:

```sh
python3 -B experiments/map-order-diagnostic-002/review.py
```

All proof verification ran on the compute node with Dafny 4.11.0 and Z3 4.12.1, all includes enabled and one bounded invocation per diagnostic. No additional paid requests, repairs, retries or model-score changes were made.
