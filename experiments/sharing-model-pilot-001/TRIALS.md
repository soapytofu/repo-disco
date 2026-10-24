# Eight-call model pilot results

Exactly eight dispatched calls. No retries. All responses rejected at JSON parsing before Dafny verification.

| Sequence | Condition | Repetition | Outcome | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- |
| 1 | shared | 1 | EDIT_REJECTED | 651 | 644 |
| 2 | separate | 1 | EDIT_REJECTED | 651 | 800 |
| 3 | separate | 2 | EDIT_REJECTED | 651 | 701 |
| 4 | shared | 2 | EDIT_REJECTED | 651 | 745 |
| 5 | shared | 3 | EDIT_REJECTED | 651 | 808 |
| 6 | separate | 3 | EDIT_REJECTED | 651 | 743 |
| 7 | separate | 4 | EDIT_REJECTED | 651 | 662 |
| 8 | shared | 4 | EDIT_REJECTED | 651 | 575 |
