# Output compatibility for the four varied calibration tasks

Eight offline test methods passed; **zero model or verifier calls**. This adds
only four task registries to a separate copy of the existing bounded body parser.
An AST comparison excludes the version and registry and requires the remaining
grammar to match the previously published v4 policy exactly. The tolerant
single-JSON envelope extractor is byte-identical to its published version.
No historical policy or result is changed.

- All 110 current reference/semantic-negative sources reconstruct byte for byte
  through the JSON envelope and body parser. This includes proof and termination
  failures: syntactic admission is distinct from semantic success.
- All 16 hidden-export attempts are rejected by the allowed-call registry.
- Immutable dependencies, clients, imports, contracts, induction attributes,
  decreases clauses and the shared forwarding helper are protected by pinned
  seed hashes and exact insertion boundaries.
- Bypass statements, alias/parameter shadowing, wrong arities, cross-helper calls,
  conflicting/duplicate/malformed JSON and resource-limit violations are tested.
  Only prefix splitting admits self-recursion; Dafny must prove termination.

The exact per-task parameters, pure expressions and statement-call arities are
in body_guard.py:policy. Output is one JSON object mapping the exact editable
filenames to body strings. Surrounding prose or a JSON fence is permitted only
when the conservative extractor finds one unambiguous complete object. Proof
bodies are not rewritten. Bounded locals, conditionals, assertions, quantified
proof statements and sequence/map expressions use the existing grammar. No
assumptions, reveals, new declarations or verification-bypass attributes.

Trusted task metadata and exact seed hashes are required. This is a syntax/scope
policy, not a sandbox or mathematical verifier. Whole-repository Dafny verification
remains required. The 110 replays are not independent new verifier observations,
and the 16 references are analyst-authored, not model responses. No prompt order,
model settings, runner or paid authorization is frozen here.

Reproduce from the repository root:

```bash
python3 -B experiments/varied-calibration-001/protocol/test_policy.py
```

The replay audit records every exact source hash. The registry freeze also binds
the current task/check list and seed manifest; future fixture edits require a new
compatibility review.
