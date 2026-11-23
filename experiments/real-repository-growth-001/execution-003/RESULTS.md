# Growth collection stopped on provider access

November 22, 2026, Eastern (November 23 UTC). Job **62950853** ended `FAILED`
after **2m42s**. Its first reserved invocation raised `AccessDeniedException`.
There are **zero returned model responses and zero native verifier invocations**.
Sequential model-generated growth remains unmeasured: this is neither a 0/8
generation score nor a 0/4 lineage score.

| Accounting item | Observed value |
| --- | --- |
| Separately approved ceiling | 8 new requests, no retries or reassignment |
| Durable reservations | 1, slot-01 (`vmc-move`) |
| Reservation status | `AMBIGUOUS_OR_UNSAVED` |
| Completed responses / saved request IDs / token reports | 0 / 0 / 0 |
| Later slots dispatched | 0 |
| Unused capacity, never reassigned | 7 |
| Native verifier calls / candidate artifacts | 0 / 0 |
| Ledger | Closed: `transport_or_response_failure` |

The frozen configuration permits one total SDK attempt, and there was no
host retry, restart or duplicate submission. The failure path did not preserve
provider retry metadata, HTTP status, request ID or billing information. Do not
substitute configured limits for observed provider metadata or infer a server
request count. The conservative reservation remains unscored. An unexpired
authorization does not permit reopening this terminal ledger.

## Submission, resources and preserved evidence

The [fresh human approval](approval-receipt-001.json) explicitly authorized this
separate execution; the older `NoCredentialsError` scope stays closed. Final
read-only checks matched all 4,164 frozen inputs, both native images and 287
Dafny/3,873 Vest tool files, with no matching output, ledger or queued job.
The frozen runner was submitted once to `shared`, then moved **in place** to
live-confirmed nonpreemptible `test` while pending on priority. The same job
kept one CPU, 8 GB, a four-hour limit, no requeue and unchanged code/prompts.
See the [submission receipt](submissions/model.json) and complete
[scheduling record](scheduling-adjustment-001.json).

Accounting reports 9.178 CPU seconds and 50,096 KiB peak batch RSS. No verifier
ran, so these measurements describe the stopped runner, not proof cost. This
was not preemption or exhaustion of the Slurm time limit.

The complete [23-file transfer](transfer-001.json) and
[raw archive](retrieved-001/) contain the request/rendering, runtime/source
bindings, authorization, execution claim, closed ledger, environment, summary,
preflight, stdout/stderr and final accounting. No credential contents are
included. The unchanged [saved-evidence reviewer](stopped-review-001.json)
passes and explicitly reports an incomplete, unscored experiment. The additional
[source audit](source-audit-001.json) matches all transferred sizes/hashes,
authorization copies and the first payload/rendering against the frozen renderer.
No new model or verifier calls were made by either review.

## What the denial establishes—and what is missing

The recorded exception class is `AccessDeniedException`, distinct from the
earlier host-side `NoCredentialsError`. However, the frozen catch path stores
only the exception class. Its final stderr contains the generic stopped-run
error; the original AWS explanation, request ID and HTTP status are absent.
They cannot be recovered from these saved files. This logging limitation is
part of the result and must not be concealed by fabricating error details.

A separate [offline metadata adapter](../provider-error-diagnostic-001/README.md)
now extracts five allowlisted fields from synthetic SDK-shaped error records,
with explicit literal-secret redaction and bounded text. Nine focused tests and
root source/log review pass. It is not integrated into this frozen runner and
cannot recover the missing actual denial details, check permissions or authorize
another request. Any future integration must preserve the original exception
and the request gate's terminal behavior.

The archive does not identify a particular IAM rule, model entitlement, key
expiry, region restriction or billing issue. AWS's
[Bedrock error guidance](https://docs.aws.amazon.com/bedrock/latest/userguide/troubleshooting-api-error-codes.html)
directs access-denial investigation toward permissions and credential validity;
it does not diagnose this specific request.

The next action is an account-owner review of **existing access settings and
available audit records**, without another model test. Relevant identifiers:

- Model/profile: `global.anthropic.claude-opus-4-5-20251101-v1:0`.
- API/region: Bedrock Converse, `us-east-1`.
- Dispatch reservation: November 23 at approximately 03:06:24 UTC
  (November 22, 10:06:24 PM Eastern); job 62950853.
- Only nonsecret denial details are needed; no key should be sent in chat.

All earlier real-source repair scores, task controls, frozen prompts and failed
execution evidence remain unchanged. Offline readiness tests do not prove live
account access, and this failure cannot judge the extender's reasoning quality.
