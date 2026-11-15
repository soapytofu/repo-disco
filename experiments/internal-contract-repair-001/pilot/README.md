# Internal-contract repair prompt freeze

This prospective pilot contains **16 proposed requests**: two development
workspaces × verifier diagnostics or failure notice × four fresh responses.
There are four unique payloads. Each request gets the same original failing
workspace for its task; it produces one response with no subsequent feedback,
repair loop, retry or reassignment. **Execution is not authorized**, and no
runner, provider client, credential handoff or submission is included.

The source gate is published in `00ac8039418f60963c8ac2499c48187dc447e1ae`.
Compute job 60865223 supplied two fresh seed observations with both
`Helper.Transfer` and `Client.Target` failing. The gate also binds eight
byte-identical earlier control observations; those are not new trials. The
separate method policy and named-target measurement manifests are pinned.

`frozen-001/requests/` holds the exact four Bedrock Converse payload objects;
`prompts/` holds readable copies of their system and user text. Full original
seed sources are included exactly. The target Helper API and public Client
specifications stay fixed. Responses contain only the two method-body
interiors. Either body may remain unchanged, and `H.Transfer` use is optional.
The two arms differ only inside the delimited feedback block. The notice arm
states only that verification failed; the diagnostics arm supplies the original
exit code, stdout and stderr after removing exactly one complete
`Results File: /tmp/repodisco-repair-adapter-.../TestResults/...` stdout line.
Original bytes and a reversible transformation record are retained. No other
diagnostic text is removed, summarized or supplemented.

`order.json` preserves the original plan's counterbalanced order: each of four
blocks contains every task-arm cell once, and every cell has mean position 8.5.
Settings remain Claude Opus 4.5 via the named Bedrock model ID, temperature 1.0,
and at most 4,096 output tokens per response. `scope.json` records the frozen
but unapproved status; the root `plan.json` is retained unchanged as historical
prospective design. No slot is allocated to or recovered from the stopped
128-call research session.

The primary outcome is strict whole-workspace verification with protected
sources and all required named units. Method outcomes, actual body edits,
syntactic helper-call occurrences and failure categories remain descriptive.
Two tasks do not become sixteen independent tasks. Transparent Kernel functions
permit direct caller implementations; this does not establish necessary
multi-file edits, helper reuse, sharing/depth effects or held-out performance.

Offline commands:

```text
python3 prepare.py build
python3 prepare.py check
python3 test_plan.py
```

`build` refuses an existing destination and writes only a child of this pilot
directory. Eight focused tests cover exact sources/interfaces, paired equality,
16-slot balance, model-facing information boundaries, exact diagnostic
transformation, transitive pins and freeze tampering. They use temporary local
bundles, never a model or verifier. `freeze.json` binds every frozen file and
all source dependencies; its host metadata and provenance are not model-facing.
The existing policy files are copied unchanged, not extended. Any future
execution needs a separately reviewed method-capable handler and explicit
execution decision; this freeze supplies neither.
