# Per-file pipeline proof-body policy

This development policy is frozen after review of all45 expected compute controls,
18 offline policy tests and three unchanged-runner compatibility tests. It applies
to four fixed-architecture repair tasks. A separate exact prompt freeze and global
budget admission are still required before a new live batch.

Each response contains exactly `HelperA.dfy` and `HelperB.dfy` body strings.
Only the trailing `Prove` body in each file may change. The pinned template
supplies every import, export, signature, contract, attribute and closing brace;
all clients and providers remain byte-exact. The two helper bodies have separate
parameter environments and callable signatures. They are different roles, not
interchangeable copies of one proof.

The only permitted helper call is `H.Prove` from HelperB to HelperA. The policy
does not require that call, a reference call order, or any particular proof.
HelperA cannot call either helper, and HelperB cannot call itself. Immutable
clients import HelperB. Later measurements must distinguish that declared
dependency graph from actual calls in a candidate and from any claim of
necessary or minimal proof dependence.

`POLICY_ID = repository-repair-selection-bodies-v1-development` identifies the
new policy. `VERSION = repair-diversity-bodies-v1-development` is retained solely
for the existing adapter ABI check. Equal VERSION strings do **not** imply equal
policies. Each decision records POLICY_ID, the registry digest, the inherited
syntax digest and the per-file rule digests; a future freeze must pin the new
policy code too.

The following copies remain byte-exact:

| File | Purpose | SHA-256 |
| --- | --- | --- |
| `syntax_guard.py` | Existing bounded AST grammar | `877f898f695ac88b0af1c377d5a1859de544dbb7cc7a1585e6b09d2eecd02fe9` |
| `repair_protocol.py` | Existing failing-parent repair adapter | `00078913c298559740663ae6d870ede56135be6151524d1079834c11fb64c60c` |
| `extract_response.py` | Existing conservative JSON envelope policy | `60446deb6d0ec4bcf9d788a3fd0ea7ba9e7275255769c61e61382513cb77e7de` |

No live handler, earlier policy, experiment, result or frozen input is changed.
The adapter verifies the failing-parent hashes, then reconstructs each candidate
against its pinned empty template; a supplied parent cannot alter protected
source bytes even if its own hash map is internally consistent.

The bounded grammar permits local variables, `if`, `assert`, one-integer-binder
`forall` expressions and proof statements, and registered qualified calls.
Per-file signature checks cover `int`, `bool`, finite integer sets and integer
maps, including map updates/comprehensions, key sets and subset comparisons.
Locals infer one of these types. Imports, new declarations, assignments,
assumptions, reveals, attributes, loops, comments, strings, shadowing and
unregistered/hidden calls are rejected. False assertions and incorrect but
well-formed proofs remain admissible so Dafny can evaluate them.

This is a narrow output policy, not a general Dafny parser or type checker.
The inherited syntax tree does not retain grouping parentheses, so signature
checks treat comparison chains by adjacent operand types. Some parenthesized
comparisons can therefore be admitted and later rejected by Dafny, while other
legal Dafny forms fall outside this policy. Quantifier binders are always integer
keys/values here. Admission makes no claim about preconditions, termination,
triggers, finite-comprehension obligations, truth or whole-repository validity.

`build_registry.py` checks the declared fixture parameter/call types against the
trusted source declarations and named exports. It checks the direct helper and
client import graph and pins exact empty-template boundaries. This construction
script handles the supplied fixture form only; it is not a live mechanism for
admitting arbitrary tasks or source code. It writes only this directory.

The offline test suite exercises per-file scope and types, exact adapter
roundtrips, reference and negative-control source reconstruction, all protected
files, hidden-export rejection, envelope ambiguity and finite limits. A body
admission replay is not another verifier observation. Logical control aliases
are retained as provenance and must not be counted as distinct trials.

Current offline results: all 18 test methods pass. The 45 distinct fixture
workspaces yield 41 exact reconstructions (82 helper bodies) and four intended
hidden-export rejections. These are syntax/scope results, not measured proof
outcomes. The four byte-identical map control aliases are excluded from those
counts. `fixture-replay.json`, `source-inputs.json` and `offline-tests.log` retain
the inputs, decisions and test output. The subsequent policy freeze pins this
complete evidence and code; it does not turn syntax replays into new proof trials.

Three additional offline compatibility tests exercise the unchanged live
handler's `decode` and `prepared` functions with temporary bundles. They cover
all four task controls, exact protected bytes, envelope rejection categories
and internally rehashed parent-contract tampering. Model dispatch, credentials,
verification and promotion are not invoked. Their output is in
`runtime-compatibility-tests.log`; this is not a full future-batch preflight.
The model-visible source/rule inputs have no explicit fault labels, but full
task/plan metadata contains fault-location annotations. A future prompt builder
must use an explicit input allowlist, never serialize those full records, and
independently check that only the feedback block differs between arms.

Run from this directory, with no model, network or Dafny access:

```bash
python3 -B build_registry.py
python3 -B -m unittest -v test_types test_protocol
python3 -B test_protocol.py --write-replay
```

During construction, the first registry build assumed every task declared a
`template_path` and every provider view was named `Public`. Witness tasks instead
use the fixed `templates/<task_id>` path and reviewed named exports such as
`Membership` and `Proof`; the builder now validates those actual exports.
The first combined replay also rejected required set-subset expressions because
the added signature check initially allowed ordering only for integers. That
diagnostic is preserved in `offline-initial-subset-rejection.log`; the prospective
type policy now admits finite-set comparisons, with explicit regression tests.
No source or prior model result was edited to address these development issues.
