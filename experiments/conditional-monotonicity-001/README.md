# Guarded clamp monotonicity — development candidate

November 2, 2026 Eastern. **All 32 verifier outcomes matched: four reference
successes, 24 proof failures, four hidden-export resolution failures. No model
calls or model prompts.** Job 57180678 ran once on live-confirmed nonpreemptible
`test` in 1m27s, two CPUs/8 GB, without requeue or retry. Five offline
construction/import/fake-process tests passed. Exact sources, protected contracts,
raw diagnostics and runtime hashes were reviewed; [full results](RESULTS.md).

## Concrete reasoning obligation

For `x <= y` and `l <= h`, prove `Clamp(x,l,h) <= Clamp(y,l,h)` using opaque
clamp/lower/upper functions and visible provider contracts. Two immutable clients
consume the result as an ordering and a nonnegative difference. Providers and
client specifications are identical across all four shallow/deep × shared/separate
workspaces. This is cross-module reasoning inside each monorepo snapshot.

Earlier clamp instances could be solved with two or three unconditional API
observations. This candidate instead exposes **guarded** below/within/above
observations. The reference selects the appropriate preconditions for each of the
two inputs, then the arithmetic solver discharges monotonicity. It does not prove
that explicit branches or this particular proof are the only solutions, or that
a model will find the task harder.

Shallow references use one applicable API observation per input. Deep references
combine one lower fact and one upper fact, then call `Assemble`: **three calls per
selected branch, but two contract-application stages** (one application-to-application
edge), because the lower and upper facts can be established independently before
assembly. The shallow reference has one application stage. These counts exclude
the final solver-discharged target and are not minimality claims. Do not call this
a three-stage dependency chain by counting statements. The two branch tests per input
are shared by the reference implementations in both conditions.

## Matched conditions and controls

Shared mode edits HelperA; immutable HelperB forwards to it. Separate mode edits
both equivalent helpers, and reference bodies are copied. Source/edit workload
therefore differs; common provider definitions exist in both modes. This is not
an equal-work causal sharing experiment. Clients A and B are two target lemmas,
not independent semantic instances or repeated trials.

The fixed 32-check set produced four reference successes, 24 ordinary proof failures,
and four explicit hidden-export resolution failures:

| Control per cell | Intended failure mechanism |
| --- | --- |
| Empty body | Monotonicity remains unproved |
| Observe only the first input | No relation for the second clamp result |
| Select `Above` in the below branch | Provider precondition fails |
| Use `x <= l` for strict-below selection | Equality boundary violates provider precondition |
| Omit the within observation / lower stage | Required intermediate fact is missing |
| Use the wrong upper-bound parameter | Fact refers to a different clamp/upper expression |
| Call API from the hidden alternate export | Explicit resolution failure, not a proof failure |

All mutations stay within the editable proof bodies. Contracts, providers, entry
point and client bytes remain fixed. No parse error was counted as a negative
proof control. Full source and all intended-failure evidence are retained.

## Evidence and remaining gates

[Tasks](tasks.json), [checks](checks.json), [deterministic builder](build.py),
[offline tests](offline-tests.log), [runtime manifest](manifest.json),
[submission](submission-monotonicity.json), [compute script](verify-monotonicity.sbatch).
The [32-case review](verification-001-review.json) links each declared outcome;
[full evidence](verification-001/) includes every exact source file and diagnostic.

This semantic instance is development data derived from inspected clamp work.
It is not held out. A separate [registry extension](protocol/README.md) now admits
these API names on the unchanged v2 grammar, with 25 offline test methods and exact
replay of prior compute evidence. The original six-instance v2 parser is untouched.
Exact model prompts/settings/order still need a coherent future freeze. No paid
budget is requested or inferred by building the fixtures. Existing pilots and
their scores remain intact.
