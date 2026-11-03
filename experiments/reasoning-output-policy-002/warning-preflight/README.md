# Strict-warning alias diagnostic

November 2, 2026 Eastern. **Completed: 16 verified, zero errors, zero warnings,
exit 0. No model calls.** Job 57178004 ran once on nonpreemptible `test` in 27
seconds; Dafny verification itself took 4.16 seconds. No requeue or retry.

The exact original trial 24 body completed proof verification but exited 2 because
of two missing-trigger warnings in the [earlier diagnostic](../../reasoning-response-diagnostic-001/RESULTS.md).
This new check asks whether ordinary admitted syntax can remove those warnings
without allowing attributes or weakening strict exit-zero acceptance.

The analyst-authored edit replaces 15 occurrences of two concrete map-update
expressions with the already defined and equated `lhs`/`rhs` aliases, from the first
`forall` statement through the final `A.Equal` call. All earlier statements stay
unchanged. No lemma call, assumption, contract, provider definition, or attribute
is added. The other eight repository files remain byte-identical. The v2 guard
reconstructs the new body exactly before the compute verifier runs.

This establishes a strict-verifying formulation for **this one body**. It does not
prove a general trigger-inference rule, give the model credit for the repair, or
change the original v1 rejection. The original pilot remains **18/24**. The
unaltered-body diagnostic still records warning-only exit 2.

- [Exact mutation record](mutation.json), [original body](original-body.json),
  [analyst body](analyst-body.json), [candidate repository](candidate/).
- [Four offline design/import/staging tests](offline-tests.log),
  [pinned runtime manifest](manifest.json), [compute guard decision](guard-decision.json).
- [Full raw verifier record](verification-001/alias-case.json),
  [environment](verification-001/environment.json),
  [Slurm log](verify-57178004.log), [stderr](verify-57178004.err),
  [accounting](accounting-57178004.txt), [submission](submission-warning-alias.json).
- [Reviewed result](review.json), [review code](review.py),
  [raw evidence hashes](verification-001-sha256.json).

The runtime snapshot includes exact inputs, copied v2 policy, pinned verifier
wrapper, preparation/test code and submission script. No credentials or SDKs are
used. Re-run only the offline review, from the repository root:

```bash
python3 -B experiments/reasoning-output-policy-002/warning-preflight/review.py
```

Do not resubmit the recorded job or overwrite its output. Any future semantic
experiment requires a separately identified case and fresh evidence directory.
