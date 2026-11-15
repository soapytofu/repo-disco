The initial offline test invocation had two test-harness errors: it looked for
the unchanged extractor's receipt under `body_policy` rather than `body_guard`,
and attempted to exceed a 128-operation limit using 129 operands (exactly 128
operations). The tests were corrected to use the actual receipt key and 130
operands. These were not verifier findings or source/contract changes. The
passing log records the subsequent invocation.
