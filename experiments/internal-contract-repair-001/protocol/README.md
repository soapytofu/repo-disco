# Fixed-interface method-body policy

This is the separate `internal-contract-method-bodies-v1-development` policy for
the two `*-dual_fault` development tasks. It is not the older lemma-repair
adapter ABI, a model prompt freeze, a paid runner, or a verification result.

The host supplies the exact four-file seed workspace and task metadata. The
registry binds `All.dfy`, `Kernel.dfy`, the **new fixed** `Helper.Transfer` header,
and the unchanged public `Client.Target` header. Only the two registered method
body byte spans may change. The response is exactly a flat JSON object with
string values for `Helper.dfy` and `Client.dfy`. The existing faulty bodies are
templates; no extra empty workspace is created. File membership, imports,
module/method names, parameters, return types, attributes, preconditions and
postconditions remain exact. No candidate can edit the metadata or providers.

## Grammar and roles

The new policy reuses the hash-pinned lexical, expression and type-checking
implementation under `inherited/` without modifying those copies. It adds a
method statement layer and integer-map display expressions. Its accepted
statement grammar is:

```text
statement := output-or-local := rhs ;
           | var fresh-local := rhs ;
           | assert boolean-expression ;
           | if boolean-expression { statement* }
               [else { statement* } | else if ...]
rhs       := expression
           | registered-returning-method(expression, ...)
```

`Helper.dfy` has no allowed method calls. `Client.dfy` may call `H.Transfer`,
whose ordered argument types and single return type are matched to the fixed
helper signature. A returning method call must occupy the complete right-hand
side of one assignment or local initializer; nested calls, discarded results,
multi-result assignments, recursion and arbitrary calls are rejected. Its
precondition remains Dafny's obligation.

Expressions admit integer and Boolean literals; variables; `+`, `-`, `!`;
parentheses; comparisons and Boolean connectives; conditional expressions;
registered `K.Endpoint`, or `K.Erase`/`K.Entry`/`K.Exclude`, according to the task;
finite integer-set displays and set `+`/`-`; `.Keys`, integer-key lookup,
functional map update and cardinality; `map[]` and
`map[key := value, ...]`; `map x | condition :: value`; and one-int-binder
`forall x [| condition] :: proposition` expressions. Quantifier nesting is
allowed within the same finite parser bounds. Standalone forall proof
statements, sequences, multiplication and typed local declarations are outside
this policy.

Inputs are read-only. Return variables are assignable. A local is introduced
with an inferred permitted type and may be reassigned only that type. Fresh
local and binder names must start with a lower-case ASCII letter; they may not
shadow any active parameter, output, local, binder, keyword or module alias.
Branch-local names stay in their lexical branch. Permitted types are `int`,
`bool`, `map<int,int>` and `set<int>`, with the exact per-file role/signature
environments recorded in `registry.json`.

The grammar rejects assumptions, axioms, verification attributes, reveals,
early returns, loops, declarations, comments, strings, mutable field/index
assignment and code outside those productions. It does **not** prescribe a
reference call sequence or require use of `H.Transfer`. The transparent Kernel
functions can implement a client directly; that is admitted and recorded.
Syntactic call counts describe source occurrences, not executed calls or proof
dependence.

## Bounds and semantic limits

- Response: 262,144 UTF-8 bytes; each body: 65,536 bytes.
- Each body: 8,192 tokens and 256 statements.
- Expression nesting: 32; statement nesting: 24; postfix chain: 32.
- At most 128 operators at one precedence-parser level, 32 map-display entries,
  and 12 digits per integer literal.

The policy checks syntax and narrow type roles. Dafny must still establish
definite assignment, finite-map well-formedness, membership requirements,
function/method preconditions, full language typing and all postconditions.
Empty bodies, false assertions and type-compatible mathematical mistakes are
admitted. As in the inherited parser, grouping parentheses are not retained in
comparison-chain ASTs; some invalid grouping can pass this coarse type check
and then be rejected by Dafny. None of these limitations permits changing a
protected byte or adding an unregistered operation.

## API and evidence

`body_guard.parse_response(strict_json, seed_sources, task)` returns full
candidate sources and a receipt, or raises `ValueError`. The receipt binds the
new policy ID, actual guard code hash, pinned registry and inherited parser
hashes, exact parent/candidate file hashes, body hashes/boundaries, per-file rule
hashes, ASTs and syntactic method/pure-call inventories. It never certifies a
proof. A consumer must pin the policy manifest/code and replay or validate the
receipt against actual sources; an arbitrary acceptance Boolean is insufficient.

`extract_response.py` is a byte-exact copy of the reviewed
`repair-envelope-v2-explicit-json-001` extractor. It remains a separate layer
for a whole-response JSON object or one unambiguous explicit JSON fence. It
does not rewrite body strings. Its combined receipt has `envelope` and
`body_guard` fields. No live handler has been modified to use this new policy.

The standalone runtime needs only `body_guard.py`, `registry.json`,
`inherited/typed_guard.py`, `inherited/syntax_guard.py`, and optionally the
extractor, plus host-supplied task metadata and exact seed sources. It does not
read the original fixture repository during parsing. `build_registry.py` and
the tests are offline host tools; their source inputs are pinned separately.

## Offline validation

Run `python3 test_body_guard.py` from any working directory. Fifteen methods
cover exact registry/ancestor pins, isolated import, sixteen byte-exact eligible
workspace replays, the separate envelope, scope protection, type roles,
shadowing, bypass attempts and finite bounds. The sixteen workspaces are two
new seeds plus fourteen existing **new-header** parent controls: four positive
reference/alternative workspaces and ten existing negative workspaces. These
replays are not new verifier observations. Four parent workspaces retaining the
old Helper header are explicitly rejected as current candidates.

`test-inputs.json` pins all source inputs used by tests; `replay-001.json` records
the exact eligible source hashes and decisions. The new seeds' verifier status
is owned by the separate fixture study. `DEVELOPMENT-NOTES.md` records two
corrected initial test-harness assumptions. No model, Dafny, remote command or
credential access was performed to implement this policy.
