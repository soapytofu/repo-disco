# Fresh balanced map pilot results

**Completed November 12, 2026: 12/16 strict whole-workspace passes.** Job **60073401** completed on `test` / `holy8a24102` in **4m05s**, with preemption disabled and no requeue. All sixteen approved requests returned with unique provider IDs and **zero SDK retries**. All sixteen JSON envelopes and proof bodies were admitted; the remaining four outcomes were proof failures, with no parser, frontend, timeout or warning-only outcomes. The ledger is closed, all sixteen calls are consumed, and no further calls are authorized.

## Balanced cell results

Each entry is strict successes / two fresh responses. The complete [trial-level report](results-review.json) also gives editable-helper completion, supplied-client closure, tokens and request IDs.

| Map task | Shallow/shared | Shallow/separate | Deep/shared | Deep/separate | Total |
| --- | --- | --- | --- | --- | --- |
| D4-M1 Fresh move composition | 2/2 | 2/2 | 2/2 | 2/2 | **8/8** |
| D4-M2 Restriction over disjoint merge | 2/2 | 2/2 | 0/2 | 0/2 | **4/8** |
| Total | 4/4 | 4/4 | 2/4 | 2/4 | **12/16** |

Observed token usage: **58,792 input + 11,541 output = 70,333 tokens**. Token usage is not a dollar-cost estimate. Shared and separate conditions each have six strict successes out of eight; this cohort does not show a sharing advantage. These totals aggregate only two related development tasks and must not be treated as independent-family evidence.

## The four failures are prerequisite-ordering failures

Trials `map-balanced-04` and `09` (deep/shared) and `08` and `11` (deep/separate) request:

```dafny
O1.Certify(K.Restrict(m, keep), K.Restrict(n, keep));
```

before calling `O2.RestrictKeys(m, keep)` and `O2.RestrictKeys(n, keep)`. The certificate requires disjointness of the restricted maps, but the supporting key-set facts have not yet been supplied through the decomposed interface. Every reported error is at that certificate call, related to `Ops1.dfy`'s disjointness precondition. Shared failures report 19 verified / one error; separate failures report 18 verified / two errors, one per editable helper. All use the newly clarified single-ensures syntax and pass the same frozen guard.

The [source audit](source-audit.json) records exact body offsets and hashes. The earlier [analyst diagnostic](../map-order-diagnostic-001/RESULTS.md) verified sufficient call reorders for the **previous cohort**. It is supporting mechanism evidence; those edited candidates are not results from this new pilot, and no new candidate was repaired or rerun here. This repeated failure is evidence about using cross-module prerequisite contracts, not just finding a helper name. It does not establish a necessary proof-depth lower bound or a general causal effect.

No partial editable-helper completion was observed in the four failed workspaces: 0/1 shared or 0/2 separate. Both supplied clients verify locally against declared helper contracts, but **0/2 clients are dependency-closed** because the needed helper remains unproved. We do not credit those local client passes as repaired repositories.

## Syntax, copying and comparison limits

All sixteen outputs were admitted under the unchanged parser. The clarified prompts therefore succeeded at the syntax-admission gate in this cohort. The prior interrupted run remains six strict passes among nine returned responses, with one body-policy rejection and two proof failures; it is not pooled into this score. Different samples and unequal prior completion prevent a causal estimate of the prompt clarification's effect.

Seven of eight separate outputs have byte-identical helper bodies. The remaining one, trial 13, differs only by the bound-variable rename `q0` / `q1`. The separate condition permits copying and has two editable bodies rather than one. Fresh move remains at ceiling; restriction has a clear descriptive shallow/deep contrast here. Both are inspected development instances, not held-out tasks, and two responses per cell do not support broad statistical conclusions.

## Preserved evidence and reproducibility

- [Frozen proposal copy](frozen-001/freeze.json): `e50e4cea1d6e6c1a4dcbc8815b25f378854d9e80ae6e88aa31a0fcd881940f3d`.
- [Runtime freeze](runtime-freeze.json): `2923c413d110e8ff31d1b2c4b3a056c6f80562ae9a895fbc4758d3a9a3f3ebff`.
- [Human authorization](authorization.json), [exclusive submission](submission.json), [live partition record](submission.lock), [scheduler accounting](accounting-60073401.txt), [job stdout](model-60073401.log) and [stderr](model-60073401.err).
- [Full model archive](model-001): exact requests, raw provider responses and metadata, extraction decisions, guarded source files, verification stdout/stderr/CSV, token usage, target metrics and accepted-source hashes. [812 model-file digests](model-001-sha256.json) and [819 transferred-file digests](transfer-001.json) are recorded.
- [Independent review output](review-001.log), [structured results](results-review.json), and [source audit](source-audit.json): 120 protected-file comparisons and 24 protected-body boundaries pass; exact frozen order and all source/contracts are preserved. All 646 original model-archive files are also unchanged.
- [20 offline tests](runner-tests.log) and [Cannon fake-transport preflight](environment-preflight.log) preceded submission; they made no provider requests or Dafny runs. The live job alone performed the sixteen authorized model requests and candidate verifications.

Reproduce the completed evidence review without provider or verifier calls:

```sh
python3 -B experiments/map-development-pilot-002/review_results.py
```

The current evidence supports a repeated prerequisite-ordering failure and clean syntax admission. Any broader task collection, intervention or new model evaluation needs a separate scope and budget; no unused requests remain in this run.
