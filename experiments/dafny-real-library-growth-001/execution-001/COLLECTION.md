# Twelve verified additions on two real Dafny components

Job **63153129** completed November 23, 2026 in **4m27s** on one CPU, with
12 distinct returned requests, zero SDK retries and no ambiguous requests.
All **12 additions passed** their complete declared verification scopes,
forming **six two-stage lineages**. These are model results, separate from the
24 analyst qualification controls and synthetic runner tests.

| Selected upstream component and fixed task chain | First additions | Second additions | Complete lineages | Logged units at stages 1 / 2 |
| --- | ---: | ---: | ---: | ---: |
| Dafny Standard Library: AppendAll → AppendRotated | 3/3 | 3/3 | **3/3** | 58 / 60 |
| AWS MPL UInt component: ReadU16Frame → ReadFramePair | 3/3 | 3/3 | **3/3** | 75 / 77 |

The first four pilot additions all passed. The frozen continuation gate then
released the eight declared expansion slots, which also all passed. Every
response passed JSON extraction and the edit guard. Each new native invocation
had exit 0, complete expected coverage, zero warnings and zero failed units.
All 56 standard-library and 71 AWS upstream units remained passing. Each child
preserved its own accepted parent file byte for byte and received that actual
source in its prompt. There were no blocked children, repairs or retries.

## What the generated code does

The standard-library parent uses the existing dynamic array's `Push` operation
and recursion to append a sequence while preserving validity, contents, size,
capacity and allocation-freshness guarantees. The child composes that new API
twice to append the suffix followed by the prefix and returns the exact appended
interval. The actual accepted child body is:

```dafny
start := a.size;
Append.AppendAll(a, values[pivot..]);
Append.AppendAll(a, values[..pivot]);
end := a.size;
```

[Accepted parent source](retrieved-001/model-001/slots/slot-01/candidate/growth/AppendAll.dfy)
and [accepted child source](retrieved-001/model-001/slots/slot-03/candidate/growth/AppendRotated.dfy).
All three standard-library parent bodies are identical, as are all three child
bodies. These are fresh responses to repeated tasks, not six distinct algorithms.

The AWS parent reads a two-byte length prefix using the existing UInt API,
checks the available bytes, returns the payload and remaining suffix, and uses
the upstream deserialize/serialize lemma to establish exact reconstruction.
Each child calls its own accepted reader twice, preserving both fields and the
final suffix. Each also contains `reveal F.ReadU16Frame();`: two ordinary call
sites plus one definition-unfolding directive. This is observed API reuse with
full source available, not an opaque-contract-only reasoning result. The three
AWS bodies at each stage differ in bytes but implement the same task.

[AWS parent](retrieved-001/model-001/slots/slot-02/candidate/StandardLibrary/src/RepoDiscoU16Frame.dfy)
and [AWS child](retrieved-001/model-001/slots/slot-04/candidate/StandardLibrary/src/RepoDiscoFramePair.dfy).
These are verified executable Dafny method/function-method bodies. The native
commands verify them; this collection does not benchmark generated executables.

## Fixed design and evidence

Claude Opus 4.5 received three complete upstream files, fixed contracts/types
and an empty current body. Second-stage prompts additionally contained the
same-lineage accepted parent. Each stage used one fresh context, temperature 1,
at most 4,096 output tokens, and one SDK attempt. No verifier feedback followed
the response. Upstream code, contracts, imports, registration and parent sources
were protected. Direct child implementations were permitted; API calls were
observed after collection, not required for acceptance.

The 53-file runtime freeze remains
`69d07a07241982e21bf06cf16ed038187c8fd2d2a7fff1e71443515745f49548`.
The final scope remains
`62af62af82abfd8c238a76b1a7f1bc3d20c39b9b71106889444b2fd6acb888bc`.
The [offline collection audit](collection-review-001.json) checks all **738
archived files**, request/response provenance, exact prompts, all 12 guarded
reconstructions and fresh native source sets, full native inventories, resources,
and all six parent–child relationships. [Review code](review_collection.py) and
[full replay logs](reviews/collection-replay-004/) are retained. The independent
[semantic/reuse audit](analysis-001/) records the actual call observations and
their limits. Neither review invokes a model or verifier or changes acceptance.

Three unsuccessful offline audit comparisons are preserved in replay-001 through
003. One compared a claim hash to the runner's pretty-printed authorization copy
rather than the original authorization bytes; the others compared in-memory
native summary tuples with saved JSON arrays, including inside parent audits.
The corrected comparisons bind original bytes and exact canonical JSON. No
runtime, raw evidence, proof result or primary score changed.

The terminal inventory was too large for a single SSH command argument
(165,832 bytes). Before any final fetch attempt, a separate tested
[archive-only stdin transport](../archival-001/) retained the exact frozen
`ops.fetch()` checks and program while changing its transport. All 14 intercepted
transport tests passed. The full archive was then fetched once; no model or
native execution was repeated. Raw CSVs, stdout/stderr, sources, request IDs,
usage, tool fingerprints and [Slurm accounting](retrieved-001/accounting.txt)
are included in [the archive](transfer-001.tar.gz).

## Cost, scope and interpretation

Usage: **99,957 input + 2,780 output = 102,737 tokens**. Native verification
totaled **61.34 seconds** across the 12 candidates (3.79–6.46 seconds each).
The one-CPU Slurm job used 72.279 CPU seconds, with reported peak RSS 182,656 KiB;
the fixed allocation was 4 GB and three hours. Native limits and toolchains were
unchanged from the qualified profiles.

This demonstrates successful contract-guided executable extension and accepted
parent reuse on **two selected three-file components**. There are four fixed
stage tasks with three responses each, not 12 independent task families. The
components share Dafny library ancestry, are author-visible development tasks,
and have small, supplied specifications. A 12/12 result is a feasibility and
calibration result; these tasks do not discriminate harder model/agent behavior.

The broader 102-file AWS baseline failed qualification and remains preserved;
this is not verification of all AWS MPL, encryption-context handling or
cryptographic security. Full-source visibility, revealed definitions and task
selection prevent claims of necessary proof dependence, causal structural
effects, unrestricted repository synthesis or held-out generalization. Earlier
Dafny-VMC failures, Vest successes and repair scores remain unchanged.

This allocation is closed at 12/12 consumed slots. Across the current 100-call
session, 19 requests have returned and 28 slots were allocated; nine unused old
slots remain closed and 72 are unallocated. The [new budget snapshot](../research-budget-20261123-006.json)
preserves the frozen pre-run snapshot. No additional collection was started.
