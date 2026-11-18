# Growth control results

November 18, 2026. These are analyst-authored verifier controls, with zero model
calls. Dafny job **61762615** is complete; Vest job **61762644** is still running.

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
not a chronological two-stage model-growth trajectory. Vest qualification and
actual-parent integration remain pending before any future pilot freeze.
