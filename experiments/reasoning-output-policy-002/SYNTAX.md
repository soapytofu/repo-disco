# Bounded proof-body syntax, version 2

This is the syntax contract for `reasoning-body-json-v2-development`, not a complete
pilot prompt. The host supplies the exact editable filenames, task parameters,
visible lemma calls, pure functions, and their arities. These restrictions are part
of the experimental treatment and must be disclosed in any future comparison.

Return one JSON object mapping **every editable filename** to its complete lemma
body string. No other files, wrapper fields, prose or duplicate keys are allowed.
A single whole-response `json` (or unlabelled) code fence is accepted. Do not include
the outer lemma braces, signature, contracts, attributes, imports, or module.

Allowed statements:

- `var name := expression;` for a fresh local, with no later assignment.
- `assert expression;` without attributes or proof-block annotations.
- `if expression { statements } else { statements }`, including `else if`.
- `forall name | range ensures condition { statements }`, one fresh untyped binder.
- An explicitly allowed qualified lemma call, or the lemma's self-recursive
  `Prove(...)` call, with the declared argument count and a semicolon.

Allowed expressions include bound identifiers, booleans, decimal integers of at
most 12 digits, parentheses, unary `+`, `-`, `!`, and the operators `+`, `-`, `==`,
`!=`, `<`, `<=`, `>`, `>=`, `in`, `!in`, `&&`, `||`, `==>`. Also permitted are
`if ... then ... else ...`, the task's whitelisted pure functions, cardinality
`|...|`, sequence displays/slices/indexes, and `.Keys`.

Version 2 adds these pure forms:

| Form | Example | Restriction |
| --- | --- | --- |
| Primed local identifiers | `var rest' := s[1..];` | `[A-Za-z_][A-Za-z_0-9']*`; no leading quote or non-ASCII letters |
| Set display | `{}`, `{k}`, `{k,j}` | Expressions only; no set comprehension |
| Functional collection update | `m[k := x][j := y]` | One key/value per bracket; no statement mutation |
| Map comprehension | `(map q \| q in m && q != k :: m[q])` | One fresh untyped binder; no explicit key projection or attributes |

The examples show syntax, not complete verified proofs. Dafny checks types,
finiteness, definedness, termination and truth. For example, an admitted functional
update can still be ill-typed, and an admitted recursive call can fail decreases.

Use fresh names distinct from parameters, module aliases, reserved words, and
active locals. A local is unavailable in its own initializer. Blocks and binders
have lexical scope; shadowing is disallowed even where Dafny would permit it.

Not supported: typed/multiple binders, map displays, `imap`, set comprehensions,
multiplication/division, mutable assignments, arbitrary functions or declarations,
`assume`, `reveal`, `expect`, `calc`, loops, attributes including trigger/axiom
attributes, comments, strings, character literals, or contract/file edits.

Bounds are 262,144 UTF-8 bytes per response; 65,536 bytes, 8,192 tokens and 256
statements per body; expression nesting 32, statement nesting 24, and postfix
chain length 32. JSON decoding, exact file-set checking, tokenization, binding,
syntax checking and source reconstruction all precede verification.

All source outside the editable body spans remains byte-identical. In the separate
condition, both helper bodies are editable and may be copied. In the shared
condition, only the designated helper body is editable. No policy change removes
that treatment difference or establishes a causal sharing effect.
