"""One-shot compute verifier for the frozen repository-growth pilot.

No provider, scheduler submission, acceptance issuance or revision promotion.
Native invocation is disabled outside a one-CPU Slurm compute allocation.
Injected process/tool hooks require explicitly synthetic, default-rejected tests.
"""
from dataclasses import asdict, dataclass
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import native_failure_policy

GROWTH = Path("experiments/real-repository-growth-001")
PILOT_FREEZE_SHA256 = "9f2e4c9602b4ce98740f2a3fa1dcf7bbef07d2b0693db8d92d9cc55546820f0c"
PROTOCOL_FREEZE_SHA256 = "9cf8cc81bd55f83a591c04c2877ab9a0ece3927fcddc31f6f3d42d7953d42057"
PROTOCOL_RUNTIME_SHA256 = "ff6b8cecf1c1f1140e0b7fb1c27be0aa66c5c0f81be14767cf2b49b74bcefac1"
CONTROL_RUNTIME_SHA256 = "44ec70080a6682007d6451e8cfe487450fe92871fbf72d0336c34505ccb922c0"
VERSION = "repodisco-growth-native-host-v2-completed-resource-outcome"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def _no_symlink(path):
    for current in (path, *path.parents):
        require(not current.is_symlink(), "Symlink in native source/evidence/tool path")


def file_sha(path):
    path = Path(path)
    _no_symlink(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(repo, name, digest):
    path = Path(repo) / name
    _no_symlink(path)
    raw = path.read_bytes()
    require(sha(raw) == digest, "Immutable native dependency changed: " + str(name))
    return raw


def _json(raw):
    return json.loads(raw)


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _no_symlink(path)
    raw = value if isinstance(value, bytes) else canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)


def _pilot(repo):
    folder = GROWTH / "pilot/frozen-001"
    manifest = _json(_read(repo, folder / "manifest.json", PILOT_FREEZE_SHA256))
    order = _json(_read(repo, folder / "order.json", manifest["order.json"]))
    binding = _json(_read(repo, folder / "protocol-binding.json", manifest["protocol-binding.json"]))
    require(binding["runtime_freeze_sha256"] == PROTOCOL_FREEZE_SHA256 and
            binding["policy_runtime_sha256"] == PROTOCOL_RUNTIME_SHA256, "Frozen protocol authority differs")
    return manifest, order, binding


def protocol_api(repo):
    repo = Path(repo).resolve()
    _, _, binding = _pilot(repo)
    folder = repo / GROWTH / "protocol-003"
    _read(repo, GROWTH / "protocol-003/runtime-freeze.json", PROTOCOL_FREEZE_SHA256)
    for name, digest in binding["files"].items():
        _read(repo, GROWTH / "protocol-003" / name, digest)
    for name, module in list(sys.modules.items()):
        if name in ("integration", "body_policy", "native_adapter", "lexical", "native_parsers") or name.startswith(("lexical.", "native_parsers.")):
            require(getattr(module, "__file__", None) and Path(module.__file__).resolve().is_relative_to(folder),
                    "Mixed cached native protocol module: " + name)
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    api = importlib.import_module("integration")
    require(api.b.policy_digest() == PROTOCOL_RUNTIME_SHA256, "Loaded protocol runtime differs")
    return api


def immutable_dependencies(repo):
    """Exact read-only metadata closure; binaries/images remain cluster-pinned."""
    repo = Path(repo).resolve()
    api = protocol_api(repo)
    manifest, _, binding = _pilot(repo)
    prefix = GROWTH.as_posix()
    pins = {
        prefix + "/pilot/frozen-001/manifest.json": PILOT_FREEZE_SHA256,
        prefix + "/pilot/frozen-001/order.json": manifest["order.json"],
        prefix + "/pilot/frozen-001/protocol-binding.json": manifest["protocol-binding.json"],
        prefix + "/protocol-003/runtime-freeze.json": PROTOCOL_FREEZE_SHA256,
        prefix + "/controls-001/runtime-freeze.json": CONTROL_RUNTIME_SHA256,
    }
    pins.update({prefix + "/protocol-003/" + n: d for n, d in binding["files"].items()})
    catalog = api._catalog()
    names = {catalog["root_gate"]}
    for project, item in catalog["projects"].items():
        names.update((item["gate"], item["review"], item["baseline_profile"]))
        gate = _json(_read(repo, item["gate"], catalog["files"][item["gate"]]))
        base = str(Path(item["gate"]).parent)
        names.update(base + "/" + name for name in gate["bindings"])
        case = next(c for c in item["cases"] if c["id"] == item["reference_case"])
        names.update(name for name in catalog["files"] if name.startswith(case["root"] + "/"))
    pins.update({name: catalog["files"][name] for name in names})
    refs = api.b.read_json((api.b.ROOT / "reference-inputs.json").read_bytes())
    for item in refs["references"].values():
        case = item["artifact_root"] + "/" + item["case"] + "/"
        selected = {refs["root_gate"], item["gate"], item["baseline_profile"],
                    case + "profile.json", case + "record.json", case + "bound-record.json",
                    item["artifact_root"] + "/tools-before.json", item["artifact_root"] + "/tools-after.json"}
        pins.update({name: item["files"][name] for name in selected})
    control = _json(_read(repo, GROWTH / "controls-001/runtime-freeze.json", CONTROL_RUNTIME_SHA256))
    for name in ("tool-image-pins.json", "qualification/coverage-001/results/tool-closure.json",
                 "qualification/vest-container-004/results/verus-tool-closure.json"):
        pins[prefix + "/controls-001/" + name] = control["files"][name]
    for name, digest in pins.items():
        _read(repo, name, digest)
    return dict(sorted(pins.items()))


