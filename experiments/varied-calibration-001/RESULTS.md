# Four varied calibration tasks: verifier results

November 9, 2026 Eastern. **126/126 current controls matched their declared
outcomes. Zero model calls.** These are analyst-authored development fixtures;
no model difficulty or held-out performance has been measured.

| Instance | Reference passes | Ordinary proof failures | Termination failures | Hidden-export failures | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bounded allocation | 4 | 20 | 0 | 4 | 28 |
| Map-swap involution | 4 | 26 | 0 | 4 | 34 |
| Clamp distance | 4 | 24 | 0 | 4 | 32 |
| Prefix splitting | 4 | 20 | 4 | 4 | 32 |
| **Total** | **16** | **90** | **4** | **16** | **126** |

All reference exits were strictly zero. There were **no warnings or parse
errors** in current controls. Hidden-export controls have unresolved-name errors
and secondary “expected method call” diagnostics; they are deliberately distinct
from mathematical failures. [diagnostic-audit.json](diagnostic-audit.json) records
all categories and error lines. Wrong witnesses/boundaries fail preconditions;
missing map facts fail quantified postconditions; nondecreasing recursion fails
termination checks. Empty helpers fail their protected target postconditions.

## Evidence lineage

| Job | Scope | Result | Runtime |
| --- | --- | --- | --- |
| 59351309 | Original four-family core | 32/32 expected | 2m05s |
| 59352546 | Deliberately revised map core | 8/8 expected | 2m22s |
| 59352900 | Current targeted negatives | 94/94 expected | 4m29s |

All jobs ran on live-confirmed nonpreemptible `test`, with two CPUs, 8 GB,
Dafny 4.11.0, Z3 4.12.1, `--verify-included-files`, one invocation per check and
no requeue or automatic retries. No verification ran on a login node or Mac.

[The current inventory](current-evidence.json) uses 24 byte-identical original
non-map observations, eight revised map observations and 94 targeted negatives.
Thus there were **134 actual verifier invocations**, of which eight original map
core outcomes were superseded but preserved. Reuse is not a new independent trial.
The [combined gate](revision-002/reference-gate.json) checks exact sources and
verifier-package bytes before allowing the negative phase.

The original granular map interface did not lengthen the chosen reference path.
Revision 002 adds an opaque domain certificate and requires it when recovering
map keys and values. Its missing-certificate controls fail as intended. The old
successful proofs are retained, not silently replaced or rescored. The other
three task definitions and all client target contracts remain unchanged.

Raw source snapshots, per-control stdout/stderr, commands, hashes, environment,
Slurm output/error/accounting and submission records are in `verification-001/`,
`revision-002/verification-001/` and `revision-002/verification-002/`. All are
reviewed by the corresponding review JSON and SHA256 inventory. Public scheduler
receipts omit unrelated projects' queue rows only, with explicit before/after
hashes in scheduler-redactions.json. Research inputs and diagnostics are intact.

## What depth and sharing mean here

| Task | Chosen shallow path stages | Chosen deep path stages | Scope |
| --- | ---: | ---: | --- |
| Allocation | 1 | 3 | Numeric facts versus individual bounds -> joined bounds -> existence |
| Map swap | 3 | 5 | Intermediate-map observation versus explicit domain certification |
| Clamp distance | 1 | 2 | Per-input region fact -> value fact, followed by arithmetic |
| Prefix split | 1 | 2 | Per-unfolding fact recovery; recursion on `i` is separate |

These count contract applications on an annotated sufficient **reference path**,
not the minimum proof depth. Edges equal stages minus one for the listed local
paths. Independent facts, arithmetic, quantifier reasoning and recursive expansion
are not silently collapsed into a single universal depth number. The prefix
proof has unbounded input-dependent recursion. No alternate-strategy lower bound
is established.

The [structural audit](structural-audit.json) uses the existing import-map metrics:
shallow and deep have identical import graphs within each sharing condition.
The manipulated quantity is contract factorization, not import distance. The
shared case has one editable body and a fixed forwarding helper; the separate
case has two copyable bodies. The shared forwarding path adds an import edge,
and separate reference output is exactly twice the editable body bytes. These
are known workload/structure confounds, not an equal-work causal comparison.

Whole-repository review checked **945 protected file comparisons** and **189
helper-body boundaries**. Contracts, clients and dependency bytes were preserved
within each current task. The two-client call paths are recorded explicitly;
forwarded reuse is not mislabeled as two direct calls to one definition.

## Concrete targets versus the earlier proposal

The implementation is lemma-body synthesis. Allocation proves the opaque
existential `Feasible(a,b,c,d,t)` by supplying concrete `u,w` to a certificate
lemma; it does not return an executable pair. Client A requires that feasibility
statement, and Client B uses swapped/translated bounds and a shifted total.
Clamp Client B consumes the distance bound under an `eps` premise, rather than
the ordered-input corollary suggested in the proposal. Map Client B observes a
key after the involution; prefix Client B splits the whole sequence at a bound.
These concrete contracts are pinned and verified; the original proposal remains
historical. All clients are immutable during candidate synthesis.

## Output readiness and next gate

Nine construction/revision tests passed locally and on Cannon. A separate
[registry-only output adaptation](protocol/README.md) passed eight offline tests:
110 exact source reconstructions, 16 hidden-export rejections and adversarial
scope/JSON checks. The existing bounded grammar and tolerant envelope are
unchanged. Syntactic admission does not make a proof true.

All four calibration instances remain in development and inherit existing
conditional, aggregate-sequence, interval-witness and map-update lineages.
Reserved tree/transition families were not implemented or inspected. Next is a
reviewable calibration prompt/order/settings freeze and separate paid approval;
no past budget can be reused.

Reproduce the review offline:

```bash
python3 -B experiments/varied-calibration-001/revision-002/review.py verification-002
python3 -B experiments/varied-calibration-001/review_results.py
```
