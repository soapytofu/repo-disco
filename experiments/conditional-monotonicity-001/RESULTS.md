# Conditional monotonicity controls: 32/32 expected outcomes

Job **57180678**, nonpreemptible `test`, completed in **1m27s** on November 2,
2026 Eastern. **Zero model calls; one Dafny invocation per control, no retries.**

| Condition | Reference pass | Intended proof failures | Hidden-export failures | Total matched |
| --- | ---: | ---: | ---: | ---: |
| Shallow/shared | 1 | 6 | 1 | 8/8 |
| Shallow/separate | 1 | 6 | 1 | 8/8 |
| Deep/shared | 1 | 6 | 1 | 8/8 |
| Deep/separate | 1 | 6 | 1 | 8/8 |
| **Total** | **4** | **24** | **4** | **32/32** |

The shallow proofs call the appropriate guarded API for each input. Deep proofs
establish lower/upper facts and assemble the clamp result. All four reference
workspaces strictly verify under fixed client specifications and included-file
verification. Every reference reports 14 verified obligations and zero errors;
these are verifier obligations, not 14 independent tasks.

Empty and one-input-only bodies fail the helper postcondition. Wrong-region and
boundary edits fail provider preconditions. Missing-stage and wrong-upper edits
leave required facts unavailable: shallow cases fail postconditions; deep cases
include assembly precondition failures. Explicit alternate-view calls produce
resolution errors (`Assemble` is hidden in shallow mode; `Below` in deep mode).
Those four name-resolution controls are distinct from the 24 proof failures.
There are no parse-error substitutes for proof failures and no infrastructure
timeouts or warnings in the four reference passes.

All **301 pinned runtime files** match the submitted manifest and the archived
compute copy. Per-control source hashes match the staged bytes and verifier
evidence. The seven provider/client/entry files are identical across conditions;
all helper signatures and contracts stay fixed. Shared HelperB is an immutable
forwarder; separate mode has two equivalent editable bodies. All negative edits
are confined to those allowed bodies.

This validates a new **development** conditional obligation and its selected
controls. It does not demonstrate greater model difficulty, a necessary minimum
proof, independent client synthesis, or a causal sharing effect. The reference
deep structure has two independent prerequisite facts followed by assembly: three
calls but two contract-application stages (one edge between applications). Shallow
has one application stage; both counts exclude the final solver target. No model prompts have
been dispatched or frozen, and no new paid budget is implied.

- [Outcome-by-control review](verification-001-review.json), [review script](review.py).
- [All raw records and exact runtime/fixture bytes](verification-001/),
  [environment](verification-001/environment.json), [summary](verification-001/summary.json).
- [Slurm stdout](verify-57180678.log), [stderr](verify-57180678.err),
  [accounting](accounting-57180678.txt), [submission](submission-monotonicity.json).
- [Runtime manifest](manifest.json), [output hashes](verification-001-sha256.json),
  [transfer inventory](verification-001-transfer.json), [construction tests](offline-tests.log).

Reproduce the offline evidence review without invoking Dafny:

```bash
python3 -B experiments/conditional-monotonicity-001/review.py verification-001
```
