# Verifier control log

No model calls were used for these checks.

| Variant | Scope | Outcome | Expected | Evidence |
| --- | --- | --- | --- | --- |
| reference | provider | PASS | True | [Result](verification-001/checks/reference/provider/result.json) |
| reference | client_only | PASS | True | [Result](verification-001/checks/reference/client_only/result.json) |
| reference | whole_repository | PASS | True | [Result](verification-001/checks/reference/whole_repository/result.json) |
| missing-proof | provider | PASS | True | [Result](verification-001/checks/missing-proof/provider/result.json) |
| missing-proof | client_only | VERIFICATION_FAILURE | True | [Result](verification-001/checks/missing-proof/client_only/result.json) |
| missing-proof | whole_repository | VERIFICATION_FAILURE | True | [Result](verification-001/checks/missing-proof/whole_repository/result.json) |
| assert-only | provider | PASS | True | [Result](verification-001/checks/assert-only/provider/result.json) |
| assert-only | client_only | VERIFICATION_FAILURE | True | [Result](verification-001/checks/assert-only/client_only/result.json) |
| assert-only | whole_repository | VERIFICATION_FAILURE | True | [Result](verification-001/checks/assert-only/whole_repository/result.json) |
| unproved-provider | provider | VERIFICATION_FAILURE | True | [Result](verification-001/checks/unproved-provider/provider/result.json) |
| unproved-provider | client_only | PASS | True | [Result](verification-001/checks/unproved-provider/client_only/result.json) |
| unproved-provider | whole_repository | VERIFICATION_FAILURE | True | [Result](verification-001/checks/unproved-provider/whole_repository/result.json) |
