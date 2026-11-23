"""Build the reviewed repository-relative execution freeze once; no transport.

Collecting pins is read-only. The explicit ``freeze`` command is reserved for
root's final review, and never creates authorization or a model/native result.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
REL = "experiments/real-repository-growth-001/execution-003"
GROWTH = "experiments/real-repository-growth-001"
PILOT_SHA = "9f2e4c9602b4ce98740f2a3fa1dcf7bbef07d2b0693db8d92d9cc55546820f0c"
PROTOCOL_SHA = "9cf8cc81bd55f83a591c04c2877ab9a0ece3927fcddc31f6f3d42d7953d42057"
OWN = ("build_runtime.py", "ops.py", "preflight.py", "run.sbatch", "test_ops.py", "README.md",
       "runtime.py", "run_pilot.py", "bounded_requests.py", "review.py", "test_runner.py",
       "native_host.py", "test_native_host.py", "copy-provenance.json",
       "credential_transport.py", "test_credential_transport.py", "sdk_probe.py",
       "test_sdk_preflight.py", "test_preflight_timeout.py")


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def safe_file(repo, name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and name == p.as_posix() and not p.is_absolute() and
            ".." not in p.parts and "\\" not in name and "\x00" not in name,
            "Unsafe repository-relative path")
    target = repo / name
    current = target
    while current != repo:
        require(not current.is_symlink(), "Symlink in pinned path: " + name)
        current = current.parent
    require(not repo.is_symlink() and target.is_file(), "Missing regular pinned file: " + name)
    return target


def collect(repo=REPO):
    """Resolve explicit immutable manifests and the reviewed native-host closure.

    Test fixtures are packaged for offline tests only, never imported by live
    dispatch. Historical evidence is private host context, not prompt content.
    No unlisted files, credentials, outputs, authorization, or old live ledgers
    are found through an unrestricted repository walk.
    """
    repo = Path(repo).resolve()
    pins = {}
    origins = {}

    def add(name, expected=None, origin="new execution source"):
        digest = sha(safe_file(repo, name))
        require(expected is None or digest == expected, "Immutable input drift: " + name)
        require(name not in pins or pins[name] == digest, "Conflicting input pin")
        pins[name] = digest
        origins.setdefault(origin, []).append(name)

    def mapping(prefix, values, origin):
        for name, digest in values.items():
            add(prefix + name, digest, origin)

    pilot = GROWTH + "/pilot/"
    add(pilot + "frozen-001/manifest.json", PILOT_SHA, "approved prompt proposal")
    mapping(pilot + "frozen-001/", read(repo / (pilot + "frozen-001/manifest.json")), "approved prompt proposal")
    mapping(pilot, read(repo / (pilot + "frozen-001/preparation-inputs.json")), "prompt preparation dependencies")
    policy = GROWTH + "/protocol-003/"
    add(policy + "runtime-freeze.json", PROTOCOL_SHA, "reviewed policy")
    mapping(policy, read(repo / (policy + "runtime-freeze.json"))["files"], "reviewed policy and offline evidence")
    mapping("", read(repo / (policy + "control-inputs.json"))["files"], "qualified native controls")
    for entry in read(repo / (policy + "reference-inputs.json"))["references"].values():
        mapping("", entry["files"], "qualified full-scope references")
    for project, item in read(repo / (policy + "upstream-inventory.json"))["projects"].items():
        mapping("experiments/real-repository-qualification-001/upstream/" + project + "/",
                item["files"], "exact qualified upstream snapshots")
    for name in OWN:
        add(REL + "/" + name)
    for destination, item in read(repo / REL / "copy-provenance.json").items():
        add(item["source"], item["sha256"], "unchanged execution dependency origin")
        if item.get("modified") is False:
            require(pins[REL + "/" + destination] == item["sha256"], "Copied execution dependency differs")
    for name in ("ops.py", "preflight.py", "test_ops.py"):
        add(GROWTH + "/controls-001/" + name, origin="immutable adaptation provenance")
    # Load only the new adapter's pure dependency enumerator. Importing this
    # module must not execute a model, verifier, subprocess, or network probe.
    spec = importlib.util.spec_from_file_location("growth_native_dependency_inventory", repo / REL / "native_host.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    mapping("", module.immutable_dependencies(repo), "native-host exact closure")
    require(REL + "/runtime-freeze.json" not in pins, "Runtime freeze cannot pin itself")
    require(not any(name.startswith(REL + "/") and any(part in name.split("/") for part in
                ("authorization.json", "model-001", "submissions", "startup-failure.json")) for name in pins),
            "Mutable execution state entered package")
    return dict(schema="repodisco-growth-execution-runtime-v1", repo_files=dict(sorted(pins.items())),
                pilot_freeze_sha256=PILOT_SHA, protocol_freeze_sha256=PROTOCOL_SHA,
                model_calls_authorized=0, proposed_max_new_requests=8,
                authorization_created=False, no_retries=True, no_reassignment=True,
                repository_relative_layout=True,
                resources=dict(cpus=1, memory_gb=8, job_seconds=14400, no_requeue=True,
                               dafny_native_wall_seconds=300, dafny_resource_limit=100000,
                               vest_native_wall_seconds=900, cargo_build_jobs=1, verus_num_threads=1,
                               provider_read_seconds=180),
                package_bytes=sum((repo / name).stat().st_size for name in pins),
                dependency_origins={key: sorted(set(names)) for key, names in sorted(origins.items())},
                adaptation_origins={name: sha(repo / GROWTH / "controls-001" / name)
                                    for name in ("ops.py", "preflight.py", "test_ops.py")},
                production_excludes_synthetic_helpers=True,
                synthetic_helpers_only_for_offline_tests=[policy + "test_fixtures.py", policy + "test_integration.py"])


def freeze(repo=REPO):
    repo = Path(repo).resolve()
    destination = repo / REL / "runtime-freeze.json"
    require(not destination.exists(), "Freeze already exists: no overwrite or automatic revision")
    value = collect(repo)
    with destination.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return dict(runtime_freeze_sha256=sha(destination), repo_files=len(value["repo_files"]),
                package_bytes=value["package_bytes"], model_calls=0, native_calls=0,
                execution_authorized=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "freeze"))
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args()
    result = freeze(args.repo) if args.action == "freeze" else collect(args.repo)
    if args.action == "inspect":
        result = dict(repo_files=len(result["repo_files"]), package_bytes=result["package_bytes"],
                      model_calls=0, native_calls=0, runtime_freeze_written=False)
    print(json.dumps(result, indent=2, sort_keys=True))
