# Repository verifier integration (development)

The original `LLMFixer` reads one agenda object, edits one string and calls the
single-program backend. That backend stages the string as `program.dfy` in an
otherwise empty temporary directory. This cannot preserve sibling include files.
Its status mapping also uses stdout text; the new API does not change that legacy
behavior or silently replace existing workers.

`language/dafny/repository.py` adds an opt-in integration boundary:

1. `snapshot_agenda_repository` copies an explicit relative-file → agenda-object
   mapping through the existing `get_object` protocol. Missing sources and aliases
   are rejected. Writers must be quiescent: these reads are not a transaction.
2. `verify_repository` stages exact bytes with relative paths, verifies the entry
   **and included files**, and returns the existing `VerificationOutput` together
   with JSON-serializable hashes, command, exit category, stdout/stderr and elapsed
   time. One invocation, no retry, no model. It does not mutate agenda objects or
   enqueue repair tasks. Callers must persist source bytes alongside the report.
3. Exit 0 means success, 4 proof failure, 2 frontend error; timeout, kill and launch
   errors remain distinct. Raw diagnostics are retained for finer interpretation.

Inputs must be trusted or protected by a task's edit guard. Relative-path checks
protect staging writes, but do not sandbox arbitrary Dafny include directives or
code. GNU `timeout` is required, matching the existing Linux execution environment.

## Validation so far

Six offline unittest methods pass. A fake process inspects actual staged nested
files and byte hashes; checks cover agenda reads, missing/aliased sources, path
rejection, process failures, single-attempt behavior and the unchanged legacy
single-program call. **No actual Dafny execution through this API yet.** The next
integration gate is a compute-only check with existing positive and negative
multi-file fixtures. These tests do not reproduce the published baseline and do
not connect repository repair to the paid worker loop.

Run offline checks from the repository root:

```
python3 -m unittest discover -s tests -p test_repository_verification.py -v
```
