# Exact-fence sequence extraction diagnostic

Status: **prepared locally; compute verification not submitted or run**. Eight existing sequence responses from [diverse-repair-pilot-001](../diverse-repair-pilot-001/RESULTS.md) failed its conservative whole-response envelope scan before body checking. Each contains one explicit JSON fence. This separate diagnostic extracts that exact substring, retains every JSON-decoded proof-body byte, and applies the unchanged original body guard and failing-base/empty-template adapter. It uses **zero new model calls**, no edited proof steps and no change to the original **16/24** primary result.

All eight exact fenced payloads pass the old body policy. The staged candidates preserve 52 immutable-file comparisons and 12 helper-body boundaries. Whether these exact proofs verify is pending compute-only validation; apparent recursive calls are not counted as proof success. `cases.json` labels strict success as a hypothesis, not a measured result.

The complete 1,204-file primary raw archive was checked against its published manifest before preparation. `parents/` holds 64 byte-exact selected response/result/request/initial-HEAD files; `frozen-001/` is the full unchanged original frozen bundle. `payloads/` preserves the exact JSON-fence contents; `fixtures/` contains only candidates admitted by the old body guard. `provenance.json` pins source commits, original manifests and all parent copies. The preparation neither writes to the original experiment nor creates a new primary score.

`prepare.py` regenerates extraction decisions and exact candidates offline. It requires exactly one explicit `json` fence and rejects duplicate keys, invalid objects and multiple fences. This is a deliberately scoped retrospective diagnostic, **not a replacement general parser or a deployment policy**. Any new parser and future pilot need independent validation/versioning.

`preflight.py` verifies each admitted candidate once on a Slurm compute node, captures exact staged bytes, full stdout/stderr and raw declaration CSV, checks Dafny/Z3 versions, and distinguishes proof, termination, frontend, warning-only and infrastructure failures. `review.py` reproduces extraction and candidate bytes, checks the unchanged original archive, protected scope, complete named-target metrics and diagnostic categories. All failures must be preserved; no automatic retry or proof rewriting.

Parent-run operations (inspect existing local/remote submission state first):

```sh
python3 -B experiments/diverse-repair-extraction-diagnostic-001/ops.py stage
python3 -B experiments/diverse-repair-extraction-diagnostic-001/ops.py preflight
python3 -B experiments/diverse-repair-extraction-diagnostic-001/ops.py submit core
python3 -B experiments/diverse-repair-extraction-diagnostic-001/ops.py status core
python3 -B experiments/diverse-repair-extraction-diagnostic-001/ops.py fetch core
python3 -B experiments/diverse-repair-extraction-diagnostic-001/review.py
```

The SSH helper targets socket 17 and an exclusive new remote directory. Submission requires live `test` partition `PreemptMode=OFF`, successful fake-process tests and unchanged pinned inputs, and writes an exclusive lock before exactly one `sbatch`. It makes no credential or model SDK calls. An ambiguous submission must be investigated, never repeated. Preserve the remote job and all evidence if connection expires. Only the parent agent may invoke remote operations or publish.
