"""Offline manifest builder and exact manifest-only packaging; no execution."""
import argparse
from pathlib import Path
import shutil

from runtime import (PACKAGE, canonical, checked_path, load_stages, read_json,
                     require, save, sha, validate_runtime, validate_scope, MAX_CALLS, TASK_ORDER)

EXECUTION_FILES = (
    "runtime.py", "run_pilot.py", "native_host.py", "build_runtime.py", "allocation.py",
    "bounded_requests.py", "credential_transport.py", "provider_error.py",
    "extract_response.py", "copy-provenance.json", "test_runner.py",
    "test_native_host.py", "test_build_runtime.py", "test_allocation.py", "README.md",
    "prior-budget-snapshot.json", "review_collection.py", "test_review_collection.py",
    "test_frontend_policy.py", "adaptation-origins.json", "test_render.py",
)
COMMON_FILES = ("common/guard.py", "common/review_native.py")


def required_inputs(scope, scope_path):
    """Every data-dependent live input is explicitly frozen."""
    require(isinstance(scope.get("renderer"), str), "Frozen renderer path required")
    inputs = set(COMMON_FILES)
    inputs.update("execution-002/" + name for name in EXECUTION_FILES)
    inputs.update((scope_path, scope["renderer"]))
    inputs.add(scope["execution_binding"]["budget_snapshot_input"])
    dependencies = scope.get("runtime_inputs")
    require(isinstance(dependencies, list) and dependencies
            and len(dependencies) == len(set(dependencies)), "Explicit renderer/evidence dependencies required")
    inputs.update(dependencies)
    for project in TASK_ORDER:
        stages = scope["projects"][project]["stages"]
        require(set(stages) == {"1"}, "Four independent tasks required")
        for stage in stages.values():
            inputs.update((stage["edit_profile"], stage["native_profile"]))
            for entry in stage["base_sources"].values():
                inputs.add(entry["path"])
    return inputs


def build(package, scope_path, output):
    package = Path(package)
    scope = validate_scope(read_json(checked_path(package, scope_path)))
    from allocation import validate_frozen_budget
    validate_frozen_budget(package,scope)
    load_stages(package, scope)
    names = required_inputs(scope, scope_path)
    files = {name:sha(checked_path(package,name).read_bytes()) for name in sorted(names)}
    require(all(not any(part in {"authorization.json", "ledger.json", "key", "model-001"}
                        for part in name.split("/")) for name in files), "Live state cannot be a runtime input")
    value = dict(schema="dafny-library-execution-runtime-v1", scope=scope_path,
                 files=files, max_calls=MAX_CALLS, no_resume=True, no_retry=True, no_reassignment=True,
                 requires_fresh_hash_bound_authorization=True)
    save(output,value)
    return value


def validate_complete(package, scope_path, freeze_path, expected_sha):
    value = validate_runtime(package, freeze_path, expected_sha)
    scope = validate_scope(read_json(checked_path(package,scope_path)))
    from allocation import validate_frozen_budget
    validate_frozen_budget(package,scope)
    require(value.get("scope") == scope_path
            and required_inputs(scope,scope_path) <= set(value["files"]), "Runtime omits required input pins")
    stages = load_stages(package,scope)
    return value,scope,stages


def package_frozen(package, manifest, expected_sha, destination):
    """Copy only pinned bytes, never local credentials/outputs or ambient files."""
    package,manifest,destination = Path(package),Path(manifest),Path(destination)
    freeze = validate_runtime(package,manifest,expected_sha)
    validate_complete(package,freeze["scope"],manifest,expected_sha)
    destination.mkdir(parents=True,exist_ok=False)
    for name,digest in freeze["files"].items():
        source = checked_path(package,name)
        target = destination/name
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("xb") as stream:
            stream.write(source.read_bytes())
        require(sha(target.read_bytes()) == digest,"Package copy drifted")
    manifest_name = "execution-002/runtime-freeze.json"
    require(manifest_name not in freeze["files"],"Manifest cannot pin itself")
    target=destination/manifest_name
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("xb") as stream:
        stream.write(manifest.read_bytes())
    return validate_complete(destination,freeze["scope"],target,expected_sha)[0]


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="action",required=True)
    make=sub.add_parser("build")
    make.add_argument("--scope",required=True)
    make.add_argument("--output",type=Path,required=True)
    pack=sub.add_parser("package")
    pack.add_argument("--manifest",type=Path,required=True)
    pack.add_argument("--expected-sha",required=True)
    pack.add_argument("--destination",type=Path,required=True)
    args=parser.parse_args()
    if args.action=="build":
        value=build(PACKAGE,args.scope,args.output)
        print(canonical(dict(files=len(value["files"]),manifest_sha256=sha(args.output.read_bytes()))).decode())
    else:
        value=package_frozen(PACKAGE,args.manifest,args.expected_sha,args.destination)
        print(canonical(dict(files=len(value["files"]),destination=str(args.destination))).decode())


if __name__=="__main__":
    main()

