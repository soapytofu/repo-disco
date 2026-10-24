# Verification and evidence review

Job 54818785 finished all 46 checks on sapphire. Raw job status: FAILED 1:0; raw matcher 42/46. Offline diagnostic review: **46/46 intended outcomes**. Four expected resolution failures were rejected only because the original matcher expected different wording. No verifier rerun or model calls.

| Variant | Entry | Exit | Raw matched | Reviewed matched |
| --- | --- | --- | --- | --- |
| shared_reference | ClientA.dfy | 0 | True | True |
| shared_reference | ClientB.dfy | 0 | True | True |
| shared_reference | All.dfy | 0 | True | True |
| shared_a_omit_first | ClientA.dfy | 4 | True | True |
| shared_a_omit_second | ClientA.dfy | 4 | True | True |
| shared_a_omit_finish | ClientA.dfy | 4 | True | True |
| shared_a_finish_first | ClientA.dfy | 4 | True | True |
| shared_a_wrong_arguments | ClientA.dfy | 4 | True | True |
| shared_a_hidden_helper | ClientA.dfy | 2 | False | True |
| shared_b_omit_first | ClientB.dfy | 4 | True | True |
| shared_b_omit_second | ClientB.dfy | 4 | True | True |
| shared_b_omit_finish | ClientB.dfy | 4 | True | True |
| shared_b_finish_first | ClientB.dfy | 4 | True | True |
| shared_b_wrong_arguments | ClientB.dfy | 4 | True | True |
| shared_b_hidden_helper | ClientB.dfy | 2 | False | True |
| shared_weaken_ConcatA | ClientA.dfy | 4 | True | True |
| shared_weaken_ConcatA | ClientB.dfy | 4 | True | True |
| shared_weaken_ConcatA | All.dfy | 4 | True | True |
| shared_weaken_ConcatA | Facts.dfy | 0 | True | True |
| shared_weaken_ConcatB | ClientA.dfy | 0 | True | True |
| shared_weaken_ConcatB | ClientB.dfy | 0 | True | True |
| shared_weaken_ConcatB | All.dfy | 0 | True | True |
| shared_weaken_ConcatB | Facts.dfy | 0 | True | True |
| separate_reference | ClientA.dfy | 0 | True | True |
| separate_reference | ClientB.dfy | 0 | True | True |
| separate_reference | All.dfy | 0 | True | True |
| separate_a_omit_first | ClientA.dfy | 4 | True | True |
| separate_a_omit_second | ClientA.dfy | 4 | True | True |
| separate_a_omit_finish | ClientA.dfy | 4 | True | True |
| separate_a_finish_first | ClientA.dfy | 4 | True | True |
| separate_a_wrong_arguments | ClientA.dfy | 4 | True | True |
| separate_a_hidden_helper | ClientA.dfy | 2 | False | True |
| separate_b_omit_first | ClientB.dfy | 4 | True | True |
| separate_b_omit_second | ClientB.dfy | 4 | True | True |
| separate_b_omit_finish | ClientB.dfy | 4 | True | True |
| separate_b_finish_first | ClientB.dfy | 4 | True | True |
| separate_b_wrong_arguments | ClientB.dfy | 4 | True | True |
| separate_b_hidden_helper | ClientB.dfy | 2 | False | True |
| separate_weaken_ConcatA | ClientA.dfy | 4 | True | True |
| separate_weaken_ConcatA | ClientB.dfy | 0 | True | True |
| separate_weaken_ConcatA | All.dfy | 4 | True | True |
| separate_weaken_ConcatA | Facts.dfy | 0 | True | True |
| separate_weaken_ConcatB | ClientA.dfy | 0 | True | True |
| separate_weaken_ConcatB | ClientB.dfy | 4 | True | True |
| separate_weaken_ConcatB | All.dfy | 4 | True | True |
| separate_weaken_ConcatB | Facts.dfy | 0 | True | True |
