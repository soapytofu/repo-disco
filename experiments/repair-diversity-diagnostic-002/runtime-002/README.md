# Diagnostic runtime 002: complete packaging

This is a deliberate packaging revision. The first staged package failed **three of six offline checks before Dafny** because its manifest excluded every file named `README.md`, including `frozen-001/policy/README.md`, which the original prompt/policy freeze requires. No Slurm diagnostic job or model request was submitted by that attempt.

The original package, manifest, operational script and failed test log remain unchanged. Exact copies of the first manifest, stage metadata, operational script, scheduler script and complete failed test log are under `first-package/`. `packaging-provenance.json` records their hashes and the original local inventory.

The corrected manifest includes every frozen dependency, including the nested policy README. Its optional top-level documentation exclusion is matched by exact relative path, never basename. `prepare.py`, `preflight.py`, both reused verifier/measurement modules, all five candidates, payloads, policies and original evidence are unchanged. The only copied source changes are the scheduler's versioned directory/log paths and local original-archive lookup paths in the reviewer/test module.

The five analyst hypotheses and expected results remain: witness trials 03/15 each verify nine obligations, and arithmetic trials 05/09/28 each verify seven, with zero errors or warnings. The primary result remains **27/32**. This version introduces no new candidate proof, model attempt, retry or rescoring.

`validate_packaging.py` creates a temporary directory using **only** manifest entries, checks complete frozen-input coverage, and runs the same six self-contained source/guard/classification tests used on Cannon. It invokes no Dafny, SDK, provider or credentials. The file-only staging check catches the exact omission that the earlier full-directory local tests missed.

```sh
python3 -B validate_packaging.py
```

After the parent reviews and stages this version, `verify.sbatch` targets `outputs/repair-diversity-diagnostic-002/runtime-002`, without requeue. No compute verification has run for these hypotheses yet. The parent owns the one submission and publication of complete raw results. The original first-attempt evidence must remain available.
