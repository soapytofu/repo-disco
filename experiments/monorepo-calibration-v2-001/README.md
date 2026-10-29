# Calibration v2 preparation: body-only protocol and alias-aware map transfer

**Zero model calls. Nine offline test methods pass. New Dafny controls are pending
Cannon reconnection; no job has been submitted. This is not a frozen model pilot.**
The original calibration and its 18/32 score remain unchanged.

## Output protocol

`body_protocol.py` accepts a strict JSON object mapping the exact editable helper
filenames to **body contents only** (without surrounding braces or declarations).
A single whole-response JSON fence is allowed. Prose search, duplicate keys,
nested/double-escaped JSON, extra files, and automatic escape/proof repairs are
rejected. The host inserts each body into pinned seed files; all imports,
attributes, contracts, decreases clauses, wrappers, providers and clients remain
byte-identical. Body whitespace is model-owned; file suffix/newlines are host-owned.

`grammar.py` is a separately versioned derivative of the reviewed inline-if
diagnostic grammar. It permits bounded pure conditional expressions as well as
statement branches, assertions and explicitly allowed lemma calls. It forbids
assumptions, reveals, attributes, declarations, loops and cross-helper delegation.
It is an output policy for trusted seed templates, not a general Dafny sandbox.
Dafny still judges semantic validity. Empty proofs are syntactically admissible.

Nine offline tests include byte-exact reconstruction of all 16 original verified
reference workspaces and all 11 previously verified diagnostic workspaces, four
new reference bodies, adversarial edits/escapes and bounds. Replaying known bytes
is not a new model evaluation or a new verifier run. The three historical wrapper
rejections are not repaired or rescored here.

## New semantic instance

Four matched shallow/deep × shared/separate snapshots transfer a nonnegative
amount between two finite-map balances. Keys may alias: self-transfer must leave
the entire map unchanged. Otherwise, debit must remain nonnegative, credit must
have the exact value, the two balances must conserve their sum, the key domain
must be unchanged, and every untouched balance must be preserved. The second
immutable client transfers in the opposite direction with its corresponding bound.
This extends the development map family, not a held-out family.

References branch on key equality. Shallow uses Alias or Direct; deep uses Alias
or Debit → Credit → Finish. Source providers and clients are identical in all four
cells. Named exports hide Direct in the deep condition. Shared mode has one editable
proof plus a fixed forwarding wrapper; separate mode has two editable proofs.
Copying equivalent proofs is permitted; delegation is not. Body-count/source-length
and the shared wrapper's import edge remain disclosed workload differences.
Reference path depth is 1 on the alias branch and 1 versus 3 on the distinct-key
branch, not a claim of minimum possible proof depth.

## Validation gate

38 planned checks: four reference passes, 32 intended proof failures, and two
explicit hidden-helper name failures. Controls omit alias handling or a credit
prerequisite, invert the branch, use the wrong amount/direction, weaken the helper
contract, and repair only one separate helper. Reference checks round-trip through
the body-only protocol before actual whole-workspace verification. Parse/type
errors do not count as proof failures. Exact fixtures, decisions, stdout/stderr and
source hashes will be archived; no automatic reruns or model transport exist.

The four task designs and reference bodies are **not semantically validated yet**.
Even after verifier validation, no claim of increased model difficulty follows.
Only after this gate should the other families be strengthened and a revised
calibration's complete prompts, settings, order and new budget be frozen.
