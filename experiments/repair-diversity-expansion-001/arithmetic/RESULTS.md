# Saturating-addition control results

Verifier-only job **60695852** completed on nonpreemptible `test` in **42 seconds**. All **18 expected outcomes** matched: four reference/alternative successes, twelve proof failures and two hidden-export resolution failures. Positive workspaces verify seven obligations with no errors or warnings. No model calls were used.

The primary faulty proof calls the unsaturated-addition contract without establishing its intermediate-sum preconditions. Both corrected case analyses verify. Omitting prerequisite facts and using wrong saturation boundaries produces proof failures; trying the hidden `Range` helper produces resolution errors, reported separately. These are analyst-constructed development controls, not model successes or a minimum-depth result.

The offline review checked exact submitted sources, all named lemma verification units, successful provider/client obligations, 99 protected-file comparisons and 27 helper-body boundaries. Shared mode has one editable body; separate mode has two copyable bodies, so work/output-size differences remain.

Evidence: [review](results-review.json), [complete source and raw verifier/CSV archive](verification-001/), [archive hashes](verification-001-sha256.json), [submission](submission-001.json), [accounting](accounting-60695852.txt), [stdout](verify-60695852.log), [stderr](verify-60695852.err), and [transfer inventory](transfer-001.json). Initial fixture metadata remains unchanged as the pre-verification design record. The reusable reviewer is [../review_verification.py](../review_verification.py).
