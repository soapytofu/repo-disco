# Growth pilot: Bedrock access checks without model calls

Prepared November 23, 2026 for the November 24 meeting. These are read-only
checks of existing records and configuration. No inference request, playground
test, key handoff, cluster reconnect or job submission is needed for them.

The saved run records `AccessDeniedException`, but not its detailed provider
message. The model/profile, region, Python and SDK versions match the earlier
successful real-source repair collection: Claude Opus 4.5 global profile,
`us-east-1`, Python 3.11.17, boto3/botocore 1.43.115. Both runs recorded the same
Cannon host. This rules out a recorded configuration change in those fields;
it does not prove that the key, principal, entitlement or policy was unchanged.
See the [stopped evidence](../experiments/real-repository-growth-001/execution-003/RESULTS.md)
and [earlier collection settings](../experiments/real-repository-repair-pilot-001/execution-001/frozen-001/settings.json).

The exact frozen inference identifier is:

```text
global.anthropic.claude-opus-4-5-20251101-v1:0
```

AWS currently lists this global profile, including source region `us-east-1`,
and the model as Active. Public availability does not establish this account's
access. [AWS model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-4-5.html).

1. **Find the original denial in CloudTrail first.** Sign into the AWS account
   that owns the key, select **US East (N. Virginia), `us-east-1`**, and open
   **CloudTrail → Event history**. Clear the default `Read only = false`
   filter. Set the displayed timezone/time range to **November 23,
   03:04–03:10 UTC** (November 22, **10:04–10:10 PM Eastern**). Search
   **Event name = Converse**. If absent, replace that filter with
   **Event source = bedrock.amazonaws.com** and inspect the same time window.
   Match the model ID above and the actual API event, not an unrelated console
   request. Retain `eventTime`, `eventName`, `errorCode`, `errorMessage` and
   `requestID` if present; the owner can use `userIdentity` to identify the
   principal. Share only the nonsecret error details, with account/user
   identifiers redacted if desired. A missing event is not proof that no
   request reached AWS. Converse is documented as a management event; checking
   existing Event history does not require creating a new paid trail.
   [CloudTrail console filtering](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/view-cloudtrail-events-console.html),
   [Bedrock event logging](https://docs.aws.amazon.com/bedrock/latest/userguide/logging-using-cloudtrail.html).

2. **Identify the key's actual principal and validity.** In **Bedrock → API
   keys**, determine whether the supplied key was short-term or long-term.
   A short-term key inherits its generating principal's permissions, expires
   with that session or after at most 12 hours, and works only in its creation
   Region. Check that it was valid at the failure time and created in
   `us-east-1`. For a long-term key, check status and expiration, then select
   **Manage in IAM Console → Permissions**. Inspect that associated IAM user;
   the permissions of the person currently viewing the console may differ.
   No key value is needed in chat or in a diagnostic report.
   [API key rules](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html),
   [associated IAM user](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-modify.html).

3. **Read model availability and profile metadata.** An account owner with
   permission can run these in **AWS CloudShell in the browser**, using the
   existing console session. They read control-plane metadata and do not call
   the model. The first command intentionally uses the base model ID; the
   second uses the exact frozen global profile. These commands have not been
   executed on this account by RepoDisco.

```bash
aws bedrock get-foundation-model-availability \
  --region us-east-1 \
  --model-id anthropic.claude-opus-4-5-20251101-v1:0 \
  --cli-connect-timeout 10 --cli-read-timeout 30 \
  --output json --no-cli-pager
```

```bash
aws bedrock get-inference-profile \
  --region us-east-1 \
  --inference-profile-identifier global.anthropic.claude-opus-4-5-20251101-v1:0 \
  --query '{id:inferenceProfileId,status:status,arn:inferenceProfileArn,models:models}' \
  --cli-connect-timeout 10 --cli-read-timeout 30 \
  --output json --no-cli-pager
```

The expected availability indicators are `authorizationStatus: AUTHORIZED`,
`entitlementAvailability: AVAILABLE`, `agreementAvailability.status: AVAILABLE`
and `regionAvailability: AVAILABLE`; the profile should report `ACTIVE`.
`PENDING`, `ERROR`, missing entitlement or a denied read warrants owner
investigation. A denied metadata read establishes missing permission for that
read, not a model inference result. A successful read under a console/admin
identity does not prove the separate API-key principal can invoke the profile.
[Availability API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_GetFoundationModelAvailability.html),
[profile command](https://docs.aws.amazon.com/cli/latest/reference/bedrock/get-inference-profile.html).

4. **Have the owner inspect the key principal's effective permissions.** The
   bearer-token path needs `bedrock:CallWithBearerToken`. The nonstreaming
   Converse operation requires `bedrock:InvokeModel`; granting an invented
   `bedrock:Converse` action is not the fix. Check explicit denies, permission
   boundaries, session policies and organization restrictions, as applicable.
   If a source-IP or VPC condition exists, compare it with the original event's
   recorded request context rather than assuming a Mac or login-node address.
   [Converse permissions](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html),
   [bearer-token permissions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_bedrock.html),
   [request-context guidance](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).

The global profile needs authorization for the source-region profile, the
source-region foundation model and the regionless global foundation model.
For this frozen request, the resource patterns to inspect are:

```text
arn:aws:bedrock:us-east-1:<ACCOUNT_ID>:inference-profile/global.anthropic.claude-opus-4-5-20251101-v1:0
arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-opus-4-5-20251101-v1:0
arn:aws:bedrock:::foundation-model/anthropic.claude-opus-4-5-20251101-v1:0
```

Global-model authorization uses `aws:RequestedRegion = unspecified`; a region
restriction can therefore block it despite a `us-east-1` endpoint. These are
inspection targets, not a recommendation to remove organization controls or
grant administrator access. Any policy correction belongs with the account
owner. [AWS global inference policy requirements](https://docs.aws.amazon.com/bedrock/latest/userguide/global-cross-region-inference.html).

5. **Resolve entitlement issues only if the evidence points there.** For Opus
   4.5 on `bedrock-runtime`, the owner should check the Anthropic first-use form,
   model agreement status and Marketplace/payment prerequisites. Existing
   subscription status matters; repeatedly generating keys does not fix a
   missing entitlement. If the detailed denial names an additional account
   restriction or says to contact AWS Sales/Support, escalate that exact
   message. Do not initiate a playground inference to diagnose the problem.
   [AWS model-access guidance](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).

Send back the **key type and creation Region**, the **original nonsecret denial
message/request ID if found**, and the **availability/profile statuses**. Do
not send credentials. These observations will let us choose a specific fix
instead of guessing among authentication, policy and entitlement problems.

The stopped job and ledger stay closed. No new model calls are authorized by
these checks. Before a separately approved collection, the reviewed error
metadata component needs integration into a new bounded runtime so a further
failure retains useful diagnostics. Preserve the frozen prompts and record any
necessary profile change explicitly; no alternate model/profile is substituted
as a troubleshooting shortcut. Read-only checks can narrow the blocker but
cannot guarantee a later invocation succeeds or that collection finishes before
the meeting.