def _slot(slot, repo):
    _, order, _ = _pilot(repo)
    require(isinstance(slot, dict) and slot in order, "Native slot differs from the frozen eight-call order")
    return dict(slot)


def _scope(project, stage, repo):
    api = protocol_api(repo)
    scope = api.stage_one_scope(project, repo)
    item = api._catalog()["projects"][project]
    gate_raw = _read(repo, item["gate"], scope["qualification_gate_sha256"])
    ref_case = next(c for c in item["cases"] if c["id"] == item["reference_case"])
    tools_name = ref_case["root"] + "/tools-before.json"
    tools_raw = _read(repo, tools_name, api._catalog()["files"][tools_name])
    if stage == 2:
        refs = api.b.read_json((api.b.ROOT / "reference-inputs.json").read_bytes())
        entry = refs["references"][project]
        selected = [refs["root_gate"], entry["gate"], entry["baseline_profile"],
                    entry["artifact_root"] + "/" + entry["case"] + "/profile.json",
                    entry["artifact_root"] + "/" + entry["case"] + "/record.json"]
        data = {name: _read(repo, name, entry["files"][name]) for name in selected}
        overall, gate, base, profile, record = (api.b.read_json(data[name]) for name in selected)
        gate_raw = data[entry["gate"]]
        require(overall["references"][project]["sha256"] == sha(gate_raw) and
                gate["analyst_authored"] is True and gate["accepted_model_parent"] is False and
                gate["native_exit_code"] == 0 and gate["errors"] == 0, "Reviewed full-scope gate differs")
        inventory = ({name: 1 for name in gate["actual_inventory"]} if project == "dafny-vmc" else gate["actual_inventory"])
        scope = dict(scope, stage=2, qualification_gate_sha256=sha(gate_raw),
                     stage_one_qualification_basis={key: scope[key] for key in
                         ("source_reference_case", "source_reference_run", "qualification_gate_sha256", "review_sha256")},
                     source_reference_case=entry["case"], source_reference_run=entry["job_id"]+":"+entry["case"],
                     review_sha256=entry["files"][entry["review"]],
                     reference_root_gate_sha256=refs["root_gate_sha256"],
                     required_inventory=inventory, required_inventory_sha256=sha(canonical(inventory)),
                     logical_command=profile["logical_command"], command_template=api._normalize_command(project, record["command"]),
                     readiness="REVIEWED_FULL_STAGE_TWO_SCOPE_PARENT_LINEAGE_HOST_CHECKED",
                     fixed_unlogged_units=[{k: x[k] for k in ("file", "unit", "counted_as_pass")} for x in
                         (gate.get("fixed_unlogged_growth_definitions", []) if project == "dafny-vmc" else gate["source_bound_unlogged_definitions"])])
        require(scope["toolchain"] == profile["toolchain"] and scope["upstream_warnings"] == base["upstream_warnings"],
                "Stage-one/full-stage tool or warning qualification disagrees")
        require((len(inventory), sum(inventory.values())) == ((269, 269) if project == "dafny-vmc" else (5306, 5416)),
                "Full-stage native inventory differs")
        if project == "vest":
            scope["native_verified_summary"] = sum(gate["native_summary_verified_by_crate"].values())
    require(stage in (1, 2), "Stage one or two required")
    return scope, gate_raw, tools_raw


