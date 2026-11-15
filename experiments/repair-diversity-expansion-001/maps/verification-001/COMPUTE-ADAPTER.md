# Additive compute adapter

The original construction files, source fixtures, manifests, cases and logs are
preserved byte for byte and inventoried in `adapter-preservation-001.json`.
The adapter interprets their diagnostic expectations without changing them.

`fixture-manifest.json` is a flat hash inventory compatible with the parent's
`compute_ops.py`. `runtime-manifest.json` pins the construction code, verifier,
test entry points, scheduler script and documentation. `verify.py` checks both
inventories and the original preservation inventory before launching any process,
then creates one fresh `verification-001` directory. It refuses login-node or
non-Slurm execution. Dafny and Z3 versions must exactly match the established
4.11.0 commit and Z3 4.12.1. The known `dafny` command and solver environment are
unchanged; resolved executable paths and version output are recorded.

Every case is attempted once on the compute node. Strict success requires exit
zero, a unique verifier summary, at least one verified obligation, and no errors
or warnings. Ordinary proof failures require exit four and an error-bearing
verifier summary; parse/type/name errors and termination failures are distinct.
The expected assertion, precondition or postcondition must appear in an actual
error diagnostic. Unexpected outcomes retain their original categories and all
raw evidence. Timeout or process-launch failure stops the batch without retry.

Evidence contains exact fixture and runtime snapshots, stdout/stderr bytes,
CSV bytes (including CRLF), hashes, execution times and a cumulative summary.
No credentials, provider SDKs, requests or model code are involved. `verify.sbatch`
is a prepared compute script only; the parent coordinator owns staging,
live partition checks and submission.

Offline entry: `python3 -B test_structure.py`. It delegates the original five
design tests and adds diagnostic, manifest and fake-process byte-staging tests.
