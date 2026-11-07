# Authorized sixteen-call witness/map pilot

The user approved the [frozen 16-call proposal](../witness-map-calibration-001/README.md) with no retries on November 6, 2026 Eastern. This execution directory is separate from the unchanged proposal and prior experiments. **Maximum 16 requests total**, eight variants × two fresh samples. No feedback, budget reassignment, SDK retries, Slurm requeue, automatic restart or alternate runner.

The bounded runner is ready; **15 offline fake-transport tests pass**. They cover exact payload/order and duplicate samples, one-attempt SDK configuration, durable reservations, transport/response persistence failures, deadline checks, duplicate request IDs, runtime/seed drift, no restart, strict verifier classification, source protection, exact wrapped reference replay, envelope versus body rejection, and audit/tamper detection. These tests make no API or Dafny calls.

`runtime-freeze.json` binds runner, unchanged request gate, tests/log, environment check, review script, scheduler script and bounded SSH operations to proposal hash `ac38dd5c49d89afa70c4fa1700b6af4ec6317df639bacb66acd9257b429a4732`. `frozen-001/` is byte-identical to the approved plan; `inputs/` contains exactly its pinned dependencies. No old parser or prompt is changed.

A single fresh compute job will consume/delete the private credential handoff, keep it in process memory, execute the slots in frozen order, and clear it on exit. A reservation is persisted before every dispatch. An ambiguous request or persistence/infrastructure failure closes the batch; completed incorrect proofs or rejected outputs consume their slot and remain evaluation outcomes. The host records whether JSON extraction succeeded separately from the bounded proof-language guard.

Before submission, validate both freezes, bind the explicit approval to their hashes and a fresh deadline, confirm live nonpreemptible `test`, inspect output/submission/queue state, and create an exclusive submission lock. `model-001` must not exist. Verification runs only on the allocated compute node, with unchanged strict flags and 60-second per-candidate limit. Scheduler limit is 90 minutes; no automatic retries. Existing connection is socket `repodisco-codex-11.sock`. No model connectivity test is needed.

The final archive will include every reservation/request ID, frozen payload, full provider response, token/latency metadata, extraction/rejection decisions, exact candidate and protected-source hashes, verifier stdout/stderr, accepted records and scheduler accounting. Review reports eight task-specific cells (two samples each), never pooling the two semantic instances as one condition. Sharing changes one versus two copyable bodies, so it is not an equal-work causal intervention; this is development calibration.

Current status: awaiting private key handoff and remote offline preflight; no model job submitted and zero requests dispatched.
