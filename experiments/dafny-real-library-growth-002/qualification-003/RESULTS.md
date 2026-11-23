# Revised Standard Library reference observations

Verifier-only job **63165218** completed in 18 seconds on one CPU. Both revised
sources still fail ordinary proof obligations; neither is a qualified positive.
The full 70-file transfer, source hashes, CSV, stdout/stderr and accounting are
preserved alongside the exact runtime and remote fake-process preflight.

| Reference | Native units passed / failed | Remaining diagnostics | Inherited units |
| --- | --- | --- | --- |
| Stable filter | 58 / 1 | unread-suffix invariant not maintained | all 56 pass |
| Splice | 59 / 1 | loop modifies permission and final concatenation assertion | all 58 pass |

Both native exits are 4, with zero warnings, frontend errors or timeouts.
The source correction broadened explicit read/modify permissions to fit the
supplied exported methods; functional postconditions stayed unchanged. The
remaining failures motivate a separately versioned proof-body correction.
Original fixtures and qualification-001 evidence remain immutable. These are
analyst reference observations, not model attempts or retries of a paid request.

The preliminary inventory review is `reviews/native-stdlib-001.json`; it does
not issue qualified profiles or acceptance. No new model request has occurred.
