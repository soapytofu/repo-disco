# repair-001 — Claude repair of the failed extension

**Model attempt: FAIL — one Dafny parse error. Assisted correction: PASS — 4 verified, 0 errors.** Date: 2026-10-20.

| Field | Record |
| --- | --- |
| Question | Can the repair worker fix the extension while preserving its intended specifications? |
| Parent | [extension-001](../extension-001/README.md) |
| Configured model / provider | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock, `us-east-1` |
| Run ID | `claude-repair-20261020-132111-493558` |
| Budget / observed attempts | 1 additional attempt; cumulative count reached 3 from 2; one model invocation appears in the supplied log |
| Configured output limit | 4,096 tokens; automatic request retries disabled |
| Environment reported before launch | `repodisco`; boto3 1.43.115; langchain-aws 1.9.0 |
| Verifier | Previously established Dafny 4.11.0 / Z3 4.12.1 setup; versions not reprinted in this run |
| Result | `program.dfy(36,1): Error: this symbol not expected in MethodSpec`; 1 parse error |
| Final repair task status | `ATTEMPTED`; scheduler stopped normally at the cumulative attempt limit |
| Token usage / measured cost | Not captured in the supplied log |
| Exact cluster source revision / resolved config | Not yet collected from Cannon |

**What happened:** Claude correctly described the separated `TestMax` body and proposed moving it back. However, both anchor lines in its text diff lacked the closing `@@` required by the patch format. The patch code ignored these malformed lines. Subsequent searches matched repeated braces in the wrong location, removing the opening brace of `TestMaxAlgebra` and leaving a stray block.

**Diagnosis reproduced locally:** applying the saved response to the saved input with the repository's `apply_text_diff` reproduces the logged failed output (ignoring trailing newlines). This is a malformed model edit combined with silent acceptance by the patch code. It is not evidence that the mathematical properties are false.

**Preservation review:** the resulting text retains `Max`'s contracts, `TestMax`'s assertions, the commutativity lemma, and the algebraic checks. No new proof bypass was observed in this text. But the file does not parse, so this is **not a successful verified repair**.

**Statistics caveat:** the log's `total_verified_programs: 1` and 16 verified lines refer to the previously accepted dataset program. They do not mean this repaired extension verified.

## Saved evidence

Extracted from the user-supplied terminal transcript; these are not a direct export of the cluster checkpoint.

- [Input program](input-program.dfy)
- [Model response, including malformed diff](model-response.txt)
- [Failed repair output](failed-repair.dfy)
- [Verifier stdout](verifier-output.txt); verifier stderr was empty in the transcript
- [Scheduler transcript excerpt](scheduler-excerpt.log), with the absolute checkout prefix replaced by `<CHECKOUT>/`
- [Local reproduction script](reproduce-patch.py)

The resolved configuration, full serialized prompt, and cluster checkpoint have not been archived here. The checkpoint remains at `outputs/claude-repair-20261020-132111-493558/agenda.pkl` on Cannon.

## Separate assisted correction — verified

Adding only the two missing closing `@@` markers to the saved diff produces [this candidate](anchor-normalization-candidate.dfy). It restores the intended block arrangement while retaining the original contracts and new checks.

This is a **human/agent-assisted formatting correction**, not Claude's original output and not another model trial. Sophie ran the saved candidate through Dafny on Cannon and reported **4 verified, 0 errors** on October 20, 2026. [Reported verifier output](anchor-normalization-verifier-output.txt).

**Preservation review of the verified candidate:** the `Max` contracts and original `TestMax` assertions remain intact. `MaxCommutative` and the commutativity, idempotence, and associativity checks in `TestMaxAlgebra` are retained. No assumptions or verification-disabling attributes were introduced in the saved candidate. The correction changed only the diff delimiters before reapplying it; no additional model request was made.

**Interpretation:** the proposed structural repair yields a verified program when its edit locations are interpreted correctly. This supports investigating the patch-format boundary; it does not turn the original autonomous attempt into a pass or establish general repair reliability. The original failed checkpoint and its `ATTEMPTED` status remain unchanged by this standalone verifier run.

From the repository root:

```bash
python experiments/repair-001/reproduce-patch.py
dafny verify experiments/repair-001/anchor-normalization-candidate.dfy
```

The first command uses no API and does not modify files. The second runs the local verifier; neither makes a model request. The reported result above is recorded separately from the failed model attempt.

**Next engineering step:** make malformed or unmatched patch anchors explicit errors, with a regression test for this recorded case, before collecting larger-scale edit success rates. That code change has not been made in this documentation commit.

[All experiments](../README.md).
