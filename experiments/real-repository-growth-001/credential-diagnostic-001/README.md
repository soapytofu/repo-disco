# Offline SDK credential-lifetime diagnostic

The first growth execution stopped with `NoCredentialsError`; no model response
or verifier result exists. This diagnostic isolates the host's authentication
path without contacting a provider or reading real credentials.

[`sdk_probe.py`](sdk_probe.py) ran on Cannon's actual Python 3.11.17 and
boto3/botocore **1.43.115**. It supplies only a hard-coded dummy token and fresh
empty AWS/Boto configuration files, disables metadata credentials, replaces the
HTTP sender with an in-memory boundary and rejects every socket connection.
The actual SDK still selects authentication, prepares/signs the request and
parses the synthetic response. The complete transcript, source hashes and SDK
module hashes are in [cannon-sdk-result-001.json](cannon-sdk-result-001.json).

| Scenario | Result |
| --- | --- |
| Frozen v1 lifetime: token present at client creation, removed before Converse | `NoCredentialsError`, 0 intercepted HTTP sends |
| Proposed wrapper: token scoped across creation and each complete request | 2 synthetic successes; one client and one token load; bearer header present; environment restored between calls |
| Synthetic HTTP failure | 1 intercepted send, no SDK retry; environment restored; wrapper rejects a second invocation |

All three scenarios passed. There were **zero socket connection attempts,
provider requests, model calls, native verifier calls or real credential reads**.
Synthetic request IDs and responses are test fixtures, not model evidence.
The failed real run's ledger is unchanged; these checks do not estimate its
provider billing or retrospectively change its conservative reservation status.

The fix keeps the private token in process memory, exposes it to the SDK only
for the bounded client/request operation and restores the previous environment
on success or failure. The native verifier separately strips provider variables
from child environments. The tested helper hash is
`7f81d5cdd287ec298df5478a4db96aedf4bad23efc0f4941639150cd20e9827d`.
The [execution-002 preparation](../execution-002/README.md) integrates this fix;
it is not permission to restart execution-001 or spend its unused slots.

Reproduction requires an environment with the recorded SDK and the exact
transport/helper files. The script takes `--transport` and `--helper` paths;
it never takes a real key or handoff path. Its successful output binds both input
hashes. The frozen `bounded_requests.py` transport is unchanged; the new wrapper
corrects when the dummy/private token is available to that transport.
