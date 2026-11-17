# Real-repository repair pilot: Dafny-VMC and Vest

The user has now approved **16 new calls with no retries**. The separately
[prepared execution bundle](execution-001/README.md) passed 17 offline tests
locally and on Cannon; no new model calls have run yet. The frozen proposal
artifacts retain their historical pre-approval state. This pilot tests
one-shot repair at four real upstream sites, using detailed verifier feedback or
a failure notice. The seeds are deliberately damaged verified code, not newly
discovered bugs. Both repositories and all four sites are inspected development
material.

The two projects passed their separate [pinned-toolchain qualification](../real-repository-qualification-001/RESULTS.md),
including native/adapter agreement, omitted-module and unproved-provider controls.
This pilot keeps those proof scopes and trust boundaries. It narrows the earlier
40-call real-repository roadmap to repairs on the two qualified projects;
repository growth, extra projects and extra models are outside this proposal.

## Four tasks

| Task | Fixed upstream site | Induced starting failure (audit only) | Cross-module context |
| --- | --- | --- | --- |
| `vmc-swap` | `FisherYates.Model.Swap` | Sequence-swap expression replaced with the input sequence | Array `Implementation.Trait.Swap` relates its update to the model; the recursive shuffle also uses the model operation. |
| `vmc-small-shuffle` | `FisherYates.Equivalence.ShuffleElseClause` | Proof body removed | Implementation's small-array branch uses the equivalence lemma to relate its result to the monadic model. |
| `vest-roundtrip` | Blanket `SPRoundTrip` implementation in `core/proof.rs` | One serializer-equivalence fact omitted | A generic theorem combines lower-level trait contracts; concrete format clients call it. |
| `vest-pair` | `Pair` implementation of `SPRoundTripDps` in `tuple/proof.rs` | A child theorem instantiated with the wrong buffer | Pair's proof composes child-format contracts with specification definitions in another module; mapped clients use nested Pair values. |

The mutation descriptions above are audit metadata and are excluded from prompt
instructions. Original correct bodies are retained as references and excluded
from each task's own model-visible body. Analogous legitimate repository code is
context, not a pretraining or solution-leakage guarantee. The Pair prompt omits
later analogous Bind proofs in the same file. Two sites in the same component
are not independent repositories or unrelated semantic families.

Upstream revisions are Dafny-VMC
`e3631f8d335bf7ec3648b13976fa2a96a2a5406e` and Vest
`333d61c1f0a2a5accc6962ee9a4ae05619fd0dcc`. The exact source/region hashes are in
[tasks.json](tasks.json); original upstream licenses accompany copied source.

## Protected edits

Each response is one JSON object, `{"replacement": "...body source..."}`. The host
selects the file and replaces exactly one registered body. All bytes before and
after that region, every other source file, contracts, imports, types, signatures,
features, lockfiles and verifier settings remain fixed. The model cannot select
paths, alter a proof scope or add trusted declarations.

[body_guard.py](body_guard.py) enforces balanced source, a bounded lexical policy
and a task-specific callable vocabulary. It rejects boundary escapes, new
declarations, assumptions/admissions, attributes, macros, unknown/recursive
calls, protected-name shadowing, comments, strings and closures. Body limits are
16,384 ASCII bytes, 4,096 lexical tokens and nesting 32. Names of ordinary value
locals can vary; proofs are not matched to an answer string. The output extractor
accepts one JSON object, including a surrounding fence, but rejects duplicate
keys, multiple objects and added fields. The prompt requests plain JSON.

This is a constrained single-body repair interface, not unrestricted Dafny/Rust
editing or a complete language parser. Native verification decides syntax,
typing and mathematics. The supplied callable vocabulary narrows the model's
search, so results measure repair under those supplied APIs. The 11 policy tests reconstruct all four upstream files
byte-exactly, admit the intentionally wrong mathematical candidates and reject
tested policy violations. An empty Dafny function expression is rejected before
verification; the empty shuffle lemma is the actual seed, and both Vest proof
sites also have separate empty-body controls.

## Context, feedback and matching

The two Dafny prompts contain all 28 declared `.dfy` input files, substituting
only the candidate body. Vest supplies exact, curated source for the relevant
trait/specification modules and client usage; its large full repository is not
included. The Pair target file is an explicitly labeled prefix through the first
Pair implementation. [frozen-001/context-manifest.json](frozen-001/context-manifest.json)
records every included file, byte range and hash. These context policies differ,
so aggregate scores are not a controlled Dafny-versus-Verus comparison.

Within each task, source, instructions, output policy, model and settings are
identical between arms. Only one feedback block changes:

- **Diagnostics:** actual saved seed-verification output. Dafny loses only its
  complete temporary CSV destination line. Vest retains all native stderr with
  exact temporary workspace/target paths normalized, plus native crate summaries
  and every failed friendly label; large timing/success inventories are omitted
  from the prompt and remain in the raw archive. No analyst advice is added.
