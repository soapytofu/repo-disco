# repair-001 — Repair the failed extension with Claude

**Status: RUNNING at the last user report on October 20, 2026. Result pending.**

| Field | Record |
| --- | --- |
| Question | Can the repair worker fix the parse error while preserving the intended program and specifications? |
| Parent | [extension-001](../extension-001/README.md) |
| Input program | [Failed extension](../extension-001/extended-program.dfy) |
| Feedback | [Dafny parse error](../extension-001/verifier-output.txt) |
| Configured model / provider | `us.anthropic.claude-sonnet-4-6` / AWS Bedrock, `us-east-1` |
| Configured budget | 1 additional agenda attempt; at most 4,096 output tokens; automatic request retries disabled |
| Worker | `worker.llm_fixer.LLMFixer` |
| Configured timeouts | 15-second connection, 90-second read, 300-second outer process limit |
| Run directory | Timestamped `outputs/claude-repair-…/`; exact path pending |
| Actual calls / token usage / measured cost | Not yet received |
| Verifier result / preservation review | Pending |

The launch instructions copy the original checkpoint to a separate run and set the cumulative attempt limit to the stored count plus one. This record documents the requested run; its artifacts and actual settings still need to be collected from Cannon.

## Evidence to archive after completion

- Exact run directory, source revision, and relevant package versions.
- Resolved run configuration and scheduler log.
- Model prompt/response or diff, and the resulting program if one was produced.
- Verifier stdout/stderr and final task status.
- Token usage if recorded; otherwise explicitly mark it not captured.

## Completion review

1. Did Dafny parse and verify the resulting file? Record the exact counts/errors.
2. Were `Max`'s contracts and the original `TestMax` assertions retained?
3. Were the commutativity lemma and the intended idempotence/associativity checks retained?
4. Were any proof bypasses introduced, such as assumptions or disabled verification?

A verifier pass alone is not sufficient to mark task preservation as confirmed. If the attempt fails, retain the failed artifact and record whether the failure was in the API call, diff application, parsing, or proof verification.

This is a single mixed-model generation → extension → repair sequence, not a controlled OpenAI-versus-Claude comparison.

[All experiments](../README.md).
