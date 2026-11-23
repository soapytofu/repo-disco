"""Compute-only, serial, fresh native capture. No provider or credential code."""
from dataclasses import dataclass
import os
import math
from pathlib import Path
import signal
import socket
import subprocess
import time

from runtime import canonical, native, require, save, save_bytes, save_sources, sha, source_files


@dataclass(frozen=True)
class NativeObservation:
    """Only the current host invocation constructs live evidence."""
    event_sha256: str
    record: dict
    raw: dict


def capture(argv, cwd, seconds, stdout_path, stderr_path):
    """Bound one process group and always reap/terminate descendants.

    No shell and no retry. Fake process tests invoke this function with Python,
    never a verifier. Native stdout/stderr stay byte-exact in exclusive files.
    """
    require(isinstance(argv, list) and argv and all(isinstance(x, str) and x for x in argv),
            "Explicit argv required")
    require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0,
            "Finite positive process wall cap required")
    started = time.monotonic()
    process = None
    timed_out = False
    with Path(stdout_path).open("xb") as out, Path(stderr_path).open("xb") as err:
        try:
            process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       start_new_session=True,
                                       env={k:v for k,v in os.environ.items()
                                            if not k.startswith("AWS_") and k not in
                                            {"BOTO_CONFIG","BOTO_PATH","BEDROCK_API_KEY"}})
            try:
                process.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=10)
        finally:
            if process is not None:
                # A normal parent exit does not mean every child exited.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                if process.poll() is None:
                    process.wait(timeout=10)
            out.flush()
            err.flush()
            os.fsync(out.fileno())
            os.fsync(err.fileno())
    return dict(exit_code=process.returncode, elapsed_seconds=time.monotonic()-started, timeout=timed_out)


def fingerprint(adapter, profile, *, check_match=True):
    root = Path(adapter["toolchain_root"]).expanduser()
    require(root.is_dir() and not root.is_symlink(), "Pinned toolchain missing")
    files = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "Toolchain symlink prohibited")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = sha(path.read_bytes())
    require(files, "Empty toolchain")
    executable = Path(profile["command"][0])
    solver = Path(adapter["solver"]).expanduser()
    require(executable.is_absolute() and executable.is_file() and not executable.is_symlink()
            and solver.is_absolute() and solver.is_file() and not solver.is_symlink(), "Tool executables missing")
    require(executable.resolve().is_relative_to(root.resolve()), "Executable outside pinned installation")
    observed = dict(profile["toolchain"])
    observed.update(executable_sha256=sha(executable.read_bytes()),
                    dafny_package_sha256=files, solver_sha256=sha(solver.read_bytes()))
    require(not check_match or observed == profile["toolchain"], "Native installation fingerprint drifted")
    return observed


