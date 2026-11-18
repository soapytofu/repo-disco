# Growth control results

November 18, 2026. These are analyst-authored verifier controls, with zero model
calls. Dafny job **61762615** and Vest job **61762644** are complete. All **23
remaining controls** match their expectations. Together with the two previously
reviewed full references, this qualifies 25 distinct source controls: eight
passing scopes, fourteen intended proof failures and three coverage rejections.

## Dafny-VMC: all 11 remaining expectations matched

| Control group | Cases | Native observation | Harness decision |
| --- | ---: | --- | --- |
| Move reference/alternative and pair alternative | 3 | All required units pass; exit 0 | Qualified scope passes |
| Insufficient move/pair bodies and included failing module | 6 | Intended named unit fails; exit 4 | Reject |
| Unproved move parent with valid pair caller | 1 | MoveToFront fails, PickPair passes; exit 4 | Reject the workspace |
| Omitted failing module | 1 | Native exit 0, 269 units pass; detached obligation absent | Reject incomplete coverage |

Every case retains all **267 passing original units**. Registered stage one has
268 logged units; registered stage two has 269. Including the detached module
produces its actual failed correctness unit alongside 269 passing units. Omitting
that same source removes the required unit, which the harness detects despite
the native command's clean exit. Merely staging and hashing it does not prove it.

The six failed move/pair controls fail the exact ordered-sequence postcondition;
the explicitly registered detached module fails its assertion. There are no
frontend or resource failures. All cases retain exactly the three inherited
warnings; successful controls are not zero-warning successes.

The unproved-parent control is especially useful: the caller proves against the
declared helper contract while the helper itself fails that contract. Whole-scope
acceptance correctly remains false. This is a concrete coverage/control result,
not evidence that every valid solution needs a helper call or two edited files.

The full **192-file transfer** includes native stdout/stderr and CSV, all 20
overlay files across cases, source/tool hashes, resource measurements and
accounting. Offline evidence replay matches all 11 results and preserves the
exact diagnostics. The [source-bound qualification gate](qualification-gate-dafny-vmc-001.json)
records the actual stage-one inventory and complete control evidence. It does
not issue an accepted model revision.

The single-CPU job took **8m34s**; native verification totaled **411.22 seconds**.
Full-job CPU use was **76.95%**, with peak RSS **620,164 KiB**. Each distinct case
ran once under the fixed 100,000-resource/300-second native limits. There were
no retries, requeue or model calls.

Together with the separately completed pair reference, the 12 Dafny source
controls now have reviewed outcomes. The original namespace-cycle failure and
all historical model scores remain unchanged. These reference observations are
not a chronological two-stage model-growth trajectory.

## Vest: all 12 remaining expectations matched

| Control group | Cases | Native observation | Harness decision |
| --- | ---: | --- | --- |
| Frame reference/alternative and batch alternative | 3 | All required timed occurrences succeed; exit 0 | Qualified scope passes |
| Empty/wrong frame or batch proofs | 6 | Intended named proof fails; exit 101 | Reject |
| Unproved frame with valid batch caller | 1 | Frame proof fails, batch proof passes; exit 101 | Reject the workspace |
| Omitted frame or batch module | 2 | Native exit 0, required added targets absent | Reject incomplete coverage |

Every run retains all **5,410 original timed occurrences**, their multiplicities
and successful flags across the qualified `vest_dev`, `vest_lib` and `vstd`
scope. A registered frame has 5,411 occurrences; a registered batch has 5,416.
Omitting the frame leaves 5,410; omitting the batch leaves 5,411. These counts
are timing records, not distinct logical proof obligations. Native verified
summaries remain separate: 5,722 for a passing frame and 5,727 for a passing batch.

The wrong-header proof fails the upstream theorem's `self.consistent(v)`
precondition. Wrong consumed length and zero batch count fail assertions;
empty proofs and missing induction fail postconditions. The unproved-frame
control logs an actual failed frame proof alongside a successful batch proof.
All seven negatives have one failed named proof target, although some emit
multiple diagnostic messages. There are no frontend errors or timeouts.

All runs retain exactly five inherited warnings. Six fixed frame specification
definitions remain source-bound and unlogged, not counted as passing targets;
in the frame-omitted control that source is explicitly unregistered. The
omission controls change only the intended host-owned registration. Neither
staged source hashes nor a successful Cargo exit substitute for required coverage.

The full **205-file transfer** contains 200 verification artifacts, all 30
overlay files, raw JSON/stdout/stderr, source/tool hashes, resources and accounting.
Root and independent read-only reviews checked all transfer hashes, original
source bindings, 36 protected boundaries, 12 registrations, native flags and
diagnostic categories. See the [Vest scope gate](qualification-gate-vest-001.json)
and [evidence replay](review-vest-001.json).

The single-CPU job took **1h58m46s**; native verification totaled **4,716.17
seconds**. Full-job CPU use was **60.83%**, with peak RSS **1,405,424 KiB**.
Each fixed case ran once with one Cargo worker, one Verus thread and a
900-second native cap. No case retried or exceeded that cap.

The [combined control gate](../control-gates-001.json) now permits offline
host integration and prompt preparation. No accepted model parent, live model
handler or model-call authorization exists. Vest additions remain specification/
proof-library growth, not executable parser generation. All prior scores and
failure archives are unchanged.
