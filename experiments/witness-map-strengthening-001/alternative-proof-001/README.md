# Alternative proof strategies through the new output policy

**Eight strict successes, zero model calls.** Verifier job 58532292 completed on non-preemptible `test` in 28 seconds. All eight workspaces passed with exit zero and no warnings. The interval variants each verified 10 obligations; the map variants each verified 16. Obligation counts are not independent research tasks.

These analyst-authored alternatives use exactly the original seed contracts and protected bytes:

- Interval witnesses are chosen from the smaller **upper** endpoint (`v = min(b,d)`, `u = v - gap`), instead of the original lower-endpoint construction.
- Map proofs split on the queried key (`q == j`) and reverse the key-comparison syntax, instead of the original top-level `k == j` pointwise branch. The shallow variant reorders independent observations.

Each candidate was supplied as a JSON object inside prose and a Markdown fence, passed through the pinned tolerant envelope and task registry, and verified without editing the extracted proof text. `responses/` stores raw synthetic responses and extraction decisions; `seeds/` and `fixtures/` store the exact before/after source. This shows that the protocol admits these different valid strategies, not general parser completeness or measured model performance.

Two offline test methods passed locally and remotely. The initial local test assumed a newline after the opening helper brace, but the frozen guard's insertion span places the body immediately after that brace. `offline-tests-initial.log` preserves this test-harness failure. The test was corrected to read explicit pinned seed bytes; neither generated proof bytes nor the parser changed. No failed compute run or automatic retry occurred.

[Exact review](verification-001-review.json) · [Full source and verifier archive](verification-001/) · [Source inventory](verification-001-sha256.json) · [Scheduler accounting](accounting-58532292.txt). The 64 original controls and all historical model results remain unchanged.
