# Named-target completion measurement diagnostic

November 12, 2026. **Completed:** job 60035863 checked four analyst states in
21 seconds; job 60038131 confirmed the logger on the corrected restriction
reference in 14 seconds. Four runtime tests per collector passed locally and
on Cannon; six offline interpretation tests passed. No model calls or original
score changes. [Results and full evidence](RESULTS.md).

This closes a measurement gap before a prospective local-versus-whole-repository
evaluation. The aggregate Dafny `verified` count includes supplied providers and
well-formedness obligations. A supplied client can verify against a helper's
contract even when the helper body fails. Neither number alone measures model
completion of the requested specifications.

Four analyst states of the verified fresh-move task are checked once each with
all included source plus the CSV logger: shared reference, shared empty helper,
separate with only A repaired, and separate with only B repaired. Source and
contracts remain fixed; the partial bodies are exact reference/empty bodies,
replayed through the existing guard. This is a logging/measurement control,
not another calibration sample, agent repair attempt, or observed model gap.

## Measured scopes

- **Local target-lemma completion:** all logged verification obligations for a
  specifically named lemma succeed, under the contracts available to its proof.
  Each lemma's contract is one target unit; individual `ensures` clauses and
  arbitrary assertion batches are not independent tasks.
- **Dependency-closed target completion:** the local target and all declared
  helper dependencies succeed, with the supplied provider obligations verified.
  ClientA depends on HelperA; ClientB depends on HelperB. In shared mode HelperB
  additionally depends on HelperA through its immutable forwarding call.
- **Model-editable target completion:** report only the one shared or two separate
  editable helpers. Supplied clients and providers are excluded from model credit.
- **Whole-workspace completion:** the existing strict exit-zero/no-warning rule
  across all included files still governs acceptance. This diagnostic does not
  replace it or weaken any verification flag.

These scopes and denominators stay separate. Each separate partial state has one
successful editable target out of two while whole completion fails. Both supplied
clients pass locally, but only one has a verified helper dependency. Fixed source
routing defines those edges; they are not inferred from import count or claimed
to be minimum proof dependencies. The states are analyst-authored controls, not
model responses.

The collector adds only `--log-format csv` to the established whole-workspace
verification command. Dafny documents per-declaration/assertion-batch log output
and notes that its format is experimental; the installed 4.11 output was reviewed
against exact declaration inventories. [Official logging documentation](https://dafny.org/v4.11.0/DafnyRef/DafnyRef).
The original frozen verifier/parser pipelines remain unchanged.

`manifest.json` pins the four source snapshots, expected statuses, target graph,
guard, runtime and tests. The one-shot runner preserves stdout/stderr, exit,
source hashes, raw CSV bytes and environment before its temporary directory is
removed. No SDK/provider/client is configured. Missing logs, unexpected exit or
infrastructure failure stops the collector without retry. Real verification runs
only on nonpreemptible compute; `test_design.py` uses a fake process only.

`review_targets.py` interprets saved CSV without running Dafny. It rejects missing,
duplicate, unknown or ambiguously grouped declaration evidence and invalid
dependency graphs. The separately pinned `restriction-001` collector verifies
one unchanged restriction reference, establishing its different 20-row inventory.
The original four-case interpretation is retained in `target-review-001.json`;
`target-review.json` adds that compatibility check without changing earlier
outcomes.
