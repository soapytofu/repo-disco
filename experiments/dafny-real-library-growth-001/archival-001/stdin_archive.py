"""Archive-only stdin transport for the completed, frozen library pilot.

The original ops.fetch function and generated remote program remain unchanged.
Only SSH's program transport changes: Python reads its program from stdin,
instead of receiving the entire inventory inside a single -c argument.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
EXECUTION = PACKAGE / "execution-001"
OPS_PATH = EXECUTION / "ops.py"
FREEZE_PATH = EXECUTION / "runtime-freeze.json"
OPS_SHA256 = "35d7109f75a539f251b67297ed487649e21c9cab42b9b0a5e8d4b0d16906a4d1"
RUNTIME_SHA256 = "69d07a07241982e21bf06cf16ed038187c8fd2d2a7fff1e71443515745f49548"
BINDING_SHA256 = "e7a0b712d23e7e1d6b312158af91b10521cf82b1ebf067daedd7c641c3206592"
JOB_ID = "63153129"
MAX_PROGRAM_BYTES = 2 * 1024**2
MAX_ARG_BYTES = 4096
TIMEOUTS = {"estimate": 90, "fetch": 240}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check_pins():
    """Check immutable source bytes before importing or transmitting code."""
    require(not OPS_PATH.is_symlink() and sha(OPS_PATH.read_bytes()) == OPS_SHA256,
            "Frozen ops source identity differs")
    require(not FREEZE_PATH.is_symlink() and sha(FREEZE_PATH.read_bytes()) == RUNTIME_SHA256,
            "Frozen runtime identity differs")
    frozen = json.loads(FREEZE_PATH.read_bytes())
    require(frozen["files"].get("execution-001/ops.py") == OPS_SHA256,
            "Runtime does not bind the required ops source")
    for name, digest in frozen["files"].items():
        parts = PurePosixPath(name).parts
        require(parts and not PurePosixPath(name).is_absolute()
                and all(part not in {".", ".."} for part in parts), "Unsafe frozen path")
        path = PACKAGE / name
        require(all(not parent.is_symlink() for parent in (path, *path.parents))
                and path.is_file() and sha(path.read_bytes()) == digest,
                "Frozen input differs: " + name)
    require(sha((EXECUTION / "execution-binding.json").read_bytes()) == BINDING_SHA256,
            "Canonical execution binding differs")
    return frozen


def load_frozen_ops():
    check_pins()
    # Imports are pure definitions; no live runner, provider, key or native call.
    # Reject ambient same-name modules rather than silently borrowing a runtime.
    expected_modules = {
        "build_runtime": EXECUTION / "build_runtime.py",
        "runtime": EXECUTION / "runtime.py",
        "allocation": EXECUTION / "allocation.py",
        "bounded_requests": EXECUTION / "bounded_requests.py",
        "extract_response": EXECUTION / "extract_response.py",
        "guard": PACKAGE / "common/guard.py",
        "review_native": PACKAGE / "common/review_native.py",
    }
    for name, path in expected_modules.items():
        if name in sys.modules:
            require(Path(getattr(sys.modules[name], "__file__", "")).resolve() == path,
                    "An unrelated module is already imported: " + name)
    sys.dont_write_bytecode = True
    if str(EXECUTION) not in sys.path:
        sys.path.insert(0, str(EXECUTION))
    spec = importlib.util.spec_from_file_location("_growth_archive_frozen_ops", OPS_PATH)
    ops = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ops
    spec.loader.exec_module(ops)
    frozen, binding, digest = ops.identity()
    require(digest == RUNTIME_SHA256 and ops.submitted_job() == JOB_ID,
            "Archive identity does not match the completed pilot")
    for name, path in expected_modules.items():
        require(name in sys.modules and Path(sys.modules[name].__file__).resolve() == path,
                "Frozen import origin differs: " + name)
    check_pins()
    return ops, frozen, binding, digest


class ArchiveTransport:
    """Accept exactly the two calls made by the frozen fetch orchestration."""

    def __init__(self, ops, binding, digest):
        require(Path(ops.__file__).resolve() == OPS_PATH and digest == RUNTIME_SHA256,
                "Only the pinned archival source is supported")
        self.ops = ops
        self.binding = json.loads(json.dumps(binding))
        self.digest = digest

    def __call__(self, action, binding, digest, *, payload=None, seconds=45,
                 job=None, inventory=None):
        require(action in TIMEOUTS, "Only estimate and fetch are permitted")
        require(payload is None, "Archive transport never accepts a data payload")
        require(type(seconds) is int and seconds == TIMEOUTS[action],
                "Archive operation must use its fixed wall timeout")
        require(binding == self.binding and digest == self.digest
                and job == JOB_ID and self.ops.submitted_job() == JOB_ID,
                "Archive operation identity differs")
        require((action == "estimate" and inventory is None)
                or (action == "fetch" and isinstance(inventory, dict)
                    and inventory.get("job_id") == JOB_ID),
                "Inventory is permitted only for the exact final fetch")
        check_pins()
        program = self.ops.remote_program(action, binding, digest, job, inventory).encode("utf-8")
        require(0 < len(program) <= MAX_PROGRAM_BYTES, "Archive program exceeds byte bound")
        # These are the frozen connection options. No host/socket/command override
        # is offered; ProxyCommand=false prevents a new authentication fallback.
        argv = ["ssh", "-S", str(self.ops.SOCKET), "-o", "ControlMaster=no", "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=10", "-o", "ProxyCommand=false", "-o",
                "NumberOfPasswordPrompts=0", self.ops.HOST]
        remote_command = " ".join(shlex.quote(x) for x in [self.ops.PYTHON, "-B", "-"])
        argv.append(remote_command)
        require(all(len(arg.encode("utf-8")) < MAX_ARG_BYTES for arg in argv),
                "Unexpectedly large SSH argument")
        # No shell, retry, provider client, credential access or native invocation.
        # TimeoutExpired propagates; frozen fetch.intent.json stays consumed.
        result = subprocess.run(argv, input=program, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=seconds)
        if result.returncode:
            raise RuntimeError("Bounded archive SSH failed (exit " + str(result.returncode) + "): "
                               + result.stderr.decode(errors="replace")[-4000:])
        return result.stdout


def run_action(action):
    require(action in TIMEOUTS, "Only estimate and fetch are permitted")
    ops, frozen, binding, digest = load_frozen_ops()
    transport = ArchiveTransport(ops, binding, digest)
    if action == "estimate":
        raw = transport("estimate", binding, digest, job=JOB_ID, seconds=90)
        sys.stdout.buffer.write(raw)
        return
    # Reuse the exact frozen function, including local_fresh, terminal estimate,
    # canonical exclusive intents, raw archive retention and inventory checks.
    original = ops.remote
    try:
        ops.remote = transport
        ops.fetch()
    finally:
        ops.remote = original


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("estimate", "fetch"))
    args = parser.parse_args(argv)
    run_action(args.action)


if __name__ == "__main__":
    main()
