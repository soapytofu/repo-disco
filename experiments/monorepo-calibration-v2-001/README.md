# Revised calibration: body-only protocol and strengthened reasoning tasks

**Preparation completed: all 136 selected verifier controls match their expected
outcomes across 16 variants; six freeze tests pass.** The separately authorized
[execution](../monorepo-calibration-v2-pilot-001/RESULTS.md) is now complete:
1/32 strict passes, 31 body-syntax rejections, zero retries. Its budget is exhausted.
The frozen proposal files and historical preparation records remain unchanged.
The original calibration and its 18/32 score remain unchanged.


## Frozen pilot

[frozen-001](frozen-001/README.md) pins **32 independent one-response trials**:
four development families × shallow/deep × shared/separate × two samples.
Every prompt contains only its complete empty-body seed workspace, declared file
map and body-only output instructions. No reference proofs or failure controls
enter messages. All families use the same versioned body-json-v2.1 guard.

| Family | Change / role | Selected verifier controls |
| --- | --- | ---: |
| Conditional preconditions | Retained as a protocol anchor; interacting sign/offset conditions | 26 |
| Sequence offset induction | Weighted concatenation with a generalized recursive offset and shifted suffix | 42 |
| Interval witness | Construct one witness for two interval contracts, then compose their facts | 30 |
| Map transfer | Aliasing, exact balances, conservation, domain and frame preservation | 38 |

Total: **16 reference passes, 108 ordinary proof failures, 4 termination failures,
8 explicit hidden-helper/name failures**. The sequence controls come from the
valid portion of job 56197680; the first relational provider failures in that job
and revision 002 frontend errors are preserved but excluded from selected evidence.
Corrected relational revision 003 passed all 30 controls in job 56197984 (1m52s).
No helper/client contract was weakened to make a reference pass.

The model ID and inference settings match the previous calibration (Opus 4.5,
maxTokens 4096, temperature 1.0); each sample gets fresh context, no feedback,
no automatic retries or quota reassignment. Four cyclic Latin rows are assigned
once each, families interleaved, with cell/family order reversed for sample two
(seed 20261029). Source, prompt, guard, order and evidence hashes are pinned.
The proposed **32 new requests have not been authorized or dispatched**.

This is a diagnostic development pilot. There is one semantic instance per family;
shared/separate editable-body count differs, and depth is reference-relative.
The conditional instance is reused with a new output protocol. Other tasks and
output policy both changed, so a future comparison against the original score
cannot isolate either change's effect. Main 192-call collection stays deferred.

Freeze SHA-256: `c37781be6014e0b5ba53ae99b28a90bf7a5bf05be2cd15650098dadc3ac0a590`.

## Output protocol

The frozen `frozen-001/guard/body_protocol.py` accepts a strict JSON object mapping the exact editable helper
filenames to **body contents only** (without surrounding braces or declarations).
A single whole-response JSON fence is allowed. Prose search, duplicate keys,
nested/double-escaped JSON, extra files, and automatic escape/proof repairs are
rejected. The host inserts each body into pinned seed files; all imports,
attributes, contracts, decreases clauses, wrappers, providers and clients remain
byte-identical. Body whitespace is model-owned; file suffix/newlines are host-owned.

The frozen `frozen-001/guard/grammar.py` is a separately versioned derivative of the reviewed inline-if
diagnostic grammar. It permits bounded pure conditional expressions as well as
statement branches, assertions and explicitly allowed lemma calls. It forbids
assumptions, reveals, attributes, declarations, loops and cross-helper delegation.
It is an output policy for trusted seed templates, not a general Dafny sandbox.
Dafny still judges semantic validity. Empty proofs are syntactically admissible.

Nine offline tests include byte-exact reconstruction of all 16 original verified
reference workspaces and all 11 previously verified diagnostic workspaces, four
new reference bodies, adversarial edits/escapes and bounds. Replaying known bytes
is not a new model evaluation or a new verifier run. The three historical wrapper
rejections are not repaired or rescored here.

## New semantic instance

Four matched shallow/deep × shared/separate snapshots transfer a nonnegative
amount between two finite-map balances. Keys may alias: self-transfer must leave
the entire map unchanged. Otherwise, debit must remain nonnegative, credit must
have the exact value, the two balances must conserve their sum, the key domain
must be unchanged, and every untouched balance must be preserved. The second
immutable client transfers in the opposite direction with its corresponding bound.
This extends the development map family, not a held-out family.

References branch on key equality. Shallow uses Alias or Direct; deep uses Alias
or Debit → Credit → Finish. Source providers and clients are identical in all four
cells. Named exports hide Direct in the deep condition. Shared mode has one editable
proof plus a fixed forwarding wrapper; separate mode has two editable proofs.
Copying equivalent proofs is permitted; delegation is not. Body-count/source-length
and the shared wrapper's import edge remain disclosed workload differences.
Reference path depth is 1 on the alias branch and 1 versus 3 on the distinct-key
branch, not a claim of minimum possible proof depth.

## Map-transfer validation gate

38 completed checks: four reference passes, 32 intended proof failures, and two
explicit hidden-helper name failures. Controls omit alias handling or a credit
prerequisite, invert the branch, use the wrong amount/direction, weaken the helper
contract, and repair only one separate helper. Reference checks round-trip through
the body-only protocol before actual whole-workspace verification. Parse/type
errors do not count as proof failures. Exact fixtures, decisions, stdout/stderr and
source hashes are archived in verification-001; no automatic reruns or model transport exist.

The four map task designs and reference bodies are **verifier validated**. This
does not establish increased model difficulty. The complete revised pilot above
is now frozen as a proposal; model execution requires separate authorization.

## Reviewed map-transfer evidence

Job 56196595 completed on holy8a24101 in 2m23s, exit zero, with requeue disabled
and test partition PreemptMode=OFF checked before submission. No model requests,
credentials, retries or replacement runs were used. `verification-001/` contains
every manifest-pinned source and script plus all 38 raw verifier reports, four
body-payload/assembly decisions, environment metadata and the summary.
`verify-56196595.log/.err`, `submission.json` and `accounting-56196595.txt` preserve
execution details. `results-review.json` and `verification-001-sha256.json` bind
the local audit to the retrieved bytes.

All four references verify through the body-only assembly path. All 32 negative
reasoning controls fail with precondition/postcondition diagnostics, not parse
errors. The two explicitly labeled export controls report unresolved Direct
(and the consequent expected-method-call error). Providers remain identical
across cells; only the intended helper-body/contract mutations occur in controls.
Original model archive hashes and the historical 18/32 calibration score remain
unchanged. The counts are controls for one semantic instance across four structural
variants, not 38 independent tasks or any measured model performance.