def audit_candidate_native(binding, artifacts, sources, repo, *, allow_synthetic=False):
    """Pure re-audit for both stages. No host receipt or acceptance is created."""
    api = protocol_api(repo)
    require(isinstance(binding, api.NativeBinding), "Typed native binding required")
    require(binding.origin == "model-candidate" or (allow_synthetic and binding.origin == "synthetic-offline"),
            "Native origin is not eligible for a model candidate")
    if binding.stage == 1:
        extraction = api.audit_model_parent_native(binding, artifacts, sources, repo=repo, allow_synthetic=allow_synthetic)
        return native_failure_policy.attach(extraction, artifacts)
    require(binding.stage == 2, "Known native stage required")
    api._reject_known_analyst(binding, artifacts)
    expected, gate_raw, _ = _scope(binding.project, 2, repo)
    scope, profile, record = (api.b.read_json(artifacts[name]) for name in ("scope.json", "profile.json", "record.json"))
    require(artifacts["qualification-gate.json"] == gate_raw, "Stage-two gate must be the reviewed full-scope gate")
    for key in ("project", "stage", "readiness", "required_inventory", "logical_command", "toolchain",
                "upstream_warnings", "warning_policy_sha256", "tools_record_sha256"):
        require(scope.get(key) == expected[key], "Stage-two reviewed scope changed: " + key)
    require(api._normalize_command(binding.project, record["command"]) == expected["command_template"],
            "Stage-two native command changed")
    require(all(profile.get("resources", {}).get(k) == v for k, v in expected["resources"].items()),
            "Stage-two native resources/concurrency changed")
    require([{k: x.get(k) for k in ("file", "unit", "counted_as_pass")} for x in scope.get("unlogged_definitions", [])] ==
            expected["fixed_unlogged_units"], "Stage-two fixed unlogged scope changed")
    if binding.project == "vest":
        require(scope.get("verus_metadata") == expected["verus_metadata"], "Stage-two Verus report profile changed")
    marked = any(api.b.read_json(artifacts[name]).get("synthetic_offline_fixture") is True
                 for name in ("profile.json", "record.json", "bound-record.json"))
    require(not marked or (allow_synthetic and binding.origin == "synthetic-offline"),
            "Marked synthetic native fixture cannot become real model evidence")
    extraction = api.n.audit_native(binding, artifacts, sources, allow_synthetic=allow_synthetic)
    extraction["host_scope_sha256"] = sha(canonical(expected))
    extraction["known_analyst_native_reuse_rejected"] = True
    return native_failure_policy.attach(extraction, artifacts)


def classify(extraction):
    """Only fully audited bounded resource failures may contain their lineage."""
    code = extraction["native_exit_code"]
    category = extraction["native_category"]
    if code < 0 or code in (124, 137, 143) or extraction["native_execution"].get("timeout"):
        return "TERMINAL_NATIVE_TIMEOUT_OR_SIGNAL", True
    if extraction["qualified_pass"]:
        return "QUALIFIED_PASS", False
    if category == "PROOF_FAILURE" and extraction["coverage_complete"]:
        return "PROOF_FAILURE", False
    outcome = extraction.get("completed_resource_outcome", {})
    if category == "VERIFIER_RESOURCE_FAILURE" and outcome.get("policy") == native_failure_policy.VERSION and outcome.get("eligible") is True:
        return "BOUNDED_NATIVE_RESOURCE_FAILURE", False
    if category in ("PROVED", "PROVED_WITH_WARNINGS") and extraction["coverage_complete"] and extraction["native_proof_pass"]:
        return "WARNING_POLICY_REJECTION", False
    if not extraction["coverage_complete"] and category in ("PROVED", "PROVED_WITH_WARNINGS", "PROOF_FAILURE"):
        return "TERMINAL_INCOMPLETE_NATIVE_COVERAGE", True
    return "TERMINAL_NATIVE_" + category, True


@dataclass(frozen=True)
class NativeResult:
    binding: object | None
    artifacts: dict
    extraction: dict | None
    classification: str
    terminal: bool
    destination: Path
    synthetic: bool
    error: dict | None = None
    native_invocations: int | None = 0
    invocation_attempted: bool = False


