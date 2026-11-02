# Six-task reasoning calibration: frozen 24-call proposal

Prepared November 2, 2026. **No model calls made; execution is not authorized.**
This is the next Weeks 5–6 difficulty/format calibration before larger monorepo
corpus collection. Earlier experiments and their scores remain unchanged.

**Recommended budget: 24 new Claude requests** = six semantic instances ×
shallow/deep × shared/separate × one sample. This is the smallest complete
four-cell pass over all six instances. It gives eight requests per family and
six per structural cell, with no retries, repair feedback or slot reassignment.
It can identify obvious floor/ceiling and output-policy problems; one sample per
variant cannot estimate sampling variability or establish a sharing/depth effect.

| Family | Semantic instance | Four configurations | Proposed calls |
|---|---|---|---:|
| Conditional | Nested clamp | Shallow/deep × shared/separate | 4 |
| Conditional | Clamp stability | Shallow/deep × shared/separate | 4 |
| Sequence | Reverse over concatenation | Shallow/deep × shared/separate | 4 |
| Sequence | Nested filtering | Shallow/deep × shared/separate | 4 |
| Maps | Commuting updates | Shallow/deep × shared/separate | 4 |
| Maps | Delete after update | Shallow/deep × shared/separate | 4 |
| **Total** | **6 instances, 24 variants** | **1 fresh context per variant** | **24** |

The [prior source validation](../monorepo-reasoning-expansion-001/RESULTS.md)
already covers all 164 intended outcomes: 24 reference passes, 120 ordinary proof
failures, eight termination failures and 12 hidden-export resolution failures.
Only final `revision-003` fixtures enter this proposal. Earlier failed references
and runtime evidence remain preserved. This preparation performs an offline
source/evidence audit, not another semantic run.

## Frozen inputs and order

- [Scope and acceptance rules](frozen-001/scope.json)
- [Exact 24-trial order](frozen-001/trials.json) and [balance guarantees/limits](frozen-001/order-design.json)
- [System instruction](frozen-001/system.txt), [bounded syntax instructions](frozen-001/syntax-instructions.txt), and [all task requests](frozen-001/tasks)
- [Model/verifier settings](frozen-001/settings.json), [unchanged guarded parser](frozen-001/guard/body_guard.py), and [source/evidence audit](frozen-001/evidence-review.json)
- [SHA-256 inventory of 306 frozen files](frozen-001/freeze.json)

Freeze SHA-256: `56dc93326ba4ebaa7ba6d5787207665c3ed89f81cf2f5703362b2815640d0afc`.
Source commit: `a58400dc7278dfa77aa3b61cab4307bbc271a742`.

There are four waves, each visiting all six instances once, with rotating instance
order. Every instance visits all four cells. At each depth, shared comes before
separate for three instances and after it for three. Three instances encounter
shallow first and three deep first; first shared/separate exposure also splits
3/3. Each cell occupies each within-instance wave position once or twice. This
does not balance every adjacent transition or exact global dispatch position.
Every request starts a fresh conversation.

The only provider input is each trial's exact `request.json`: system instruction,
user prompt, model ID and inference configuration. Each prompt contains all nine
empty-seed workspace files, a source-derived include/import map, allowed call
signatures and syntax examples. Fixed provider implementations and the shared
forwarding helper are legitimate context. Reference helper bodies, negative
controls, measured outcomes and reviewer proof-path metadata are excluded.
Reviewer-only `tasks.json` retains the original task metadata unchanged, including
its historical `future_protocol_required` flag; it is never sent as model context.

The parser permits a deliberately bounded language including braced branches,
inferred locals, recursive self-calls, assertions and pointwise `forall` proof
blocks. Responses must map exactly the editable filenames to body strings.
The guard keeps its original development version label but its exact bytes are
frozen here. It protects contracts, imports, providers, clients and decreases
clauses; its admission alone is not verification. Prior parsers are untouched.

## Proposed execution and measurement

Inference settings match the preceding balanced calibration:
`global.anthropic.claude-opus-4-5-20251101-v1:0` through Bedrock in `us-east-1`,
temperature 1.0, at most 4,096 output tokens per request. The aggregate output
ceiling is **98,304 tokens**, plus input tokens. This is a token ceiling, not a
cost estimate; no pricing, availability or connectivity requests were made.
Reference bodies total 121–1,520 UTF-8 bytes per response across these variants;
that is a workload audit, not a model-token prediction.

Success requires guarded edits and strict whole-workspace Dafny exit zero,
including all providers and clients, using pinned Dafny 4.11.0 and a 60-second
verification timeout. Report planned, reserved, dispatched, returned, admitted
and verified counts separately. Record per-instance four-cell outcomes, family
counts, tokens, latency and separate-body copying. Distinguish JSON/schema/guard
or truncation rejection, frontend failures, proof/termination failures and
infrastructure failures. Inspect every accepted proof and every failure.

Ordinary rejected or incorrect responses consume their trial; no retries or
feedback repairs. Transport ambiguity, hash/persistence failure, verifier
timeout/killing/launch failure or interrupted dispatch stops the run without
automatic recovery or replacement. A future bounded runner must make one SDK
attempt per durable reservation and enforce the approved cap/deadline at every
dispatch. There is **no live runner, authorization, key access or job submission**
in this preparation. Execution requires separate approval of 24 new calls and a
tested, hash-bound runtime; historical unused call slots cannot be reassigned.

Any output-policy failure requires offline review before scaling. A task at
4/4 or 0/4, a family at 8/8 or 0/8, near-ceiling results or repeated proof templates
trigger difficulty review. No silent extraction repairs or retrospective score
changes. No automatic repeat round or main-corpus collection follows this pilot.

All six instances are inspected development tasks, not held-out data or generated
repositories. Shared exposes one editable helper body; separate exposes two and
permits copied proofs. Primitive definitions remain shared in both conditions.
Source/imports and output workload therefore differ; this is not an equal-work
causal sharing comparison. Depth denotes the designed reference fact path, not
proved minimum proof depth. Model difficulty is still unmeasured.

## Offline validation and reproduction

**12 tests passed** ([full log](offline-tests.log)). They check all 24 exact
reference reconstructions, 104 unchanged semantic-negative reconstructions,
reference/control input isolation, protected sources, grammar examples and
rejections, counterbalance claims, input/settings hashes, no-overwrite behavior,
tamper detection and byte-identical regeneration. All 164 existing source/log
links were audited; no Dafny or model requests were needed.

From the repository root, this command uses temporary directories and no network:

```sh
python3 -B experiments/monorepo-reasoning-calibration-001/test_plan.py
```

`prepare.py` refuses to overwrite `frozen-001`; tests reproduce it in temporary
directories and verify the same freeze hash. Run the repository script, not the
provenance copy in `frozen-001/preparation`. Before any future dispatch, pin the
outer freeze hash and validate its complete inventory. The [preparation manifest](manifest.json)
also pins the plan, scripts, test log and freeze hash.
