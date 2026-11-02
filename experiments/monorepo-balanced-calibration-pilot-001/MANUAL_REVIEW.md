# Completion and proof review — November 2, 2026

Job **57099049** completed on nonpreemptible test in **4m29s**, exit zero.
Exactly 32 reservations, completed responses and unique provider request IDs;
zero SDK retries. All 32 candidates passed the unchanged output guard. Whole
workspaces verified in 29 cases; three had ordinary precondition proof failures.
No output rejection, frontend error, timeout or infrastructure stop occurred.
The full 32-call budget is exhausted. No proof was repaired or rerun.

The 820 retrieved files match their remote inventory, including 813 raw model-run
files. The private handoff is absent after the compute process consumed it.
Scope, runtime, authorization, messages/order, response copies, candidate and
accepted hashes were audited; no integrity issue was found. Every provider,
client, import, lemma contract, attribute and decreases clause outside the allowed
bodies remains byte-identical. Raw stderr is empty.

## Three interval-witness failures

| Trial | Configuration | Saved error | Explanation |
| --- | --- | --- | --- |
| [balanced-09](model-001/balanced-09/verification.json) | Deep/shared, sample 1 | Left precondition `a <= w <= b` | Always chooses c; the assumptions do not imply a <= c. |
| [balanced-20](model-001/balanced-20/verification.json) | Deep/separate, sample 2 | Left precondition fails in both helper bodies | Both branches choose d; the assumptions do not imply d <= b. |
| [balanced-24](model-001/balanced-24/verification.json) | Deep/shared, sample 2 | Same missing lower-bound precondition as balanced-09 | Repeats the unconditional c choice. |

For balanced-09/24, a=2,b=5,c=0,d=4 satisfies all original interval-overlap
preconditions while c=0 is outside [2,5]. For balanced-20, a=0,b=2,c=1,d=3
satisfies those preconditions while d=3 is outside [0,2]. Its branch `a <= d`
is already an assumption and does not supply the missing upper bound. These
arithmetic examples explain the archived diagnostics; they are not repaired
model trials or new verifier runs. Failures remain in the denominator.

## Accepted source inspection

All 32 candidates' protected bytes and 48 editable bodies were checked. The
12 distinct normalized body-syntax forms were manually read against their APIs;
the grouping is syntax only, not repository-scoped proof identity. The accepted
forms use the intended conditional normalization, sequence base/recursive offset
step, map alias/distinct-key contracts and common-witness construction.

The successful deep/separate witness trial (balanced-13) selects a or c based on
their ordering and proves both interval facts for that same witness. It wraps
this in a condition already implied by the task and contains `assert false` in
the unreachable else branch. This is a verified assertion under contradictory
path conditions, not an assumption, axiom, contract weakening or verification
bypass. The accepted shallow witness proof in balanced-28 also contains
redundant branches; each uses the common witness max(a,c).

All **16 separate-condition responses duplicate equivalent body syntax across
HelperA and HelperB**. The two samples of 14/16 task configurations have identical
body syntax. They still have distinct request IDs and fresh contexts; repeated
output is an observation, not evidence of repeated dispatch. It limits diversity
and must not be counted as additional independent problems or reasoning paths.
`inspect_sources.py` reproduces the byte/syntax comparisons in source-review.json.

## Calibration conclusion

Conditional, sequence-offset and map-transfer each scored **8/8**. Interval
witness scored **5/8**: shallow/shared 2/2, shallow/separate 2/2, deep/shared 0/2,
deep/separate 1/2. The observed failures are confined to one developed semantic
instance. Two samples per cell cannot establish a general depth or sharing effect;
separate conditions also require twice as many editable bodies.

The syntax protocol was usable for all 32 samples in this run. This is not a
causal estimate of the prompt revision's effect or a rare-error guarantee; older
18/32, 1/32 and 7/8 scores remain separate and unchanged. No reference solutions
or earlier model responses were provided in these messages.

**Do not launch the 192-call main corpus yet.** Three families reached a ceiling,
and provider interfaces carry much of the mathematics. The useful next work is
non-paid design of more varied obligations requiring additional proof construction,
with matched client semantics and verifier controls, rather than more samples of
the same easy forms. Keep this calibration archive frozen and label any changed
task/protocol separately. Main collection or additional calibration requests need
their own reviewed scope and explicit budget.
