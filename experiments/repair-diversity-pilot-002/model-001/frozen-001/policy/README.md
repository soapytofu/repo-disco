# Development repair body policy v1

This is a separate prospective policy for `saturating_assoc`, `compression_fixed_point`, `exact_gap_pair` and `overlap_override_restrict`, each in shared and separate conditions. It admits bounded proof syntax and preserves trusted source bytes; it does not establish proof correctness. No old fixture, policy, result or score is changed. This directory contains no model runner, provider configuration, credentials, verifier invocation or paid execution authorization.

## Scope and source binding

`registry.json` pins the eight exact empty workspaces, helper boundary offsets and prefix/suffix hashes. `body_guard.py` verifies the registry hash, the task identity/environment, the complete source filename/hash set, and the empty helper boundaries before parsing a body. Each response must map exactly `HelperA.dfy` in shared mode, or exactly `HelperA.dfy` and `HelperB.dfy` in separate mode, to strings. The source outside these bodies remains byte-exact, including providers, clients, imports, exports, attributes, signatures, contracts and decreases clauses. The shared forwarding helper remains protected. Unknown task IDs and altered or additional files fail closed.

Bodies are inserted without normalization, whitespace repair, call reordering or semantic edits. Offsets include the opening body newline, so a supplied body is the text between that newline and the protected closing brace. The returned candidate contains all original source files. `repair_protocol.apply_response` also binds the failing parent to caller-provided exact hashes and checks every parent file against the same protected template. The host must freeze those expected parent hashes before a future run; they are not a substitute for a trusted parent selection.

## Bounded grammar

The lexer, operators and bounds come from the frozen diverse-repair v1 grammar (`legacy_body_guard.py`, preserved byte-for-byte). The task environment is additive and fixed in the new registry:

| Instance | Parameters | Lemma calls | Pure functions/predicates |
| --- | --- | --- | --- |
| Saturating addition | `c,a,b,d` | `O.Low/3`, `O.High/3` | `K.Sat/3` |
| Compression fixed point | `s` | `O.Base/1`, `O.TailInvariant/1`, `O.Boundary/1`, `O.Keep/1`, self `Prove/1` | `K.Compress/1`, `K.Clean/1` |
| Exact-gap pair | `a,b,c,d,gap` | `O.Left/3`, `O.Right/3`, `O.Offset/3`, `A.Finish/7` | `K.Left/3`, `K.Right/3`, `K.Offset/3`, `K.Feasible/5` |
| Overlapping override/restriction | `m,n,keep` | `D.OverrideKeys/2`, `D.RestrictKeys/2`, `V.OverrideAt/3`, `V.RestrictAt/3`, `A.Equal/2` | `K.Override/2`, `K.Restrict/2` |

Statements are `if`/`else`, one-name inferred `var name := expression;`, `assert expression;`, allowed lemma calls, and one-binder forall proof blocks of the form `forall q | domain ensures post { statements }`. Local names are lexically scoped. Parameters, module aliases, callable symbols, reserved words and existing locals cannot be rebound or shadowed. A sibling block can independently reuse a local name after the previous scope closes. Arbitrary assignment and delegation between helper modules are not admitted.

Expressions retain the earlier grammar: bound variables; at most twelve-digit nonnegative integer literals and unary `+`, `-`, `!`; booleans; parenthesized expressions; `if ... then ... else ...`; `+`, `-`, comparisons, membership, `&&`, `||`, and implication; sequence/set displays; cardinality; indexing and slices; `.Keys`; functional updates; bounded single-binder map comprehensions; and exact-arity task pure calls. Types, overloaded operators, comparison chains, preconditions and truth are checked by Dafny separately.

The only new expression form is a single-binder universal expression, `forall q :: expression`, optionally with a range: `forall q | domain :: expression`. It is a general scoped syntax rule, added so the maps negative assertion about disjointness is admitted without choosing outcomes based on truth. Nesting is subject to the same expression bound. Explicit binder types, multiple binders, attributes/triggers, existential expressions and arbitrary declarations remain unsupported. All 102 replayed helper bodies not using this new expression form produce identical syntax trees under the prior grammar with the same injected task environment. Compression needs no new syntax.

There are no `assume`, `reveal`, axiom/verification attributes, loops, declarations, comments, strings, arbitrary method calls, hidden export calls or source-level escape mechanisms. This is a narrow proof language, not a general Dafny parser or operating-system sandbox. It can admit false assertions, incorrect precondition usage and nondecreasing recursive calls; the verifier must reject those. It does not privilege reference call order or accept bodies only because they match a reference.

Limits are 262,144 UTF-8 bytes per payload/response; 65,536 bytes, 8,192 tokens and 256 statements per helper body; expression depth 32; postfix-chain length 32; statement depth 24; and the inherited bound of 128 binary operations per expression loop. Invalid UTF-8 surrogate values and unsupported lexical tokens are rejected.

## Separate JSON extraction

`extract_response.py` is an exact copy of the frozen `repair-envelope-v2-explicit-json-001` extractor (SHA-256 `60446deb6d0ec4bcf9d788a3fd0ea7ba9e7275255769c61e61382513cb77e7de`). It accepts a whole strict JSON object or one explicitly JSON-tagged fence under its existing surrounding-text ambiguity rules. Duplicate keys, malformed/wrapped/multiple answers, non-string values, nonstandard constants and oversized payloads are rejected. `body_guard.parse_response` itself accepts strict JSON only. The repair adapter composes the separately pinned extractor and body guard, retaining their separate audit decisions.

## Offline evidence and use

Twenty test methods pass. The replay checks all 678 pinned construction input files and all 78 fixture workspaces. It reconstructs 70 admitted workspaces exactly, including 105 helper bodies; all eight hidden-helper controls are rejected. Allowed workspaces include references, independent alternatives, ordinary mathematical failures and nondecreasing recursive failures. These are syntax and preservation observations, not new verifier outcomes or model trials. `fixture-replay.json` gives case-by-case hashes and decisions; `offline-tests.log` records the adversarial tests. The initial test log is preserved: its sole failure came from a test mutator that tried to replace a nonexistent `module` token in `All.dfy`, leaving the file unchanged. The corrected test actually changes every protected file.

From the repository root:

```sh
python3 -B -m unittest discover -s experiments/repair-diversity-expansion-001/protocol -p test_protocol.py -v
python3 -B experiments/repair-diversity-expansion-001/protocol/test_protocol.py --write-replay
```

A future coordinator must separately pin the parent source, this policy freeze, exact prompts/settings/order and a bounded request runner. For local use, import `repair_protocol.py` and call `apply_response(raw, failing_base, empty_template, task, frozen_parent_hashes)`. It returns a candidate mapping and audit; it writes nothing and invokes no external process. Verification and any promotion remain separate host operations. Shared versus separate still permits copying and differs in output body count/work; guard admission does not remove those treatment limitations.
