# Separated witnesses and overwrite/delete reasoning

**Verifier-only development; zero model calls.** Eight variants cover two semantic instances × shallow/deep exported interfaces × shared/separate helper bodies. Five construction/mock-staging tests passed locally and in Cannon's Python environment. Job **58529512** was submitted once on live-confirmed non-preemptible `test`, 2 CPUs/8 GB/20 minutes, no requeue. Actual Dafny results are pending.

| Instance | Obligation | Intended distinction |
| --- | --- | --- |
| `separated_witness` | Construct two points in both intervals, separated by a positive required gap | Both membership obligations, a separation obligation, and correctly matched witness arguments must hold. The deep reference composes membership → join → finish; the shallow interface accepts arithmetic bounds directly. |
| `overwrite_delete` | Overwrite two keys then delete the first; prove the conditional normal form for equal and distinct keys | Alias cases are allowed. The deep reference tracks membership and values through intermediate maps; the shallow interface exposes complete operation equations. |

The interval assumptions guarantee room for the required gap, rather than merely nonempty overlap. The map contract imposes no distinct-key precondition. Two immutable clients exercise each helper contract, including translated/swapped interval arguments and swapped map-update arguments.

The 64 planned controls comprise **8 reference passes, 48 proof failures, and 8 hidden-export resolution failures**. Wrong witness bounds/gaps, omitted second-witness facts, missing inner-map value facts, wrong intermediate snapshots/deletion keys, and omitted alias/distinct branches are targeted separately. A parse error does not count as a proof failure. Sources, expected outcomes, and runtime are pinned in `manifest.json`; `preflight.py` runs each control exactly once on a compute node and archives exact inputs plus stdout/stderr.

Providers, client bytes, and helper contracts are fixed within each semantic instance. Sharing changes one editable proof body versus two copyable bodies; this also changes editable size and proof duplication. Reference paths are design annotations, not proof-minimality results. These tasks have not been tested with a model, are not held out, and do not yet establish greater model difficulty or a causal sharing effect. Prior frozen tasks and pilot scores are unchanged.

- `build.py`, `tasks.json`, `checks.json`, and `fixtures/`: reproducible definitions and all control bytes.
- `offline-tests.log`, `remote-offline-tests.log`: construction and mocked staging tests; no Dafny/model calls.
- `submission.json`, `verify.sbatch`: single submission and live non-preemption evidence.
- `ops.py`: bounded verifier-only stage/status/fetch operations; no key or provider access.
