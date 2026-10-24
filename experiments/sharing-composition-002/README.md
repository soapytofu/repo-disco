# Harder shared-versus-separate composition tasks (offline)

Status: verifier job **54977065 completed on shared in 3m19s**. All **76/76 controls matched expectations**: 12 successful reference checks and 64 intended proof failures, with no parse/name-resolution errors. All fixture bytes and logged source hashes were reviewed. Five parser tests and three design tests passed. No model calls authorized or made. This is a new experiment. Previous pilot outcomes and extraction diagnostic are unchanged.

## Why these tasks

The previous extracted proofs hit a ceiling (4/4 in each condition). These tasks replace concatenation with opaque numeric transformations and a join lemma with positive-value preconditions. Clients must establish intermediate facts in dependency order, compose them, and discharge a stronger final threshold. Function bodies are hidden behind named export views.

| Tier | Calls per client in reference | Longest reference lemma dependency chain | Joint client calls | Shared composition helpers | Separate composition helpers |
| --- | ---: | ---: | ---: | ---: | ---: |
| diamond | 4 | 3 | 8 | 2 | 4 |
| nested | 6 | 4 | 12 | 2 | 4 |

Diamond uses two Lift instantiations, then Join, then Finish. Nested adds a third Lift and another dependent Join. Client A and B have different argument arrangements and assumptions. Shared clients both use LiftA/JoinA; separate clients use A and B copies respectively. These counts describe reference proofs, not a proven minimum or measured model reasoning effort.

Facts.dfy and ClientA.dfy are identical across conditions. ClientB differs only in its export view and corresponding helper names. Finish and the underlying definitions remain shared in both conditions. This isolates reuse of visible composition-helper identities, not independent repositories or proof invention. Equivalent helper contracts, API visibility, naming and output length remain relevant limitations. Greater structural depth is not yet evidence of greater model difficulty or a benefit from sharing.

## Verification controls

76 completed checks: 12 positive reference checks (whole repository and both clients for each tier/condition), and 64 expected proof failures. Negatives remove each reference step individually, leave the proof empty, call Join before prerequisites, or instantiate Lift on the wrong input. Every negative is checked separately for both clients. Provider definitions and client contracts remain unchanged. Parse/name-resolution errors do not count as successful negative controls. `checks.json` freezes expectations before execution. Verification runs only on compute nodes, with full included-source verification, no automatic retries and no model SDK.

## Tolerant parser v1

`parser.py` accepts one decodable JSON object, with exactly two string-valued client filenames, optionally wrapped in prose or Markdown fences. It rejects multiple decodable objects, duplicate keys, invalid JSON, oversized responses (128 KiB), extra filenames, non-string values and protected-source edits. Extraction offsets record removed wrappers. It never repairs escapes, changes proof statements, evaluates wrappers or executes output.

The original client prefix (imports, signatures, requires/ensures) and closing bytes remain protected. Proof bodies allow only qualified lemma calls with restricted argument tokens; Step and Pair expressions are allowed. This syntactic guard is not a proof checker: malformed-but-guard-accepted calls or unknown lemma names must fail Dafny. Empty bodies can pass the guard and must fail verification. Format acceptance and proof success must be recorded separately.

Five offline parser tests cover wrappers, ambiguous/malformed output, duplicate keys, forbidden edits/injections, all four new reference pairs, and regression against all eight saved responses. Three design tests check matched conditions, protected contracts and unique check IDs. Saved-response regression is development evidence, not held-out parser performance. `parser-freeze.json` records hashes for a future pilot; any later change requires a new version before model requests.

## Proposed next model pilot — not authorized or run

Cross tier (diamond/nested) with condition (shared/separate), using paired repetitions and counterbalanced order. Freeze exact prompts, model configuration, parser version, output cap and call budget before collecting anything. Keep full source and dependency-map policy constant. Use neutral counterbalanced helper names across future instances and hold out independently constructed tasks, because these two instances alone cannot support general claims.

Report format acceptance, guard acceptance, whole-repository verification, per-client verification, partial completion, first failed dependency, token usage and proof-call/dependency metrics. Separately record use of common composition schemas (2 vs 4 unique visible helper identities here); do not label this a proof-reuse benefit without measured outcomes. If both tiers again saturate, add tasks requiring different intermediate facts or helper-proof synthesis rather than repeatedly increasing call count. Do not alter tasks after seeing responses within a frozen batch.
