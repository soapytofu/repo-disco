# Separated witnesses and overwrite/delete reasoning

**Verifier-only development; zero model calls.** Eight variants cover two semantic instances × shallow/deep exported interfaces × shared/separate helper bodies. Five construction/mock-staging tests passed locally and in Cannon's Python environment. Job **58529512** completed on live-confirmed non-preemptible `test` in **2m51s**, 2 CPUs/8 GB, no requeue. **All 64 outcomes matched**: eight strict reference passes, 48 proof failures (exit 4), and eight hidden-export resolution failures (exit 2). No parse errors or warnings occurred. Exact archived inputs match the submitted manifest.

| Instance | Obligation | Intended distinction |
| --- | --- | --- |
| `separated_witness` | Construct two points in both intervals, separated by a positive required gap | Both membership obligations, a separation obligation, and correctly matched witness arguments must hold. The deep reference composes membership → join → finish; the shallow interface accepts arithmetic bounds directly. |
| `overwrite_delete` | Overwrite two keys then delete the first; prove the conditional normal form for equal and distinct keys | Alias cases are allowed. The deep reference tracks membership and values through intermediate maps; the shallow interface exposes complete operation equations. |

The interval assumptions guarantee room for the required gap, rather than merely nonempty overlap. The map contract imposes no distinct-key precondition. Two immutable clients exercise each helper contract, including translated/swapped interval arguments and swapped map-update arguments.

The 64 completed controls comprise **8 reference passes, 48 proof failures, and 8 hidden-export resolution failures**. Wrong witness bounds/gaps, omitted second-witness facts, missing inner-map value facts, wrong intermediate snapshots/deletion keys, and omitted alias/distinct branches are targeted separately. A parse error does not count as a proof failure. Sources, expected outcomes, and runtime are pinned in `manifest.json`; `preflight.py` runs each control exactly once on a compute node and archives exact inputs plus stdout/stderr.

Providers, client bytes, and helper contracts are fixed within each semantic instance. Sharing changes one editable proof body versus two copyable bodies; this also changes editable size and proof duplication. Reference paths are design annotations, not proof-minimality results. These tasks have not been tested with a model, are not held out, and do not yet establish greater model difficulty or a causal sharing effect. Prior frozen tasks and pilot scores are unchanged.

- `build.py`, `tasks.json`, `checks.json`, and `fixtures/`: reproducible definitions and all control bytes.
- `offline-tests.log`, `remote-offline-tests.log`: construction and mocked staging tests; no Dafny/model calls.
- `submission.json`, `verify.sbatch`: single submission and live non-preemption evidence.
- `ops.py`: bounded verifier-only stage/status/fetch operations; no key or provider access.


The [diagnostic audit](diagnostic-audit.json), [reproducible hash review](verification-001-review.json), and [full raw evidence](verification-001/) preserve all outcomes. Missing second-witness facts fail `Finish` preconditions; a too-short gap fails `Separate`; missing inner-map observations fail pointwise equality. Hidden helpers fail name resolution, separately from mathematical proof failures. See `verify-58529512.log/.err` and `accounting-58529512.txt` for scheduler evidence.

A separate [task registry](protocol/body_guard.py) uses the unchanged v4 grammar with only task call/variable bindings and version changed. Five offline test methods pass: 56 reference/semantic-negative sources reconstruct exactly, all eight hidden-call controls are rejected, and ambiguous output, mutation and bypass checks remain enforced. The tolerant envelope is composed with this registry; it does not alter proof strings. `protocol/registry-freeze.json` pins both layers. No future model pilot has been frozen or authorized here.

[Reference structure](REFERENCE-STRUCTURE.md) records family-specific contract stages, branching/quantifier qualifications, fixed-proof sensitivity evidence, and sharing/forwarding confounds. Provider stages are 1/3 for the witness interfaces and 2/4 for map interfaces; these are annotated reference paths, not minimum proof depths.

[Eight alternative proofs](alternative-proof-001/README.md) also passed strictly on Cannon after exact tolerant-envelope/guard reconstruction. These use upper-endpoint witness selection and query-key map case splitting, with unchanged contracts. Job 58532292 completed in 28 seconds; no warnings and zero model calls.
