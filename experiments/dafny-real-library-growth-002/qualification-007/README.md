# Two replacement controls at the unchanged native policy

This runtime dispatches exactly two new analyst controls from control-revision-001:
splice-retains-old-content and splice-unproved-seed-rebuild. It has no route for
AWS, a selected reference, an already observed control or the retired shifting
splice reference. The original qualification-002 package and evidence are immutable.

The original four-reference gate (18888e38...) is replayed before operations.
A separate binding validates all new fixture bytes and the original two mismatched
control observations, including source/record/raw pins. Those observations remain
RESOURCE_FAILURE rather than ordinary proof failures. The intended final active
gate combines four old references, 24 unchanged matching controls and two new
observations; this does not turn reuse into independent trials or rescore history.
The expanded historical catalog has 33 entries and the intended active matrix 30.

The first new case removes only the proven alternative's clearing loop and must
fail the Splice result contract with AppendAll passing. The second keeps the proven
alternative caller exactly, uses the existing return-only helper mutant, and must
show an actual failing AppendAll plus passing Splice. That helper mutation is not
eligible under the model edit guard, and a passing caller cannot accept the workspace.
All five source files are explicit verifier inputs. New native outcomes are unknown.

Dafny4.11.0, one core, resource limit1,000,000, verifier time300 seconds and outer
cap360 seconds remain fixed. The two-case job uses one CPU,4GB and one hour,
live-confirmed nonpreemptible test, no requeue and no retry. All records, CSV,
stdout/stderr, sources, tools and resources are preserved; outer timeout stops
the remaining case. Native processes exclude provider-related environment entries.
Proof failures require exact coverage/named failures and zero warnings. Source-bound
unlogged definitions never count as verified observations.

Stage, submission and fetch have exclusive intents and bounded stdin transport.
There is no provider/model/key operation. Tests use fake native processes and read
saved evidence; eight fixture construction tests run as part of the combined suite.
Full source/selection/origin diffs and local plus isolated test logs are retained.

Root operates from the experiment directory:

```sh
python3 -B qualification-007/ops.py inspect stdlib
python3 -B qualification-007/ops.py stage stdlib
python3 -B qualification-007/ops.py preflight stdlib
python3 -B qualification-007/ops.py submit stdlib
python3 -B qualification-007/ops.py status stdlib
python3 -B qualification-007/ops.py fetch stdlib
python3 -B qualification-007/review.py stdlib --output qualification-007/reviews/native-stdlib-001.json
```