class FreshNativeHost:
    synthetic = False

    def __init__(self):
        require(os.environ.get("SLURM_JOB_ID") and "login" not in socket.gethostname().lower(),
                "Fresh native runs require compute provenance")
        require(os.environ.get("SLURM_CPUS_PER_TASK") == "1", "Exactly one serial CPU required")
        self.host = dict(job_id=os.environ["SLURM_JOB_ID"], hostname=socket.gethostname(),
                         partition=os.environ.get("SLURM_JOB_PARTITION"), cpus_per_task=1)
        require(isinstance(self.host["partition"], str) and self.host["partition"], "Partition provenance missing")
        self.used_events = set()
        self.prepared = False

    def prepare(self, stages, destination):
        """Validate pinned installation/version before any provider dispatch."""
        require(not self.prepared, "Native host cannot be prepared twice")
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)
        seen = set()
        for (project, number), stage in sorted(stages.items()):
            require(number == 1, "Independent task stage required")
            identity = sha(canonical(dict(toolchain=stage.native_profile["toolchain"], adapter=stage.adapter)))
            if identity in seen:
                continue
            seen.add(identity)
            profile, adapter = stage.native_profile, stage.adapter
            before = fingerprint(adapter, profile)
            project_path = destination / project
            project_path.mkdir()
            commands = [("dafny", [profile["command"][0], "--version"], before["dafny_version"]),
                        ("solver", [str(Path(adapter["solver"]).expanduser()), "-version"], before["solver_version"])]
            for name, argv, expected in commands:
                out, err = project_path / (name + ".stdout"), project_path / (name + ".stderr")
                meta = capture(argv, project_path, 30, out, err)
                save(project_path / (name + ".record.json"), dict(argv=argv, **meta))
                require(meta["exit_code"] == 0 and not meta["timeout"] and not err.read_bytes()
                        and out.read_bytes().decode().strip() == expected, "Native version preflight differs")
            after = fingerprint(adapter, profile)
            save(project_path / "environment.json", dict(toolchain=before, toolchain_after=after, host=self.host))
        self.prepared = True

    def check_tools(self, stages):
        seen = set()
        for (project, number), stage in sorted(stages.items()):
            require(number == 1, "Independent task stage required")
            identity = sha(canonical(dict(toolchain=stage.native_profile["toolchain"], adapter=stage.adapter)))
            if identity in seen:
                continue
            seen.add(identity)
            fingerprint(stage.adapter, stage.native_profile)

    def run(self, profile, sources, event, destination, adapter):
        require(self.prepared, "Native host preflight absent")
        require(event.get("schema") == "dafny-library-fresh-native-event-v1"
                and event.get("synthetic") is False and event["run_id"] not in self.used_events,
                "Fresh non-synthetic invocation required")
        require(event["candidate_sha256"] == sha(canonical(native.hashes(sources)))
                and event["profile_sha256"] == sha(canonical(profile)), "Native dispatch source/profile differs")
        require(type(adapter.get("wall_seconds")) in (int, float) and 0 < adapter["wall_seconds"] <= 3600,
                "Bounded native wall cap required")
        self.used_events.add(event["run_id"])
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)
        save(destination / "event.json", event)
        workspace = destination / "workspace"
        save_sources(workspace, sources)
        before = native.hashes(source_files(workspace))
        require(before == native.hashes(sources), "Fresh workspace source differs")
        tools = fingerprint(adapter, profile)
        raw_path = destination / "raw"
        raw_path.mkdir()
        resources = raw_path / "resources.txt"
        argv = list(profile["command"])
        # This command is already source/order/resource-qualified in the frozen
        # profile; no shell, extra verification inputs or resource escalation.
        invocation = ["/usr/bin/time", "-v", "-o", str(resources.resolve())] + argv
        save(destination / "invocation-start.json", dict(schema="dafny-library-native-invocation-v1",
             event_sha256=sha(canonical(event)), argv=argv, wrapper_argv=invocation,
             host=self.host, before_sha256=before, wall_seconds=adapter["wall_seconds"]))
        meta = capture(invocation, workspace, adapter["wall_seconds"], raw_path / "stdout.txt", raw_path / "stderr.txt")
        if not resources.exists():
            # Missing metrics remain explicit evidence and block acceptance.
            save_bytes(resources, b"")
        for path in sorted(workspace.rglob("*.csv")):
            require(path.is_file() and not path.is_symlink(), "Native CSV is not a regular file")
            save_bytes(raw_path / "csv" / path.relative_to(workspace), path.read_bytes())
        after = native.hashes(source_files(workspace))
        # Preserve the actual post-run fingerprint even on drift; replay then
        # rejects it without losing the process record/raw result.
        after_tools = fingerprint(adapter, profile, check_match=False)
        raw = {path.relative_to(raw_path).as_posix():path.read_bytes()
               for path in sorted(raw_path.rglob("*")) if path.is_file()}
        record = dict(schema=native.RECORD_SCHEMA, run_id=event["run_id"], origin="model_candidate",
                      source_before_sha256=before, source_after_sha256=after,
                      argv=argv, toolchain=tools, toolchain_after=after_tools,
                      raw_sha256=native.hashes(raw), attempts=1, model_calls=0, host=self.host, **meta)
        save(destination / "record.json", record)
        return NativeObservation(sha(canonical(event)), record, raw)

