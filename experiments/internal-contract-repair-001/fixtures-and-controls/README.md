# Fixed internal API, two stale method bodies

This prospective verifier-only study constructs **two new repair seeds** from
the published `internal-contract-propagation-001` work. The host selects and
locks the new internal API before a future repair system sees the source. Each
seed keeps the old helper body and old caller body. Only the two method bodies
are prospective edit locations; the new helper contract, public client contract,
imports, signatures, kernel definitions and include graph stay fixed.

The arithmetic API returns a relative advance instead of an absolute endpoint.
The map API returns the extracted entry instead of the remainder. These are
meaningful changes in the return value and legal input domain. We expect both
`Helper.Transfer` and `Client.Target` to fail in each new seed, with real
postcondition and call-precondition diagnostics. This expectation is not yet a
verification result.

The two old bodies can retain the original end-to-end behavior. The defect here
is that they no longer implement and compose through the selected new internal
API: the helper violates its fixed contract, and the caller proof fails when it
reasons from that contract. This is not a claim of newly observed public runtime
misbehavior.

`cases.json` contains **only the two fresh seed checks**. The eight entries in
`reused-controls.json` link exact source bytes and reviewed evidence from job
60723362. They are not new observations and will not be submitted again:

| Reused parent variant, once per task | Helper | Client | Role in the new study |
| --- | --- | --- | --- |
| `paired_repair` | Pass | Pass | Coordinated body repair |
| `alternative` | Pass | Pass | Alternative coordinated body repair |
| `helper_only` | Pass | Fail | Repair only the helper body |
| `contract_only` | Fail | Pass locally | Repair only the client body |

The parent's `caller_only` variant has the **old** helper header and is excluded.
An individual client proof is conditional on the helper contract; its local pass
does not certify a workspace with a failed helper implementation.

The dependency is `Kernel → Helper.Transfer → Client.Target`, with the client
also using the kernel directly. Named CSV observations, not a synthetic closure
score, must establish both seed failures. The arithmetic kernel definition did
not emit a separate unit in the parent run; it remains hash-protected and is not
counted as a verified provider observation. The three map kernel well-formedness
units must all pass.

`build.py` makes exact snapshots of the selected parent sources, reviewed records,
raw streams and CSV. It constructs each seed by taking `Helper.dfy` from
`contract_only` and `Client.dfy` from `reference`; the other files are identical.
`parent-inputs.json` preserves original paths and hashes. `tasks.json` carries
typed per-file interfaces and masked-body hashes for the separately developed
method-body guard. It is host metadata, not a model prompt.

Offline checks cover exact old bodies/new headers, public and kernel preservation,
source/evidence reuse, concrete counterexamples, finite semantic boundary cases,
deterministic rebuilding and isolated fake-process staging. They do not run
Dafny. `verify.sbatch` is the single compute-only entry point for two seed checks.
The standard-library verifier pins Dafny 4.11.0 and Z3 4.12.1, saves exact sources,
stdout, stderr and raw CSV, checks both named outcomes, and never retries.

These are two constructed development migrations from inspected arithmetic/map
lineages. They are neither held-out families nor independent evidence of a
general need for multi-file repair. The controls establish that the particular
one-sided body repairs are insufficient under the selected fixed API. Other
implementations may exist. No model prompts, model runner, paid authorization or
model result are part of this fixture bundle; prior sources and scores are
unchanged.