- **Notice:** “Verification of this candidate failed.”

The first and second repeat reverse arm order for each task. Each slot has a new
context and at most one model response. There is no feedback after the response,
sharing of responses between arms, iterative agent loop or best-of-two selection.
The treatment includes the diagnostic content and its extra prompt length; this
small pilot does not separate those effects.

## Proposed budget and evaluation

**4 tasks × 2 arms × 2 fresh responses = 16 new Claude calls.** The proposed model
is `global.anthropic.claude-opus-4-5-20251101-v1:0` through Bedrock Converse in
`us-east-1`, temperature 1.0, maximum 4,096 output tokens per request (65,536 total
output-token ceiling). No availability/API test is part of preparation. Exact
settings, payload sizes, character-based input estimates and the 16-slot order
are frozen with the prompts. No automatic retries, reassignment, alternate
client or recovery after an ambiguous provider result are permitted.

Primary success requires all of the following:

1. Response and edit-policy admission; host reconstruction from the exact seed;
   complete protected-source and build-input integrity.
2. The complete qualified command and pinned toolchain, using a fresh Vest target
   directory and including dependency verification (no `focus` shortcut).
3. Every required named Dafny unit or Verus inventory occurrence present and
   successful, with summaries consistent with the native output. A passing client
   cannot conceal an unproved provider. Unlogged files/definitions stay unlogged.
4. Only the original reviewed warnings: three Dafny trigger diagnostics or five
   Vest root diagnostics. New warnings do not silently become accepted results.

Report zero-warning outcomes separately; neither unmodified baseline is
zero-warning. Report envelope, policy, frontend, proof, coverage/integrity,
warning, timeout and infrastructure failures separately, along with per-target
outcomes, elapsed time, peak RSS, requests, response IDs and token use. Retain
every output, not just successes. Review accepted patches against the fixed
specifications and task intent. An ambiguous transport outcome has no proof
score, and an undispatched slot is not a mathematical failure.

Results will be shown per task and repository, then by feedback arm. The two
responses characterize variability at the same site; the independent task count
remains four, clustered within two repositories. This is a feasibility and failure
analysis pilot, not a held-out benchmark, a causal structural result, a language
comparison, a test of necessary multi-file edits or an open-ended repository
generation study.

## Evidence and execution boundary

[RESULTS.md](RESULTS.md) records the verifier-only controls, exact reference reuse
and preserved setup failure. The initial job stopped before verification because
two locally produced qualification-review files had not been staged remotely.
`runtime-002` bundles those exact files and changes only dependency locations;
task sources, guard and scorers are unchanged. Both submissions and all logs are
retained. The corrected worker checks the six candidates with at most two
simultaneous verifier commands on a nonpreemptible compute partition.

The original `plan.json` and first runtime are historical preparation artifacts.
The final [frozen scope](frozen-001/scope.json), [payloads](frozen-001/payloads),
[order](frozen-001/order.json) and [manifest](frozen-001/manifest.json) govern the
proposal. `review_controls.py` replays raw source-bound observations without
running a verifier. `build_freeze.py` exclusively constructs the proposal only
after that gate; `test_preparation.py` checks exact reconstruction and pairing.

Future execution requires a separately approved 16-call scope and a reviewed
bounded live handler bound to this freeze. No paid runner, authorization file or
credential handoff is created here. The older terminal paid session remains
closed; this proposal cannot reuse or recover its unused slots. No reconnection
or Bedrock key is needed to inspect the saved plan.

## November 17: resource sizing for future execution

Following the user's JDS efficiency notice, future scheduling must use the
workload's actual parallelism. Serial stages and independently scheduled serial
Dafny checks default to one node, one task and one CPU per task. Request more
cores only for explicit concurrent workers or verifier/build threads, and inspect
`jobstats`/Slurm CPU accounting after execution. Slurm allocation alone does not
parallelize a program ([FASRC guidance](https://docs.rc.fas.harvard.edu/kb/job-efficiency-and-optimization-best-practices/#Cores)).

The six existing `runtime-002/verification-001/*/resources.txt` logs show roughly
0.99–1.02 active CPU cores per Dafny command and 1.70–1.98 per Vest command, computed
as `(user_seconds + system_seconds) / elapsed_seconds`. These are command-level
averages, not whole-job Slurm efficiency or peak concurrency measurements. They
do not justify eight cores for a single invocation. Separate serial staging/API
waiting from parallel verification when implementing the future runner, and
avoid concurrent writes to a shared Cargo cache.

The frozen Vest command still uses three verifier threads and four Cargo build
workers; it must not simply be assigned one core as if it were serial. Choose an
allocation consistent with those limits and measured usage, or explicitly version
and qualify any thread/command change. The published historical scripts, source
evidence, prompt freeze and proposed 16-call budget remain unchanged. This note
adds no job submission or model authorization.
