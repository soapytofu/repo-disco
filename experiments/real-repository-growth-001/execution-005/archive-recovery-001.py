"""Operator-reviewed archival timeout correction; never runs a model or verifier.

The first frozen fetch stopped in its read-only inventory at 90 seconds.
Inspection found no local retrieval/receipt or remote accounting files, and
its orphaned read-only process has finished. Reuse the exact frozen fetch and
all its integrity/space/exclusive-write checks, changing only SSH wall limits.
"""
from pathlib import Path
import datetime
import hashlib
import json
import time

import ops


def main():
    root = Path(__file__).resolve().parent
    frozen_bytes = (root / "runtime-freeze.json").read_bytes()
    assert hashlib.sha256(frozen_bytes).hexdigest() == "5c007d3a1b77a7ff413e9b79a68e1485f18915534fcf05459cf760869ce94d7b"
    freeze = json.loads(frozen_bytes)
    name = "experiments/real-repository-growth-001/execution-005/ops.py"
    assert hashlib.sha256((root / "ops.py").read_bytes()).hexdigest() == freeze["repo_files"][name]
    inspection = json.loads((root / "transfer-inspection-001.json").read_bytes())
    assert inspection["cleanup"]["state"] in ("already_absent", "terminated")
    assert not (root / "retrieved-001").exists()
    assert not (root / "transfer-001.json").exists()
    original_remote = ops.remote
    calls = []

    def bounded_archival_remote(program, *args, **kwargs):
        old_seconds = kwargs["seconds"]
        expected = (90, 180)[len(calls)]
        assert old_seconds == expected
        assert "transfer_inventory(root,job,accounting,terminal_review)" in program
        assert "terminal_review=terminal_accounting(accounting,job)" in program
        kwargs["seconds"] = 600
        entry = {"original_wall_seconds": old_seconds, "archival_wall_seconds": 600,
                 "program_sha256": hashlib.sha256(program.encode()).hexdigest()}
        calls.append(entry)
        started = time.monotonic()
        try:
            result = original_remote(program, *args, **kwargs)
            entry["returned_bytes"] = len(result)
            return result
        finally:
            entry["elapsed_seconds"] = time.monotonic() - started

    ops.remote = bounded_archival_remote
    try:
        ops.fetch()
    finally:
        ops.remote = original_remote
        record = {"schema": "repodisco-archival-timeout-correction-v1",
                  "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "frozen_ops_unchanged": True, "calls": calls,
                  "model_calls": 0, "native_verifier_calls": 0,
                  "previous_read_only_failure_preserved": "fetch-001.stderr"}
        with (root / "archive-recovery-001.json").open("x") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
