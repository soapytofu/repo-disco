# Certificate-order diagnostic: confirmed

November 12, 2026. Verifier-only job **60066865** completed on nonpreemptible
`test` in **24 seconds**. **All four expected outcomes matched. Zero model calls,
retries or requeue.**

| Saved response / analyst case | Source change | Dafny result |
| --- | --- | --- |
| 04: originally policy-rejected | None | 19 verified, one certificate-precondition error |
| 04: analyst reordered | Move existing certificate call after both restriction-key facts | 20 verified, zero errors/warnings |
| 08: separate helpers | Same move in each existing helper body | 20 verified, zero errors/warnings |
| 09: shared helper | Same move in its existing body | 20 verified, zero errors/warnings |

Every repaired case has strict exit zero. The unchanged response 04 has exit 4
with exactly one proof failure in HelperA at the restricted-map certificate call;
it has no parse errors or warnings. Its two `ensures` clauses are valid for
Dafny, although they remain outside the original bounded output grammar.

## What the diagnosis establishes

The required ordering is to expose both restricted key sets before calling
the certificate whose precondition requires their disjointness:

```dafny
O2.RestrictKeys(m, keep);
O2.RestrictKeys(n, keep);
O1.Certify(K.Restrict(m, keep), K.Restrict(n, keep));
```

All three model responses had the needed key-fact calls later in their proof.
Moving the certificate after those calls is sufficient for the full workspace
to verify. No new lemma call, assertion, precondition, postcondition or definition
was added. The separate response required the same line movement in both copied
bodies.

This is concrete evidence of a prerequisite-ordering failure across module
contracts. It differs from the earlier missing-value-fact diagnosis: here the
needed fact-producing calls were present, but came too late. It does not establish
minimal repairs, necessary mathematical proof depth, a general causal
sharing/depth effect or improved model performance.

Response 04 had **two distinct issues**: the frozen guard rejected its repeated
`ensures` syntax; the unchanged proof also fails the certificate precondition
when examined in this separate trusted analyst diagnostic. Its repaired version
still fails the original guard, despite verifying in Dafny. No parser or prompt
was silently changed, and no original rejection was reclassified.

The original interrupted pilot therefore remains **six strict passes, two proof
failures and one policy rejection among nine returned responses**, plus one
service-error dispatch and six undispatched slots. These analyst successes are
not additional model successes.

## Fidelity and reproducibility

Review checked all four exact source snapshots, expected diagnostic categories,
CSV contents, immutable providers/clients, signatures, contracts, imports and
exports. Statement multisets are unchanged for the reordered bodies; only the
identified call moves. Both `ensures` clauses stay in the actual response-04
Dafny input. The syntax-review projection described in the README is neither the
compiled source nor an automatic model-output repair.

All **646 files** in the original model archive remain byte-identical. Copied
response/task/extraction records match their original parents. All **120 transferred
diagnostic files** match their transfer hashes. The unchanged responses 08/09
were not rerun; their original failure evidence is already archived. Four offline
tests passed locally and on Cannon before a single compute submission.

- [Reviewed results](results-review.json), reproduced by `python3 -B review.py`
  without model or verifier execution.
- [Full source, stdout/stderr and CSV archive](verification-001/).
- [Transfer hashes](transfer-core.json), [archive hashes](verification-001-sha256.json),
  [accounting](accounting-60066865.txt) and job stdout/stderr are retained here.
- [Original model results](../map-development-pilot-001/RESULTS.md) remain separate.

This diagnostic is complete. Any later output-policy change or resumed/new
model collection needs its own explicit protocol and scope; no unused calls
were reassigned.