def audit_result(slot, sources, result, repo, *, allow_synthetic=False):
    slot = _slot(slot, repo)
    api = protocol_api(repo)
    require(isinstance(result, NativeResult), "Typed native result required")
    require(not result.synthetic or allow_synthetic, "Synthetic native results are rejected by default")
    require(result.binding is not None and result.extraction is not None, "Incomplete native result has no proof score")
    require(result.binding.project == slot["project"] and result.binding.stage == slot["stage"] and
            result.synthetic == (result.binding.origin == "synthetic-offline"), "Result slot/origin differs")
    recomputed = audit_candidate_native(result.binding, result.artifacts, sources, repo, allow_synthetic=allow_synthetic)
    require(canonical(recomputed) == canonical(result.extraction), "Native result extraction is stale or changed")
    classification, terminal = classify(recomputed)
    require((result.classification, result.terminal) == (classification, terminal), "Native result classification changed")
    return dict(classification=classification, terminal=terminal, qualified_pass=recomputed["qualified_pass"],
                extraction_sha256=sha(canonical(recomputed)), accepted_revision_issued=False,
                host_request_provenance_checked_here=False, source_revision_sha256=api.b.digest_map(api.b.source_hashes(sources)))


def _inventory(folder, *, excluded=()):
    excluded = set(excluded)
    result = {}
    for path in sorted(Path(folder).rglob("*")):
        _no_symlink(path)
        if path.is_file():
            name = path.relative_to(folder).as_posix()
            if name not in excluded:
                result[name] = file_sha(path)
    return result


class NativeLaunchError(OSError):
    """The outer native command could not be started; no invocation occurred."""


