# Repository repair choices: prospective development study

**All45 fresh layout/control expectations passed; see [the full results](RESULTS.md).
No prompts are frozen or model requests admitted yet.** The proposed study uses 32
calls within the already authorized 128-call research window; 32 earlier calls
are complete and 96 remain. This is a ceiling, not a commitment to spend without
the validation gates.

The question is whether whole-workspace verifier feedback helps repair when two
proof modules are eligible and the model must decide which bodies to change.
`HelperA.Prove` supplies a fact used by `HelperB.Prove`; two immutable client
lemmas depend on B. Both nonempty bodies are editable and must be returned.
Contracts, imports, exports, providers and clients stay fixed. Both feedback arms
receive the same full failing source and eligible files; only the detailed
diagnostic block versus a failure notice differs.

Four instances are selected before model collection:

| Development instance | Additional obligation | Seeded fault |
| --- | --- | --- |
| Intersection/separation | An exhaustive positive or negative interval certificate | B: touching treated as strict separation |
| Conserved sum and gap | Two bounded values with fixed sum and positive separation | A: invalid lower-endpoint choice |
| Inverse map exchange | Preserve both inverse directions after exchanging values | B: wrong keys in the inverse map |
| Masked override composition | Account for a right override whose value leaves the final domain | A: retaining an overwritten left-domain key |

Each task has four independent responses in each feedback arm: 4 × 2 × 4 = 32.
The proposed four-block order gives every task/arm a mean trial position of 16.5.
It is recorded in [plan.json](plan.json); exact requests and order still require a
later reviewed freeze. The single existing session, model/settings and global
ledger will be reused. There will be no extra client, connectivity request,
automatic retry or reassignment.

Each new layout passed fresh positive/alternative and targeted negative controls,
including repairs confined to A or B. The per-file bounded output policy admits
exact references and rejects contract edits, bypasses, hidden calls and A-to-B
cycles. CSV evidence binds every provider, helper and client obligation; local
client passes conditional on unproved helper contracts do not count as certified
under the declared dependency closure. Empty reconstruction templates and
the known seeded-fault labels remain host metadata and will not appear in the
prompts.

The primary result is strict whole-workspace repair. Secondary reporting covers
local verification, closure under the frozen declared module graph, changed-body
sets, failure category and tokens. Observed helper-call use is reported separately;
the declared graph is not a claim of necessary proof dependence. Text or token changes do not establish semantic necessity or minimum
patch size. The controlled source already gives role information; this is repair
choice within a declared eligible set, not blind or unrestricted fault discovery.

These are four adaptive development instances in two inspected families, not 32
independent tasks or a held-out test. The architecture is fixed: this study does
not estimate a sharing/depth effect. The tree and transition reservations remain
untouched. Existing frozen experiments, scores and the live execution code are
unchanged. The witness, map and protocol subdirectories are being developed
separately; the parent coordinates verification, freeze, budget and publication.
