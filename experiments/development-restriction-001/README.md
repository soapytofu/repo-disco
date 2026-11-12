# Restriction over disjoint merge — D4-M2

November 12, 2026. **Initial core run failed during frontend checking; this
version is not a validated fixture. Zero model calls.** Eight offline methods
passed locally and on Cannon, but job **60033315** failed all eight core cases
before proof verification: Dafny could not infer a finite map-comprehension bound
from `q in m || q in n` in Kernel.dfy. This is a fixture construction issue,
not a proof failure or model result. The complete original sources, diagnostics,
accounting and [review](verification-001-review.json) are retained. No negative
phase was submitted. A deliberate revision will use the equivalent explicit
finite domain `q in m.Keys + n.Keys` without changing theorem/client contracts.

This implements the second map collection instance in the existing
[corpus plan](../../docs/corpus-family-split-plan.md). Four workspaces vary bundled
versus decomposed contracts and shared versus separate helpers. They are four
conditions of one development instance, with map-family ancestry shared with
swap and fresh-move tasks. No reserved test family is used.

For finite maps with disjoint domains, establish:

```text
Restrict(Merge(m,n),keep) == Merge(Restrict(m,keep),Restrict(n,keep))
```

The partial mathematical operation of disjoint merge is represented by a total
function that returns an empty map outside disjoint domains. This fallback is
explicit: the identity can fail without the disjointness assumption, because
filtering may remove the original conflict. Restriction keeps exactly the keys
in `keep`, with their original values. Empty inputs and empty filters are allowed.

ClientA consumes whole-map equality. ClientB consumes membership and pointwise
equality at a key in the restricted original merge. Both are immutable consumers
of the helper theorem, not independently synthesized programs.

Shallow mode exposes bundled observations for merge and restriction; deep mode
exposes a disjointness certificate and separate key/value facts. The reference
first establishes restricted-map domains, which justify the restricted merge's
certificate, then selects the appropriate source map for each value. Named
exports hide the alternate interface. Map extensionality is shared in both
conditions. Shared mode has one editable body with an immutable forwarding
wrapper; separate mode has two editable bodies and permits copying. Source/edit
workloads differ and are not claimed to be a pure measure of shared reasoning.

## Validation plan and evidence

Core verification checks four references and four empty bodies. Only after its
reviewed eight-check gate passes will the 30 targeted controls run: 26 expected
proof failures and four expected hidden-export resolution failures. Total:
**38 expected outcomes: four strict passes, 30 proof failures, four resolution
failures.** A resolution/parse error cannot substitute for a proof failure.

Negatives omit one source-map value observation, filter the right operand with
the empty set, incorrectly take every result value from the left operand,
discard the right operand's domain, skip the empty-left case, or omit the deep
restricted-disjointness certificate. In shallow mode removing a bundled
observation removes domain and value facts together; that is not a value-only
ablation. Full checks and source hashes are in `checks.json`.

[Eight offline methods](offline-tests-001.log) cover:

- An independent finite oracle: 2,744 admissible map-pair/filter cases, including
  512 empty-left and 343 empty-filter cases. A concrete overlapping-map example
  shows why the stated disjointness assumption matters for this totalization.
- All 38 deterministic source reconstructions; contracts, providers and clients
  are protected. Only declared helper bodies vary within a structural cell.
- Byte-exact admission of 34 semantic controls and rejection of four hidden
  calls, plus scoped-JSON, bypass and immutable-source boundary tests.
- Exact fake-process staging, strict diagnostic category tests, embedded remote
  script compilation, and pinned input integrity. No actual verifier is invoked
  by these local tests.

The separate task registry changes only bindings and version on the diagnostic's
bounded grammar. Envelope and isolated verifier files are unchanged copies;
`provenance.json` pins their origin. Existing pilot and diagnostic bytes/scores
remain unchanged. Syntax admission does not establish Dafny validity or truth.

`manifest.json` pins runtime, source and test files. `ops.py` stages an exclusive
directory and allows one submission per phase. Actual verification runs on a
live-confirmed nonpreemptible compute partition, with no requeue or automatic
retries. Unexpected outcomes are archived before deliberate versioned fixes.

This task broadens domain/set-algebra and source-selection obligations. It does
not establish higher model difficulty, minimum proof depth, an independent
family, or a causal sharing benefit. Actual model behavior requires a later
frozen and separately approved collection.
