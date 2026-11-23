# Completed-pilot archive transport

This separate package changes only how the completed job's existing archive
program reaches Python over SSH. Job `63153129` has 738 archive members totaling
9,368,273 source bytes. Its frozen fetch program is 141,770 bytes and the quoted
SSH command is 165,832 bytes, exceeding Linux's 131,072-byte single-argument
limit. The exact same generated program is instead sent to `python -B -` on
standard input. Each command-line argument stays below 4 KiB.

`stdin_archive.py` pins the original execution runtime, `ops.py`, canonical
binding and submitted job. It checks all 53 runtime input hashes before use.
Only `estimate` and `fetch` are accepted. Estimate has a 90-second wall cap;
fetch has a 240-second cap; the program has a 2 MiB bound. Existing authenticated
socket 21 and all frozen SSH options are retained. No alternate host, output,
authorization, payload, provider, credential, staging or submission interface is
provided. No native verifier is invoked.

The wrapper calls the **unchanged frozen `ops.fetch()` function**. The original
terminal parent/step accounting, empty matching queue, exact inventory replay,
remote and local exclusive fetch intents, disk checks, safe archive checks and
canonical `execution-001/transfer-001.*` / `retrieved-001/` paths all remain in
force. Its generated program also stays byte-exact; unused function definitions
in that program are inherited from frozen ops, not alternate dispatch routes.
A timeout or other failed transfer leaves the existing intent consumed, with no
automatic retry or recovery path.

Root may run the reviewed final transfer once:

```sh
python3 -B experiments/dafny-real-library-growth-001/archival-001/stdin_archive.py fetch
```

An optional `estimate` action is read-only. The tests intercept every SSH process;
they make no network, Slurm, provider or native-verifier calls. Synthetic archive
files are created only in temporary directories and cannot replace live evidence.
The current source and prior model results are unchanged.