def _process(args, *, cwd, env, stdout, stderr, timeout):
    """One child process group, hard outer wall timeout, no retry."""
    try:
        process = subprocess.Popen(args, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
    except OSError as error:
        raise NativeLaunchError(str(error)) from error
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        raise


def _native_environment(environment):
    """Verifiers do not need provider credentials; never retain or forward them."""
    prefixes = ("AWS_", "BEDROCK_", "ANTHROPIC_", "OPENAI_", "AZURE_OPENAI_", "GOOGLE_API_", "GEMINI_")
    explicit = {"HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"}
    return {name: value for name, value in environment.items()
            if not name.upper().startswith(prefixes) and name.upper() not in explicit}


class NativeVerifier:
    def __init__(self, repo, *, process_runner=None, tool_observer=None, environment=None, hostname=None, synthetic=False):
        require(type(synthetic) is bool, "Explicit synthetic flag required")
        require(synthetic or all(x is None for x in (process_runner, tool_observer, environment, hostname)),
                "Injected native environment/process/tools require synthetic=True")
        self.repo = Path(repo).resolve()
        self.synthetic = synthetic
        self.api = protocol_api(self.repo)
        self.process_runner = process_runner or _process
        self.tool_observer = tool_observer
        self.environment = _native_environment(os.environ if environment is None else environment)
        self.hostname = socket.gethostname() if hostname is None else hostname
        self.dependencies = immutable_dependencies(self.repo)

    def _compute(self):
        env = self.environment
        require(env.get("SLURM_JOB_ID") and "login" not in self.hostname.lower(), "Slurm compute allocation required")
        require(env.get("SLURM_CPUS_PER_TASK") == "1" and env.get("SLURM_NTASKS", "1") == "1" and
                env.get("SLURM_JOB_NUM_NODES", env.get("SLURM_NNODES", "1")) == "1", "One node, task and CPU required")
        require(env.get("SLURM_JOB_PARTITION") in ("test", "shared"), "Qualified nonpreemptible partition required")
        if self.synthetic:
            require(self.process_runner is not _process and self.tool_observer is not None,
                    "Synthetic tests cannot fall through to real native processes/tools")
        return dict(job_id=env["SLURM_JOB_ID"], hostname=self.hostname, partition=env["SLURM_JOB_PARTITION"],
                    cpus=1, synthetic_offline_fixture=self.synthetic, live_partition_check_is_submission_host_responsibility=True)

    def _tools(self, project, expected):
        if self.tool_observer is not None:
            observed = self.tool_observer(project, dict(expected))
            require(observed == expected, "Synthetic observed tool closure changed")
            return observed
        image = Path(expected["image"])
        q = image.parent.parent
        closure_name = (GROWTH / "controls-001/qualification" / expected["closure_path"]).as_posix()
        closure = _json(_read(self.repo, closure_name, self.dependencies[closure_name]))
        base = q / ("toolchains/dafny-vmc/unpacked" if project == "dafny-vmc" else "vest-container-002/tools/unpacked")
        require(file_sha(image) == expected["image_sha256"], "Native container image changed")
        for name, digest in closure.items():
            self.api.b.path_name(name)
            require(file_sha(base / name) == digest, "Native tool closure changed: " + name)
        require(len(closure) == expected["checked_tool_files"], "Native tool closure count differs")
        return expected

    def verify(self, slot, sources, destination, run_id):
        slot = _slot(slot, self.repo)
        environment = self._compute()
        require(isinstance(run_id, str) and self.api.b.IDENTITY.fullmatch(run_id), "Bounded native run ID required")
        hashes = self.api.b.check_workspace(slot["project"], slot["stage"], sources)
        scope, gate_raw, tools_raw = _scope(slot["project"], slot["stage"], self.repo)
        expected_tools = self.api.b.read_json(tools_raw)
        destination = Path(destination).absolute()
        _no_symlink(destination)
        require(not destination.exists(), "Existing native destination: no retry, restart or overwrite")
        if not self.synthetic:
            # Both container profiles bind only the reviewed cluster output tree.
            bind = scope["command_template"][scope["command_template"].index("--bind") + 1].split(":")[0]
            require(destination.is_relative_to(Path(bind)), "Native work/evidence must be inside the qualified container bind")
        destination.mkdir(parents=True, exist_ok=False)
        work = destination / "workspace"
        target = destination / "fresh-target"
        native_dir = destination / "native"
        work.mkdir(); native_dir.mkdir()
        command = [x.replace("<WORKSPACE>", str(work)).replace("<FRESH_TARGET>", str(target)) for x in scope["command_template"]]
        limit = scope["resources"]["native_wall_seconds"]
        profile = dict(project=slot["project"], source_sha256=hashes, logical_command=scope["logical_command"],
                       toolchain=scope["toolchain"], resources=scope["resources"], model_calls=0,
                       synthetic_offline_fixture=self.synthetic, slot=slot, native_host=VERSION)
        artifacts = {}
        binding = None
        native_invocations = 0
        invocation_attempted = False
        try:
            for name, raw in sources.items():
                _write(work / name, raw)
            before = _inventory(work)
            _write(destination / "source-before.json", dict(expected=hashes, observed=before, match=before == hashes))
            require(before == hashes, "Materialized native source differs")
            tools_before = self._tools(slot["project"], expected_tools)
            _write(destination / "tools-before.json", tools_before)
            _write(destination / "environment.json", environment)
            _write(destination / "profile.json", profile)
            _write(destination / "invocation.json", dict(run_id=run_id, slot=slot, command=command,
                    hard_wall_seconds=limit, outer_timeout_seconds=limit+25, attempts=1, native_invocations_max=1,
                    model_calls=0, synthetic_offline_fixture=self.synthetic,
                    candidate_source_revision_sha256=self.api.b.digest_map(hashes), immutable_dependencies=self.dependencies))
            # Exclusive reservation is created before dispatch and never removed.
            _write(destination / "native-reserved.json", dict(run_id=run_id, slot_id=slot["slot_id"], no_retry=True))
            wrapped = ["/usr/bin/time", "-v", "-o", str(native_dir / "resources.txt"), "timeout", "-k", "10s", str(limit)+"s", *command]
            env = dict(_native_environment(self.environment), OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
            started = time.monotonic()
            outer_timeout = False
            with (native_dir / "stdout.txt").open("xb") as stdout, (native_dir / "stderr.txt").open("xb") as stderr:
                try:
                    invocation_attempted = True
                    native_invocations = None
                    exit_code = self.process_runner(wrapped, cwd=str(destination), env=env, stdout=stdout,
                                                     stderr=stderr, timeout=limit+25)
                    native_invocations = 1
                    require(type(exit_code) is int, "Native process return code missing")
                except subprocess.TimeoutExpired:
                    exit_code, outer_timeout, native_invocations = 124, True, 1
                except NativeLaunchError:
                    native_invocations = 0
                    raise
            elapsed = time.monotonic() - started
            if not (native_dir / "resources.txt").exists():
                _write(native_dir / "resources.txt", b"NATIVE_RESOURCE_CAPTURE_MISSING\n")
                resource_missing = True
            else:
                resource_missing = False
            raw = {name: (native_dir / name).read_bytes() for name in ("stdout.txt", "stderr.txt", "resources.txt")}
            record = dict(command=command, cwd=str(destination), exit_code=exit_code, elapsed_seconds=elapsed,
                          timeout=exit_code == 124, outer_timeout=outer_timeout, model_calls=0, attempts=1,
                          synthetic_offline_fixture=self.synthetic, resource_capture_missing=resource_missing,
                          artifacts={name: sha(data) for name, data in raw.items()})
            _write(native_dir / "record.json", record)
            excluded = []
            if slot["project"] == "dafny-vmc":
                for path in sorted((work / "TestResults").rglob("*.csv")):
                    _no_symlink(path)
                    relative = path.relative_to(work).as_posix()
                    name = "csv/" + relative
                    raw[name] = path.read_bytes()
                    _write(native_dir / name, raw[name])
                    excluded.append(relative)
            after = _inventory(work, excluded=excluded)
            _write(destination / "source-after.json", dict(expected=hashes, observed=after, match=after == hashes))
            tools_after = self._tools(slot["project"], expected_tools)
            _write(destination / "tools-after.json", tools_after)
            require(before == after == hashes and tools_before == tools_after, "Source or tool integrity changed during native verification")
            bound = dict(run_id=run_id, profile_sha256=sha(canonical(profile)), source_sha256=before,
                         source_after_sha256=after, logical_command=scope["logical_command"], toolchain=scope["toolchain"],
                         raw_sha256={name: sha(data) for name, data in sorted(raw.items())}, model_calls=0, attempts=1,
                         exit_code=exit_code, elapsed_seconds=elapsed, synthetic_offline_fixture=self.synthetic)
            native_scope = dict(schema="repodisco-native-growth-scope-v2", project=slot["project"], stage=slot["stage"],
                    qualification_gate_sha256=sha(gate_raw), readiness=scope["readiness"], command_sha256=sha(canonical(command)),
                    logical_command=scope["logical_command"], toolchain=scope["toolchain"],
                    tools_record_sha256=sha(canonical(tools_before)), warning_policy_sha256=scope["warning_policy_sha256"],
                    upstream_warnings=scope["upstream_warnings"], required_inventory=scope["required_inventory"],
                    unlogged_definitions=[dict(item, source_sha256=hashes[item["file"]]) for item in scope["fixed_unlogged_units"]])
            if slot["project"] == "vest":
                native_scope["verus_metadata"] = scope["verus_metadata"]
            artifacts = {**raw, "scope.json": canonical(native_scope), "qualification-gate.json": gate_raw,
                         "profile.json": (destination / "profile.json").read_bytes(),
                         "bound-record.json": canonical(bound), "record.json": (native_dir / "record.json").read_bytes(),
                         "tools-before.json": (destination / "tools-before.json").read_bytes(),
                         "tools-after.json": (destination / "tools-after.json").read_bytes()}
            for name in ("scope.json", "qualification-gate.json", "bound-record.json"):
                _write(destination / name, artifacts[name])
            binding = self.api.NativeBinding(slot["project"], slot["stage"],
                        "synthetic-offline" if self.synthetic else "model-candidate", run_id,
                        self.api.b.digest_map(hashes), PROTOCOL_RUNTIME_SHA256,
                        tuple(sorted((name, sha(data)) for name, data in artifacts.items())))
            _write(destination / "native-binding.json", asdict(binding))
            require(not resource_missing, "Native resource capture missing; no correctness score")
            extraction = audit_candidate_native(binding, artifacts, sources, self.repo, allow_synthetic=self.synthetic)
            classification, terminal = classify(extraction)
            result = NativeResult(binding, artifacts, extraction, classification, terminal, destination, self.synthetic,
                                  native_invocations=native_invocations, invocation_attempted=invocation_attempted)
            _write(destination / "native-units.json", canonical(extraction))
            _write(destination / "native-result.json", dict(classification=classification, terminal=terminal,
                    qualified_pass=extraction["qualified_pass"], extraction_sha256=sha(canonical(extraction)),
                    native_binding_sha256=sha(canonical(asdict(binding))), synthetic_offline_fixture=self.synthetic,
                    native_invocations=native_invocations, invocation_attempted=invocation_attempted,
                    accepted_revision_issued=False, no_retry=True))
            return result
        except Exception as error:
            failure = dict(type=type(error).__name__, message=str(error), native_host=VERSION,
                           raw_evidence_preserved=True, no_retry=True, synthetic_offline_fixture=self.synthetic,
                           native_invocations=native_invocations, invocation_attempted=invocation_attempted,
                           accepted_revision_issued=False)
            _write(destination / "failure.json", failure)
            return NativeResult(binding, artifacts, None, "TERMINAL_NATIVE_INTEGRITY_OR_EXECUTION_ERROR", True,
                                destination, self.synthetic, failure, native_invocations, invocation_attempted)

    __call__ = verify
