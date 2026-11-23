# Reviewed control gate

`gate.json` binds **30 matching active expectations**: four selected references,
24 matching q002 controls and two new q007 replacements. The controls contain
one alternative proof pass, 21 expected ordinary proof failures and four native
passes correctly rejected for incomplete coverage. These are verifier
qualification results, not model successes.

The two original q002 resource failures and the retired complex splice-reference
resource failure remain unchanged outside the active matrix. No result was
rescored. Filter's byte-identical reference reuse is explicitly recorded.

The four profiles under `profiles/` are new copies. Only their analyst run-ID
and raw-fingerprint exclusion lists change, extending each to 64 entries because
the live runner enforces those profile fields. Proof inventories, commands,
budgets and source scope are unchanged. The original profiles and reference gate
remain immutable; their reference-stage metadata is retained verbatim. The
completed control qualification is recorded in this gate.

`build_gate.py` replays source-bound native reviews before writing exclusive
outputs. Missing or unsuccessful q007 evidence prevents gate construction.
Full build stdout, stderr and source hashes are in `build-001.*`; the gate binds
1,667 exact inputs. Its SHA is
`34977084989b4d14dfa01cdf19bc8e9ab0a2b8479ec3aa00a72933a4e9ee934b`.
This gate does not authorize model execution.
