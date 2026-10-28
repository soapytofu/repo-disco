# Contract-guided repository extension preparation

**No model requests authorized or dispatched.** Four proposed independent requests,
one per new client, across two verified seed repositories. This addresses the
remaining initial-generation milestone by adding a genuinely new client module;
it is constrained extension under a supplied interface, not open-ended generation
of specifications or entire repositories. Existing hand-built controls are not
counted as model-generated output.

Seeds are the accepted branch-shared and inductive-shared model revisions from
repository-agent-001/model-001. Two proposed extensions per seed are independent:
branch clients prove absolute-value facts for x+y and x-y-y; sequence clients prove
sum decomposition of s+t+u and t+s+t. Each starts from the same original seed,
not from the other extension. All inspected families remain development data.

The model would return the complete new ClientC.dfy with a fixed import, signature
and contract. Existing files cannot be supplied or changed. The host adds exactly
one include to All.dfy in a separate snapshot, then verifies all included files.
The seed archive never changes. A passing candidate is a verified extension, not
an automatic merge into the original seed. Count modules added, whole-repository
verification success, request/token cost and rejection categories; do not infer
proof minimality, a sharing effect, or generalization from four easy tasks.

The branch grammar is an unchanged copied guard. The sequence grammar permits
only qualified AppendA calls on bounded concatenations of s,t,u. It excludes
assume/assert/reveal/loops/attributes/arbitrary declarations. JSON parsing is
strict with duplicate-key rejection; this intentionally differs from the earlier
tolerant agent parser and is disclosed, not silently substituted there.

Four offline test methods pass: immutable seeds/controlled entry-point change,
references and negative candidates, contract/file tampering, bypasses/duplicate
fields, stale seeds and file collisions. Compute preflight plans fourteen checks:
two unchanged seeds, four references, four empty and four targeted wrong proofs.
Expected: six passes and eight proof failures, no parse/name-resolution failures.
No automatic retries; preserve unexpected outcomes before deliberate revisions.

Only after those controls pass and sources/diagnostics are reviewed will exact
prompts and order be frozen. The current plan is preparatory, not permission to
spend four calls. Reuse no historical budget, and make no connectivity API calls.

Verifier-only job **55810726** submitted once to test (live PreemptMode=OFF),
two CPUs/8GiB/15 minutes, no requeue. Results pending. The manifest pins the
pre-submission README; subsequent status notes are not runtime source changes.

## Reviewed preflight and frozen proposal

Job55810726 completed on test in 44 seconds. All **14 expected outcomes** matched:
six seed/reference passes and eight targeted proof failures, with no parse or
name-resolution failures. Exact staged source hashes, seed immutability, controlled
entry-point changes and diagnostics were reviewed by review_preflight.py. Full
sources and raw verifier logs are retained in verification-001.

frozen-001 now pins four exact prompts in branch-1, branch-2, inductive-1,
inductive-2 order, model/settings, guards, seeds and preflight review. Each is one
independent extension, with no repair retry or unused-call reassignment. Human
reference controls are excluded from model context. The two existing verified
clients are deliberately visible as seed context. This order is a development
collection order, not counterbalanced evidence of a treatment effect.

Still needed before any model dispatch: bounded runner integration and offline
transport tests, separately hash-bound execution authorization, and a private key
handoff. No new API requests have been made or authorized. The proposed request
budget is **four total**, separate from the completed baseline/agent budget.

## Bounded runner ready for separate approval

run_pilot.py now implements the frozen four-trial collection. Ten additional
fake-transport/fake-verifier tests pass, including exact prompt/order/cap, no
restart, ambiguous request stop, ordinary rejection/proof-failure accounting,
verifier timeout/hash-mismatch stop, deadline, per-dispatch freeze checks,
authorization-before-credential access and SDK retry configuration. Tests made
**zero API calls and zero Dafny invocations**. The previously reviewed fourteen
compute controls supply semantic verification evidence.

runtime-freeze.json pins the runner, copied request gate, tests and submission
script separately from the unchanged prompt/guard freeze. Execution requires a
new authorization.json containing explicit user approval, max_calls=4,
automatic_retries=false, reassign_unused=false, both freeze hashes, a recorded
approval basis and a fresh expiry no more than 24 hours away. The active runner
also enforces a 30-minute request window. No authorization file has been created.

The compute-only CLI refuses an existing model-001 output, validates both freezes
before credential access and before every request, consumes a new private handoff
once, and clears its process environment afterward. Source snapshots, actual wire
messages, responses, request IDs, candidate hashes, raw verifier evidence and
accepted-extension records are saved. Existing seed repositories are never
modified. SDK requests have total_max_attempts=1. No Slurm requeue or model retry.
One response per task; four total at most; unused calls cannot be reassigned.

The prepared model.sbatch requests two CPUs/8GiB/20 minutes on test. Reconfirm live
PreemptMode=OFF before submission, inspect output/ledger and any submission record,
and create a unique submission lock. It has **not** been submitted. Expected run
work is a few minutes, but queue delay and provider latency are not guaranteed.
No live runner result or generation milestone is claimed yet.

The same ten fake-only tests also passed in Cannon's repodisco environment.
Runtime files are staged at outputs/repository-extension-001; no authorization
file, model output, submission or private-key access was created by staging.
remote-offline-tests.log preserves that environment check.
