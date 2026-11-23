"""Transfer the completed evidence with bounded stdin transport.

Preserves the frozen ops.fetch implementation and all integrity/space checks.
The first attempt timed out in read-only inventory; correction 001 established
that inventory but its second SSH launch exceeded the local argument-size
limit before a remote process was started. This version sends the unchanged
archival program through stdin and records the exact inventory and transport.
No model or verifier is invoked. The paid/native runtime remains frozen.
"""
from pathlib import Path
import datetime
import hashlib
import json
import time

import ops

FROZEN_SHA = "5c007d3a1b77a7ff413e9b79a68e1485f18915534fcf05459cf760869ce94d7b"
TEMP_ARCHIVE = Path("/private/tmp/repodisco-growth-005-transfer-002.tar.gz")


def main():
    root = Path(__file__).resolve().parent
    frozen = (root / "runtime-freeze.json").read_bytes()
    assert hashlib.sha256(frozen).hexdigest() == FROZEN_SHA
    freeze = json.loads(frozen)
    assert ops.sha(root / "ops.py") == freeze["repo_files"][ops.REL + "/ops.py"]
    assert not TEMP_ARCHIVE.exists()
    assert not (root / "retrieved-001").exists()
    assert not (root / "transfer-001.json").exists()
    original_remote = ops.remote
    inspection = json.loads(original_remote(
        "import json\nprint(json.dumps({name:(root/name).exists() for name in "
        "('accounting.txt','accounting-review.json','model-001/archive-manifest.json')}))\n",
        seconds=30))
    assert inspection == {"accounting.txt": False, "accounting-review.json": False,
                          "model-001/archive-manifest.json": True}
    with (root / "transfer-inspection-002.json").open("x") as stream:
        json.dump(inspection, stream, indent=2, sort_keys=True)
    calls = []

    def stdin_archival_remote(program, *args, **kwargs):
        assert not args and "data" not in kwargs
        ordinal = len(calls)
        assert kwargs["seconds"] == (90, 180)[ordinal]
        assert "transfer_inventory(root,job,accounting,terminal_review)" in program
        assert "terminal_review=terminal_accounting(accounting,job)" in program
        resolved = program.replace("EXPECTED_RUNTIME", repr(FROZEN_SHA)).encode()
        kwargs["seconds"] = 600
        entry = {"phase": ordinal + 1, "original_wall_seconds": (90, 180)[ordinal],
                 "archival_wall_seconds": 600, "transport": "ssh_stdin",
                 "program_sha256": hashlib.sha256(resolved).hexdigest(),
                 "program_bytes": len(resolved)}
        calls.append(entry)
        started = time.monotonic()
        try:
            data = original_remote(
                "import sys\nexec(compile(sys.stdin.buffer.read(), '<growth-archive-002>', 'exec'))\n",
                data=resolved, **kwargs)
            entry["returned_bytes"] = len(data)
            entry["returned_sha256"] = hashlib.sha256(data).hexdigest()
            destination = root / "archive-recovery-002-estimate.json" if ordinal == 0 else TEMP_ARCHIVE
            with destination.open("xb") as stream:
                stream.write(data)
            return data
        finally:
            entry["elapsed_seconds"] = time.monotonic() - started

    ops.remote = stdin_archival_remote
    try:
        ops.fetch()
    finally:
        ops.remote = original_remote
        record = {"schema": "repodisco-archival-stdin-correction-v1",
                  "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "runtime_sha256": FROZEN_SHA, "frozen_ops_unchanged": True,
                  "calls": calls, "model_calls": 0, "native_verifier_calls": 0,
                  "temporary_archive": str(TEMP_ARCHIVE),
                  "previous_failures": ["fetch-001.stderr", "archive-recovery-001.stderr"]}
        with (root / "archive-recovery-002.json").open("x") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
