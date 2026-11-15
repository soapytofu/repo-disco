# Frozen repair-selection pilot — stopped collection

The exact 32-trial study is frozen in [frozen-001](frozen-001/), with freeze SHA256
`9a3ac2546edc6c79307826766af3517bdc8d9a8fe629a2ba0239660f4ead778a`.
All 45 verifier controls, 11 pilot preparation tests and the independent audit
of all eight requests passed. The freeze pins 109 files and 1,095 repository
inputs to source commit `cfa51ee966b3f54cfcec3badb8c8f77fe310da94`.
See [reviewed-prompts.json](reviewed-prompts.json) for the prompt audit.
The batch was admitted once through the existing window ledger. Its first
request timed out without a returned response; the session closed and the other
31 slots were not dispatched. The [main result record](../RESULTS.md) and separate
[stopped-run audit](stopped-review-001.json) distinguish this infrastructure event
from model proof outcomes. Frozen inputs and the earlier results are unchanged.
Nothing in this directory dispatches a model or scheduler job.

There are four constructed development workspaces, two feedback arms and four
fresh responses per task/arm. Both eligible proof bodies are returned each time.
The architecture is always `pipeline`; there is no sharing or depth factor.
The only treatment difference is detailed original verifier feedback versus a
failure notice. Both arms see the same full failing source, per-file symbol/type
environments and syntax. Empty reconstruction templates, seeded-fault metadata,
reference solutions and counterexamples are host-only.

The exact task IDs and all 32 positions come from the parent `plan.json`, written
before compute outcomes. Each eight-trial block contains every task/arm once,
and each cell's mean position is 16.5. The execution schema uses the existing
`verifier_diagnostics` / `failure_notice_only` names; the parent design's
`diagnostics` / `notice` labels map to them without changing order. Actual
`semantic_instance` values come from the source tasks and registry, including
the map task suffixes. No task metadata is normalized or dumped into a prompt.

The model and runtime settings remain Claude Opus 4.5, temperature 1, maximum
4,096 output tokens, independent contexts, one request per trial and no retries,
repair-after-feedback or reassignment. The proposal allocates 32 calls within
the user's existing aggregate 128-call window; it grants no separate budget.
The coordinator still controls the canonical remaining ledger and admission.

Strict whole-workspace verification is primary. The unchanged `target_metrics`
interpreter separately measures both editable helpers, immutable providers and
client completion under the declared graph A → B → clients. Each failing parent
must have one locally verified helper, one failing helper, locally verified
clients, and zero clients verified with their full declared dependency chain.
A local client pass alone is insufficient. The declared graph is not a proof
that every accepted candidate must call A; observed calls remain separate.

After the compute reviews, `prepare.py measurements` constructs
the exact reference-derived named scope and an unendorsed gate draft. It does
not render prompts. Root must endorse those exact source, policy, measurement,
syntax and design hashes and supply the published source commit. Only then can
`prepare.py freeze` create `frozen-001`. That output will include four base and
host-template workspaces, eight exact payloads, 32 trial slots, the entire frozen
policy with all nested dependencies, and full input/evidence hash inventories.
The study's review manifest and every pinned auditor, transitive dependency,
test, report and log are validated and included in that input inventory too.
`prepare.py check` will rebuild deterministically without executing tools.

The offline tests initially use synthetic diagnostic and CSV data to check
feedback fidelity, source/metadata separation, dependency-closed scoring,
order/budget constraints and refusal to render before the gate. Actual prompt,
standalone-policy and rebuild checks remain explicitly skipped until root
endorsement. A synthetic test outcome is never recorded as a fixture proof.

The four workspaces are adaptive development instances in two inspected
families. This is repair choice within two declared eligible files, with their
roles visible in the source; it is not blind repository discovery. The 32
responses are not 32 independent tasks. No causal sharing/depth, minimality or
unseen-family claim follows. Reserved tree and transition families and all
earlier frozen experiments remain unchanged.
