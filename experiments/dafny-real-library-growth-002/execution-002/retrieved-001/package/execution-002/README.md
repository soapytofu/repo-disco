# Fresh eight-call cohort with candidate frontend continuation

Execution-002 is a new independent cohort. It preserves the four exact payloads
in pilot/frozen-001 and the forward/reverse eight-slot order. No old claim,
response, candidate or ledger is resumed. All prior results remain unchanged.
The same guards, native scorer, source inventories, toolchains, proof-resource
limits, warning policy for acceptance, model settings and one-attempt transport
are retained. Up to eight requests are newly allocated within the 100-call cap:
44 allocated in total, 56 unallocated; the 14 old unused slots stay closed.

The only outcome-policy change is prospective: a fully reviewed parse or
resolution/type failure may remain a failed trial while later independent
trials proceed. It must be a normal exit 2, with complete matching resource
capture, no timeout, no proof rows or proof summary, one counted frontend
summary, and every error and incidental warning located in the editable new
file. Raw stdout/stderr, source, tool and invocation bindings are still checked;
nonempty stderr, protected-file or unlocated errors remain terminal. A frontend
failure never counts as proof coverage or acceptance. Candidate warnings stay
in the logs and do not turn that failed candidate into a success.

Ordinary proof failures and fully captured solver-resource failures retain their
existing treatment. Provider ambiguity, missing/changed evidence, coverage
mismatch, unexpected process outcomes and warning-only/new-warning positives
still stop dispatch. No retry, repair loop, slot reassignment, resumption or
sampling until success is permitted. Each output is independent of all others.

The original renderer is byte-identical and validates its original inert input
metadata, including the old scope. Only execution-002's separate scope/binding,
canonical budget 009 and exclusive allocation claim can dispatch this cohort.
A copied smoke entry imports execution-002; production payloads are unchanged.
Offline tests, saved-evidence replay and manifest-only Cannon preflight precede
fresh hash-bound authorization and one nonpreemptible Slurm submission. Serial
execution allocates one CPU, 4 GB and at most three hours. No model or native
verifier calls are made by the tests or renderer smoke.
