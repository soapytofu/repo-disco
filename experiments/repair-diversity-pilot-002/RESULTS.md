# Four-instance repair results

**27/32 repairs passed strict whole-workspace verification.** All 32 responses were admitted by the frozen prospective parser and edit guard. The verifier-feedback arm achieved **16/16**, compared with **11/16** for the matched failure-notice arm. These are four selected development instances, not 32 independent tasks or a general feedback-effect estimate.

| Instance | Verifier diagnostics | Failure notice only | Total |
| --- | --- | --- | --- |
| Saturating addition associativity | 4/4 | 1/4 | 5/8 |
| Adjacent-run compression fixed point | 4/4 | 4/4 | 8/8 |
| Exact positive-gap interval pair | 4/4 | 2/4 | 6/8 |
| Restriction of overlapping right-biased override | 4/4 | 4/4 | 8/8 |
| **Total** | **16/16** | **11/16** | **27/32** |

The 16 parent/replicate comparisons contain 11 both-success pairs and five diagnostics-only successes. Responses were independent contexts, not paired random seeds. All five differences occur in arithmetic or witness construction; sequence and map repair are ceiling cases in this sample. The observed aggregate difference is 5/16, or 31.25 percentage points, for this fixed small cohort. It does not establish unseen-family performance or a general causal sharing/depth result.

Shared mode scored 14/16 and separate mode 13/16. Shared mode has one editable body and a protected forwarding helper; separate mode has two equivalent editable bodies. All 16 separate responses used identical bodies in their two helpers. The forwarding dependency, source length and output work differ, so the one-response aggregate difference does not isolate a sharing effect. [The full reviewed report](reviewed-results.json) lists all sixteen structural/feedback cells.

## Failure mechanisms

All five failures were admitted proofs, with no parse, policy, warning-only, timeout or infrastructure failure:

- Trials 05, 09 and 28 retained two unconditional `O.Low` calls before adding a region-based proof. Those calls require their sums to be at most the cap. For example, `c=a=b=d=1` satisfies the task assumptions but violates both initial call preconditions. This is a counterexample to those calls, not to the associativity theorem.
- Trials 03 and 15 retained `u=a; v=u+gap`. The assumptions do not imply `c <= a+gap`. For `a=0,b=2,c=2,d=4,gap=1`, the goal is feasible (use `u=1,v=2`), but that proposed endpoint gives `v=1<c`. Trial 03 explicitly asserted the false bound; trial 15 kept the same ordered body lines with only layout changes and failed the corresponding call precondition.

These conclusions come from the saved candidates and actual Dafny diagnostics. Separately prepared analyst edits are not counted here and must receive their own verifier evidence. The original **27/32** remains the primary score.

## Execution and preservation

The first batch in research session job **60698074** ran on nonpreemptible `sapphire`, with Dafny 4.11.0, Z3 4.12.1 and boto3/botocore 1.43.115. It used **32 unique provider requests, zero SDK retries**, and **113,505 tokens** (88,790 input; 24,715 output; no cache tokens). No connectivity requests were added. The global ledger has used **32 of the authorized 128 requests**; 96 remain available for separately reviewed/frozen work, not an obligation to spend them.

All 27 successes were promoted to new isolated revisions; all five failures retained their starting HEADs. Review checked 208 immutable-file comparisons, 48 protected helper boundaries, exact requests and settings, raw provider responses, both request ledgers, all named provider/helper/client CSV outcomes, accepted revision contents and the durable completion receipt. The initial failing revisions and prior experiments are unchanged.

[model-001](model-001/) contains the full immutable batch archive: frozen inputs, prompts/responses, candidates, both old and accepted revisions, raw verifier CSV, diagnostic streams, runtime and completion receipt. [window-evidence-001](window-evidence-001/) is a timed snapshot of global requests, ledger, queue/events and scheduler logs. [transfer-001.json](transfer-001.json) records all **1,931 transferred files**. The Slurm process was still running at the snapshot because it retains the one in-memory client while waiting for future reviewed batches; this completed model batch is not pending.

The reproducible [offline reviewer](review_results.py) imports only hash-pinned guard/scoring code and makes no model/verifier calls. Its development evidence includes six synthetic-archive tests plus hostname, file-only-archive and edit-label regressions. The transfer intentionally records regular files, so empty directories are not required. Prior reviewer errors and the initial overly broad `reorder_only` annotation are preserved in `reviewer-diagnostics-001/` and `reviewer-diagnostics-002/`; the corrected report labels trial 15 `whitespace_only`. These were offline review corrections, not new model attempts or changed verifier scores.
