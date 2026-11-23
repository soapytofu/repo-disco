# Saved candidate reasoning diagnosis

Read-only analysis of the three returned candidates. Original sources, native results and scores are unchanged. No new model or verifier calls were made. [diagnosis.json](diagnosis.json) records the findings, source lines and 69 inspected file hashes. It checks 15 candidate/native source pairs, all 12 fixed source files displayed across the prompts, exact template/body reconstruction and 12 raw capture artifacts.

| Saved candidate | Actual native result | Interpretation |
| --- | --- | --- |
| StableFilterBelow, slot 01 | 58 passed, 1 failed; exit 4; no warnings | False loop invariant on entry |
| ReadCountedFrames, slot 02 | 81 passed, 0 failed; exit 0; no warnings | Accepted recursive extension using the saved frame function |
| Splice, slot 03 | 10 resolution errors; exit 2; 1 indentation warning; zero proof rows | Accesses a field excluded from the imported API |

These are three observations from a partial cohort, not an eight-response score or evidence of broad model performance.

## Filter: a false annotation, not an established wrong output

The [outer invariant](../../retrieved-001/model-001/slots/slot-01/candidate/growth/StableFilterBelow.dfy#L39) states that the **entire** current array equals the filtered processed prefix. At entry, `i=0`, `n=a.size`, and `original=a.items`, so its right side is `KeepBelow(original[..0], limit) == []`. Every valid nonempty array contradicts this assertion.

For example, let `items=[1]`, `size=capacity=1`, `data=[1]`, the corresponding valid representation, and `limit=2`. The asserted equality is `[1] == []`. Ignoring proof annotations, a manual trace of this particular input takes the keep branch, exits with `[1]`, and returns `removed=0`: the required result. This is a counterexample to the invariant, **not** a wrong-output counterexample or a proof of the whole implementation.

There is another source-level issue at [line 53](../../retrieved-001/model-001/slots/slot-01/candidate/growth/StableFilterBelow.dfy#L53): the inner invariant equates an array of `oldSize` elements with a sequence of `oldSize-1` elements before `PopFast`. It describes completed deletion too early. This is an analytical observation, not a second reported native error. The returned comments at lines 73–82 themselves notice the outer-invariant problem without fixing it.

## Counted frames: verified recursion and exact remainder

The [successful body](../../retrieved-001/model-001/slots/slot-02/candidate/StandardLibrary/src/RepoDiscoFrameBatch.dfy#L45) handles zero count by returning no payloads and the input unchanged, even if that input is malformed as a frame. For positive count it reads one frame, propagates either first-frame or recursive failure, and recursively decodes the remainder with `count-1`. It establishes the requested payload count and length bounds, ordered reconstruction of the original input, and the exact unconsumed suffix. All 81 required units pass, including all 77 inherited units and the four new function/predicate units.

The body has one syntactic call site for the exact saved `F.ReadU16Frame` and one self-recursive call site. It also explicitly executes [`reveal F.ReadU16Frame()`](../../retrieved-001/model-001/slots/slot-02/candidate/StandardLibrary/src/RepoDiscoFrameBatch.dfy#L51). The [saved parent](../../retrieved-001/model-001/slots/slot-02/candidate/StandardLibrary/src/RepoDiscoU16Frame.dfy#L26) is opaque, so this is reuse with access to the parent body, not demonstrated contract-only reasoning. The supplied two-frame function is not called. No claim is made that the reveal or this particular call pattern is necessary.

## Splice: source visibility is not API visibility

The exact [DynamicArray export](../../retrieved-001/model-001/slots/slot-03/candidate/Source/DafnyStandardLibraries/src/Std/DynamicArray.dfy#L5), also displayed unchanged in the prompt, provides `At`, `Put`, `Push`, `PopFast` and the other listed members. It omits the `data` field declared at line 36. The [candidate](../../retrieved-001/model-001/slots/slot-03/candidate/growth/SpliceRange.dfy#L30) nevertheless accesses `a.data` at ten locations: lines 31, 33, 34, 42, 44, 45, 47, 76, 85 and 89. Dafny reports the same hidden-member error at every location. Showing the upstream implementation in the prompt does not make a private member available to an importing module.

The bounded edit guard admitted a replacement body that preserved all fixed bytes; Dafny then performed language/API resolution and rejected it. That separation does not establish a guard defect. The indentation warning at line 41 is separate from the ten resolution errors. The CSV contains only its header, so this outcome says nothing about proof success or runtime correctness. The saved host policy marks this native outcome terminal. The imported saved `AppendAll` method is not called.

These findings motivate studying invariant construction and API-boundary use, but do not establish causal effects of structure or reuse, general cross-project capability, or held-out performance.
