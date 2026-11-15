# Frozen batch handler compatibility

`test_frozen_handler.py` exercises the unchanged `repair-v1` batch handler on
the actual repository-repair-selection proposal freeze
`9a3ac2546edc6c79307826766af3517bdc8d9a8fe629a2ba0239660f4ead778a`.
It creates a temporary complete input bundle and injects fake transport and
verifier functions. Network, subprocess dispatch, credential consumption and
the SDK factory are explicitly blocked. No session/admission or global ledger
is created or altered.

The single test passed in `offline-handler-001.log`. All 32 request payloads and
positions match the frozen plan, with 32 unique fake request IDs and zero
retries. The first block exercises all four task-specific A/B interfaces.
Slots 1–30 reconstruct known reference bodies and receive synthetic successful
verifier evidence; slot 31 returns a forbidden assumption and is rejected before
the verifier; slot 32 returns its unchanged failing parent and receives synthetic
proof-failure evidence. The latter two do not promote a revision. Every supplied
provider and protected source byte is checked, and reopening the completed local
ledger is refused.

`fake-run-001/` retains the handler's local completion summary, ledger/responses,
per-slot decisions, metrics and promotion records, together with an explicit
synthetic compatibility report and hash inventory. Its 30/32 synthetic successful
paths are **not model performance or new Dafny observations**. Runtime, prompts,
policy, source fixtures and prior results remain unchanged. This test covers the
batch handler; the coordinator separately reviews session/global admission.
