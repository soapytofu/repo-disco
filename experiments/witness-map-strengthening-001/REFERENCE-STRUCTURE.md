# Reference structure and interpretation

These annotations describe the verified, analyst-authored proofs in `verification-001`. They are not minimum proof depths, dynamic execution traces, or model results. Count **contract-application stages** separately from edges between applications. Arithmetic, case splitting, and quantifier introduction are proof work even when they add no provider call.

| Instance / interface | Reference provider stages | Longest annotated provider path | Additional reasoning |
| --- | ---: | --- | --- |
| Separated witnesses / shallow | 1 (0 edges) | `Api.Direct` | Choose `u = max(a,c)`, `v = u + gap`; discharge membership/separation bounds from four width/overlap assumptions. |
| Separated witnesses / deep | 3 (2 edges) | `Ops1.Left/Right` → `Ops2.Join` → `Api.Finish` | Instantiate membership/join for **both** witnesses. `Ops1.Separate` is an independent prerequisite of `Finish`, not a fourth serial stage. |
| Overwrite/delete / shallow | 2 (1 edge) | `Api.ObservePut/ObserveDrop` → `Api.Equal` | Five operation equations (the fifth in the distinct-key case), domain equality, pointwise proof, and alias cases. Observation order itself is not a dependency chain. |
| Overwrite/delete / deep | 4 (3 edges) | `Ops2.DropAt(v,k,q)` → `Ops2.PutAt(u,j,y,q)` → `Ops2.PutAt(m,k,x,q)` → `Api.Equal` | Along the `q != j` value path: membership in the dropped result yields membership in `v`, then `u`, then the original map. The pointwise facts are universally introduced before `Equal`. Separate key-set facts support domain equality and right-hand observations. |

For the map path, `u = Put(m,k,x)` and `v = Put(u,j,y)`. The final arrow includes the `forall` statement's pointwise postcondition; it is not a claim that one lemma call directly proves the entire universal formula. In the `q == j` branch, the outer write supplies the value directly, so the path is shorter. Calls to `DropAt(m,k,q)` can obtain membership from the established domain equations; their later textual location does not require counting them after the inner `PutAt` as another serial stage.

The negative controls support specific fixed-proof sensitivity statements:

- Interval `missing_second` in deep mode loses the second `Joined` fact required by `Finish`; `short_gap` violates `Separate`'s precondition.
- Map `missing_inner` loses the value correspondence to the original map and fails the pointwise equality. `wrong_snapshot` additionally fails a membership precondition; it is not a pure value-only ablation.
- Skipping either key-alias case fails the helper postcondition. The new contract does not assume distinct keys.
- Hidden shortcuts fail resolution and are reported separately from these proof failures.

These interventions do not establish that each original reference call is necessary among **all** possible proofs. The alternative-proof validation explores different witness selection and case-splitting strategies under the same contracts.

## Matching and shared-proof reuse

Within each semantic instance, all four cells have nine files, the same provider implementations, two immutable client targets, and the same helper specification. Shallow/deep changes which named export view is available; it does **not** change physical include depth. In shared mode `HelperB.Prove` forwards to `HelperA.Prove`; separate mode gives each helper its own editable body. Shared mode therefore includes an extra forwarding edge for the second client. The stage counts above start **inside the editable helper** and exclude client calls/forwarding, so they are comparable as provider-interface annotations.

Separate mode has two editable bodies, and copying a proof is allowed. Provider definitions remain shared by both clients in both modes. Measure accepted whole-workspace completion, body duplication and generation workload; do not interpret this as a pure equal-work sharing intervention or zero common definitions in the separate condition. Both instances are development tasks already inspected by the researcher. Model difficulty and sharing effects remain unmeasured.
