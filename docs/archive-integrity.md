# Checking archived experiment integrity

Use this read-only command from the repository root:

```sh
python3 scripts/audit_archive.py experiments/composition-pilot-001/manifest-sha256.json --require-complete
```

The auditor checks every recorded SHA-256 digest, rejects path traversal and symlink entries, and reports missing or changed files. It separately lists files not covered by the manifest (excluding the manifest itself and Python caches). `--require-complete` makes unlisted files a failure as well. Exit status is zero only when the requested checks pass. It never regenerates hashes to make a changed archive pass.

On October 23, 2026, all **399 files** in the published composition-pilot-001 manifest matched, with no uncovered files. This check ran after retrieving the completed 12-call pilot. The source/prompt/contract review and scientific outcomes remain recorded separately in that experiment's preservation review and summary.

Hashes establish consistency with a manifest, not independent authenticity or correctness of the experiment. Commit the manifest and evidence together; use Git history to review intentional later changes. A future edit to a summary may legitimately require a new digest, but first inspect and explain the edit rather than silently refreshing all hashes. Preserve raw failed and successful run evidence.

Test the auditor with `python3 tests/test_archive_audit.py`. Three tests cover valid files, changed and missing files, incomplete coverage, traversal, malformed digests, symlinks, and invalid manifest shapes. No model calls or Dafny execution are involved.
