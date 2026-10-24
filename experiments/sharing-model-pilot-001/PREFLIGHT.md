# Verifier-only preflight results

Job 54969539 completed on shared in 47 seconds. All 12 checks matched expectations. Responses are authored fixture replays, not model outputs.

| Condition | Replay input | Entry | Outcome |
| --- | --- | --- | --- |
| shared | reference | All.dfy | SUCCESS |
| shared | reference | ClientA.dfy | SUCCESS |
| shared | reference | ClientB.dfy | SUCCESS |
| shared | missing | All.dfy | PROOF_FAILURE |
| shared | missing | ClientA.dfy | PROOF_FAILURE |
| shared | missing | ClientB.dfy | PROOF_FAILURE |
| separate | reference | All.dfy | SUCCESS |
| separate | reference | ClientA.dfy | SUCCESS |
| separate | reference | ClientB.dfy | SUCCESS |
| separate | missing | All.dfy | PROOF_FAILURE |
| separate | missing | ClientA.dfy | PROOF_FAILURE |
| separate | missing | ClientB.dfy | PROOF_FAILURE |
