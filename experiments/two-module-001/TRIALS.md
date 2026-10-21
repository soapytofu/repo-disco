# Verifier-only trial log

All checks ran on Cannon with no model API calls. Raw diagnostics and the exact source hashes are linked below.

| Variant | Scope | Outcome | Verified obligations | Errors | Seconds | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | provider | PASS | 1 | 0 | 4.858 | [Result](verification-001/checks/baseline/provider/result.json) |
| baseline | client_only | PASS | 1 | 0 | 3.375 | [Result](verification-001/checks/baseline/client_only/result.json) |
| baseline | whole_repository | PASS | 2 | 0 | 3.606 | [Result](verification-001/checks/baseline/whole_repository/result.json) |
| implementation-bug | provider | VERIFICATION_FAILURE | 0 | 1 | 3.322 | [Result](verification-001/checks/implementation-bug/provider/result.json) |
| implementation-bug | client_only | PASS | 1 | 0 | 2.429 | [Result](verification-001/checks/implementation-bug/client_only/result.json) |
| implementation-bug | whole_repository | VERIFICATION_FAILURE | 1 | 1 | 2.608 | [Result](verification-001/checks/implementation-bug/whole_repository/result.json) |
| weakened-contract-control | provider | PASS | 1 | 0 | 2.499 | [Result](verification-001/checks/weakened-contract-control/provider/result.json) |
| weakened-contract-control | client_only | VERIFICATION_FAILURE | 0 | 2 | 2.709 | [Result](verification-001/checks/weakened-contract-control/client_only/result.json) |
| weakened-contract-control | whole_repository | VERIFICATION_FAILURE | 1 | 2 | 3.866 | [Result](verification-001/checks/weakened-contract-control/whole_repository/result.json) |
| reference-repair | provider | PASS | 1 | 0 | 3.524 | [Result](verification-001/checks/reference-repair/provider/result.json) |
| reference-repair | client_only | PASS | 1 | 0 | 3.644 | [Result](verification-001/checks/reference-repair/client_only/result.json) |
| reference-repair | whole_repository | PASS | 2 | 0 | 4.438 | [Result](verification-001/checks/reference-repair/whole_repository/result.json) |
