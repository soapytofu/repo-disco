# Growth execution stopped before an evaluable response

November 22, 2026, Eastern. Job **62928981** ended `FAILED` after **2m57s**.
The first reserved transport call raised `NoCredentialsError`. There are **zero
returned model responses, zero native verifier invocations and no accepted
model revision**. This is not a 0/8 generation score or a 0/4 lineage score.

| Accounting item | Observed value |
| --- | ---: |
| Frozen maximum | 8 requests |
| Durable reservations | 1, slot-01 |
| Completed responses / request IDs / token reports | 0 / 0 / 0 |
| Reservation status | `AMBIGUOUS_OR_UNSAVED` |
| Later slots dispatched | 0 |
| Unused capacity, never reassigned | 7 |
| Native invocations | 0 |
| Automatic retries / duplicate submissions | 0 / 0 |

The ledger is closed with `transport_or_response_failure`. The original
reservation and conservative status are preserved, even though the separately
reproduced SDK path fails before HTTP dispatch. That reproduction is not a
measurement of provider billing or a fabricated receipt for this actual run.
No complete-pilot correctness score or token total is inferred from absent
responses. The stopped authorization/ledger must not be restarted or reused.

## Scheduling and full evidence

The job was submitted once to `shared`. While pending on priority, a live check
showed `test` UP, `PreemptMode=OFF` and a 12-hour maximum. One in-place partition
change started the same job immediately with its unchanged one CPU, 8 GB,
four-hour limit, command, request cap, `Requeue=0` and `Restarts=0`.
The failure is a credential-loading error, not preemption, proof failure or a
wall/resource timeout. Accounting reports 9.422 CPU seconds and 36,432 KiB peak
batch RSS; no verifier ran.

[The 23-file transfer](transfer-001.json) preserves the entire stopped evidence
set: request, rendering, source/runtime bindings, closed ledger, authorization,
claim, SDK environment, summary, raw stdout/stderr, preflight and scheduler
accounting. Full bytes are in [retrieved-001](retrieved-001/). The in-place
scheduling record is separately retained in [scheduling-adjustment-001.json](scheduling-adjustment-001.json).
No credential contents are present.

The frozen reviewer first encountered an archive-layout bug: a files-only
transfer omits an empty `accepted-heads` directory, which it unconditionally
iterated. That failed review is saved in [stopped-review-001.json](stopped-review-001.json).
The [second review](stopped-review-002.json) copies the archived files to a
temporary directory and restores only that empty directory, then runs the
**unchanged frozen reviewer**. No file or acceptance record is added, changed or
removed; all original archive hashes remain unchanged. The review passes and
explicitly records an incomplete experiment, one unscored reservation and zero
completed responses. A future reviewer handles this empty-directory case
separately; the original reviewer and failure remain preserved.

## Credential failure diagnosis

The runner consumed the private handoff, constructed the SDK client, and removed
`AWS_BEARER_TOKEN_BEDROCK` before calling `client.converse`. The installed SDK
also consults the environment when preparing the request. Removing the token
at that point switches the request away from the intended bearer authentication
and reproduces `NoCredentialsError`.

The [separate offline SDK diagnostic](../credential-diagnostic-001/README.md)
uses the exact installed boto3/botocore 1.43.115, a dummy token, empty credential
configuration files and an in-memory HTTP boundary. Socket connections are
forbidden. It reproduces the old failure before any fake HTTP send, then checks
the proposed scoped-token fix across two calls and a terminal error. All three
scenarios pass with **zero network attempts, provider requests or native calls**.

This is an execution integration defect, not evidence that the model cannot
extend these repositories or that the user's supplied key was invalid. The
next runtime is separately versioned and requires reviewed tests and an explicit
new execution decision. The prompts, task controls and prior model scores are
unchanged. Unused capacity in this terminal scope is not reassigned.
