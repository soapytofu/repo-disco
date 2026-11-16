# Verification-harness review, November 16

Status: offline code review and test execution complete; real-repository/native
verifier agreement and coverage checks remain pending. No model or Dafny/Verus
process was invoked in this review. Reviewed code is the unchanged repository
state at 743a78b856910e9d9762e4f16c886a8ae7880996.

## What was checked

The reusable harness stages exact files and invokes Dafny; Dafny is the proof
engine. Task-specific guards and scorers add source and obligation checks.
This review concerns the integration and scoring, not a new proof of soundness
of Dafny, Verus or their solvers.

Using /usr/local/bin/python3.12 (3.12.8):
- 22 existing tests passed across test_repository_verification.py,
  test_repository_candidate.py and test_repository_agent.py.
- 15 tests passed for internal-contract-repair-001/measurement/test_measure.py.
  These include replay of all 18 saved observations, required named helper/client
  outcomes, protected source/receipt/hash checks, warning classification, and
  rejection of missing/duplicate/inconsistent CSV units.
- Those 18 observations are reused evidence, not fresh verifier runs. Synthetic
  verifier records in tests are not mathematical proof evidence.

Logs: [core-tests.log](core-tests.log) and [measurement-tests.log](measurement-tests.log).
The first command resolved python3 to Apple's Python 3.9 and failed while importing
the Python 3.10+ union type syntax. No test assertions ran in that attempt.
[python39-import-failure.log](python39-import-failure.log) preserves it. Selecting
the already installed Python 3.12 resolved the environment problem; source code
was not changed.

Commands (from the repository root, except the second):
```python
import unittest
loader = unittest.TestLoader()
suite = unittest.TestSuite(loader.discover("tests", pattern=name) for name in [
    "test_repository_verification.py",
    "test_repository_candidate.py",
    "test_repository_agent.py",
])
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
```

Run that snippet with /usr/local/bin/python3.12 -B. For measurement:
```sh
cd experiments/internal-contract-repair-001/measurement
/usr/local/bin/python3.12 -B -m unittest -v test_measure
```

## Two concrete boundaries of the generic API

1. language/dafny/repository.py passes only the selected entry to Dafny, with
   --verify-included-files. It hashes and stages every supplied file, but has no
   independent file-reachability or proof-unit coverage gate. A source hash proves
   file identity, not that a proof obligation was checked. The declared dependency
   map in repository_agent.py is context metadata. Existing fixed experiments
   supplied protected include hosts and reviewed scopes; arbitrary real repositories
   need an explicit coverage/acceptance layer.

2. The generic API labels every exit 2 frontend_error. A mocked warning-only exit
   2 is correctly rejected as strict success but receives that coarse label.
   Newer named-outcome scoring distinguishes warnings from parse/resolution/type
   failures. Its fixed-task declaration rules cannot simply be asserted to cover
   unrelated Dafny or Verus projects.

Two one-off fake-process probes characterize these limits (not actual Dafny results):
- Files Entry.dfy and Unreferenced.dfy were staged; Entry.dfy had no include.
  The fake process returned exit zero. The API accepted process success and
  recorded both source hashes, without any independent module/obligation coverage
  evidence. The omitted-module negative still requires a real compute check.
- A fabricated warning-only diagnostic, two verified/zero errors and exit 2,
  produced strict_success=false and coarse category frontend_error.

No frozen wrapper, guard, scorer, prior candidate or score was changed. These
observations do not establish a false acceptance in historical model results.

## Required real-repository acceptance gate

Before paid collection, compare the new adapter against direct native verification
using identical pinned source/toolchain/options/verification scope. Run controls
on compute nodes and preserve both raw outputs.

| Control | Required behavior |
| --- | --- |
| Unmodified upstream scope and reviewed correct patch | Agree with direct verification; all required targets/dependencies covered. |
| Known contract-violating patch or missing required proof | Reject if the fixed specification is violated/unproved; diagnose inadequate specs separately. |
| Client local pass while helper correctness fails | Never count as complete-scope success. |
| Deliberately omitted failing module / focused consumer-only check | Coverage gate rejects or explicitly narrows the claim; never a full-scope pass. |
| New admission, axiom, external body, disabled verification or weakened contract | Edit policy rejects; unchanged upstream trusted boundaries remain disclosed. |
| Warning-only, parse/type/resolution error, timeout, killed or launch-error result | Distinct categories; incomplete runs receive no proof success. |
| Missing, duplicated, inconsistent or stale result/source evidence | Fail the acceptance audit; never turn missing evidence into a pass. |

Expected proof-unit coverage is toolchain- and task-specific. Definitions that
legitimately emit no verification unit must be documented as unlogged, not
silently counted as passes. Do not require synthetic units that the native tool
does not emit. Required executable/proof targets cannot use this exception.

Acceptance means zero wrapper/direct-result disagreements and zero false
acceptances on the reviewed control set, not a universal error-rate guarantee.
Review any false rejection with the direct result, configured strict-warning
policy and required target scope. Preserve each mismatch before versioned fixes.

Measure runtime and resource use too: baseline and candidate verification wall time,
harness overhead, timeouts and peak memory where available. Keep cold/cached scope
and machine settings explicit. These local unit-test timings do not benchmark
Dafny/Verus or support a speed claim. Do not repeat expensive unchanged verification
merely to inflate sample counts.
