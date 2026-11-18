"""Offline reviewed-control replay and prospective actual-parent boundary.

Nothing here runs a verifier, calls a model, creates acceptance or authenticates
the trusted host. The host must pin this runtime and the candidate's provenance.
"""
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import body_policy as b
import native_adapter as n

NativeBinding = n.NativeBinding
AcceptedParentBinding = n.AcceptedParentBinding
ROOT_GATE_SHA256 = "3325a3a688638bf5a894a9618722c811b9e58dc9a02c867730e41405fa048fd2"
DEFAULT_REPO = b.ROOT.parents[2]
STAGES = {"dafny-vmc": ("vmc-move", "vmc-pair"), "vest": ("vest-frame", "vest-batch")}


def _catalog():
    b.load_assets()
    catalog = b.read_json((b.ROOT / "control-inputs.json").read_bytes())
    n.require(catalog["root_gate_sha256"] == ROOT_GATE_SHA256, "Reviewed control authority differs")
    return catalog


def _load(repo, names, catalog):
    n.require(all(name in catalog["files"] for name in names), "Unreviewed evidence path")
    return n._read_pinned(repo, {name: catalog["files"][name] for name in names})


def _project(project, repo):
    catalog = _catalog()
    n.require(project in catalog["projects"], "Unknown qualified project")
    item = catalog["projects"][project]
    names = {catalog["root_gate"], item["gate"], item["review"], item["baseline_profile"]}
    data = _load(repo, names, catalog)
    root, gate, review, base = (b.read_json(data[name]) for name in
                               (catalog["root_gate"], item["gate"], item["review"], item["baseline_profile"]))
    n.exact(root, dict(schema="repodisco-growth-control-gates-v1", status="BOTH_PROJECT_CONTROL_GATES_PASSED",
                       accepted_model_parents_issued=0, model_calls=0, paid_execution_authorized=False))
    n.require(root["projects"][project]["sha256"] == b.sha(data[item["gate"]]), "Root/project control link differs")
    n.exact(gate, dict(schema="repodisco-growth-stage-one-scope-qualification-v1", project=project, stage=1,
                       status="SOURCE_AND_NATIVE_INVENTORY_REVIEW_PASSED", reference_reviewed=True,
                       negative_controls_reviewed=True, analyst_authored=True, model_acceptance=False,
                       accepted_stage_one_revision_issued=False, model_calls=0))
    n.require(gate["required_inventory_sha256"] == b.sha(b.canonical(gate["required_inventory"])),
              "Stage-one native inventory hash differs")
    n.exact(review, dict(status="CONTROL_EVIDENCE_REPLAY_PASSED", state="COMPLETE", project=project, model_calls=0))
    n.require(review["matched_expectations"] == len(item["cases"]) == gate["control_expectations_matched"] and
              not review["undispatched"], "Incomplete reviewed control gate")
    prefix = str(Path(item["gate"]).parent) + "/"
    extra = _load(repo, [prefix + name for name in gate["bindings"]], catalog)
    n.require(all(b.sha(extra[prefix + name]) == digest for name, digest in gate["bindings"].items()),
              "Project control gate dependency changed")
    data.update(extra)
    plan = b.read_json(data[prefix + "plan.json"])
    n.require(gate["exact_upstream_warnings"] == base["upstream_warnings"], "Reviewed warning policy differs")
    return catalog, item, data, gate, review, base, plan


def _case_bytes(project, case_id, repo):
    catalog, item, data, gate, review, base, plan = _project(project, repo)
    selected = [case for case in item["cases"] if case["id"] == case_id]
    n.require(len(selected) == 1, "Case is not one of the reviewed actual controls")
    case = selected[0]
    prefix = case["root"] + "/"
    names = [name for name in catalog["files"] if name.startswith(prefix)]
    case_data = _load(repo, names, catalog)
    reviewed_prefix = case_id + "/"
    for name, digest in review["raw_files"].items():
        if name.startswith(reviewed_prefix):
            actual = prefix + name[len(reviewed_prefix):]
            n.require(actual in case_data and b.sha(case_data[actual]) == digest, "Reviewed raw case drift")
    data.update(case_data)
    entry = [entry for entry in plan["cases"][project] if entry["id"] == case_id]
    n.require(len(entry) == 1, "Case missing from fixed native plan")
    return case, entry[0], data, gate, review, base, catalog, item


def _normalize_command(project, command):
    n.require(isinstance(command, list) and all(isinstance(x, str) for x in command), "Native command absent")
    command = list(command)
    for flag, marker in (("--pwd", "<WORKSPACE>"), ("--target-dir", "<FRESH_TARGET>")):
        required = flag == "--pwd" or project == "vest"
        n.require(command.count(flag) == int(required), "Native command path slot differs")
        if required:
            index = command.index(flag) + 1
            n.require(index < len(command) and command[index].startswith("/") and
                      "\x00" not in command[index], "Absolute native workspace/target path required")
            command[index] = marker
    return command


def stage_one_scope(project, repo=DEFAULT_REPO):
    """Reviewed scope facts, not a native result or accepted model parent.

    Required inventory comes from the actual stage-one run. It is not obtained
    by subtracting child units from a full-stage reference.
    """
    catalog = _catalog()
    n.require(project in catalog["projects"], "Unknown qualified project")
    ref = catalog["projects"][project]["reference_case"]
    case, entry, data, gate, review, base, catalog, item = _case_bytes(project, ref, repo)
    prefix = case["root"] + "/"
    profile, record, tools = (b.read_json(data[prefix + name]) for name in
                              ("profile.json", "native/record.json", "tools-before.json"))
    n.require(case["stage"] == 1 and profile["source_sha256"] == gate["reference_source_sha256"],
              "Stage-one qualification source identity differs")
    resource_keys = ("cpus", "native_wall_seconds", "resource_limit") if project == "dafny-vmc" else (
        "cpus", "native_wall_seconds", "cargo_build_jobs", "verus_num_threads")
    descriptor = dict(schema="repodisco-reviewed-stage-one-host-scope-v3", project=project, stage=1,
                      source_reference_case=ref, source_reference_run=gate["reference_job"] + ":" + ref,
                      root_gate_sha256=ROOT_GATE_SHA256, qualification_gate_sha256=b.sha(data[item["gate"]]),
                      review_sha256=b.sha(data[item["review"]]), required_inventory=gate["required_inventory"],
                      required_inventory_sha256=gate["required_inventory_sha256"],
                      logical_command=profile["logical_command"], command_template=_normalize_command(project, record["command"]),
                      toolchain=profile["toolchain"], tools_record_sha256=b.sha(b.canonical(tools)),
                      resources={key: profile["resources"][key] for key in resource_keys},
                      upstream_warnings=base["upstream_warnings"],
                      warning_policy_sha256=b.sha((b.ROOT / "native_parsers/warning_policy.py").read_bytes()),
                      fixed_unlogged_units=[dict(file=x["file"], unit=x["unit"], counted_as_pass=False)
                                            for x in gate.get("fixed_unlogged_definitions", [])],
                      readiness="STAGE_ONE_REFERENCE_AND_NEGATIVES_REVIEWED",
                      model_origin_acceptance=False, accepted_revision_issued=False)
    if project == "vest":
        descriptor["verus_metadata"] = dict(crates=base["required"]["crates"], version=base["required"]["version"], num_threads=1)
        descriptor["native_verified_summary"] = gate["native_verified_summary"]
        descriptor["timed_occurrences_are_not_unique_logical_obligations"] = True
    return descriptor


def control_material(project, case_id, repo=DEFAULT_REPO):
    """Load exactly pinned analyst controls, including intentional omissions."""
    case, entry, data, gate, review, base, catalog, item = _case_bytes(project, case_id, repo)
    prefix = case["root"] + "/"
    profile, bound, record, before = (b.read_json(data[prefix + name]) for name in
                                     ("profile.json", "bound-record.json", "native/record.json", "tools-before.json"))
    n.require(profile["case"] == entry, "Native case profile differs from reviewed control plan")
    original = ({name: 1 for name in base["required_units"]} if project == "dafny-vmc" else base["required"]["inventory"])
    required = {**original, **entry["required_new_inventory"]}
    case_gate = dict(schema="repodisco-exact-analyst-control-scope-v3", project=project, stage=case["stage"],
                     case=case_id, root_gate_sha256=ROOT_GATE_SHA256,
                     source_qualification_gate_sha256=b.sha(data[item["gate"]]),
                     required_inventory_sha256=b.sha(b.canonical(required)), model_acceptance=False)
    observation = b.read_json(data[prefix + "observation.json"])
    scope = dict(schema="repodisco-native-growth-scope-v2", project=project, stage=case["stage"],
                 qualification_gate_sha256=b.sha(b.canonical(case_gate)), readiness="ANALYST_CONTROL_ONLY",
                 command_sha256=b.sha(b.canonical(record["command"])), logical_command=profile["logical_command"],
                 toolchain=profile["toolchain"], tools_record_sha256=b.sha(b.canonical(before)),
                 warning_policy_sha256=b.sha((b.ROOT / "native_parsers/warning_policy.py").read_bytes()),
                 upstream_warnings=base["upstream_warnings"], required_inventory=required,
                 unlogged_definitions=observation["fixed_unlogged_definitions"])
    if project == "vest":
        scope["verus_metadata"] = dict(crates=base["required"]["crates"], version=base["required"]["version"], num_threads=1)
    artifacts = {name: data[prefix + "native/" + name] for name in bound["raw_sha256"]}
    artifacts.update({"scope.json": b.canonical(scope), "qualification-gate.json": b.canonical(case_gate),
                      **{name: data[prefix + name] for name in ("profile.json", "bound-record.json", "tools-before.json", "tools-after.json")},
                      "record.json": data[prefix + "native/record.json"]})
    _, inventory = b.load_assets()
    seed_prefix = "experiments/real-repository-qualification-001/upstream/" + project + "/"
    old_pins = inventory["projects"][project]["files"]
    upstream = n._read_pinned(repo, {seed_prefix + name: digest for name, digest in old_pins.items()})
    sources = {name: upstream[seed_prefix + name] for name in old_pins}
    for name, digest in entry["overlay_sha256"].items():
        raw = data[prefix + "overlay/" + name]
        n.require(b.sha(raw) == digest, "Native overlay is not exact reviewed source")
        sources[name] = raw
    hashes = b.source_hashes(sources)
    n.require(hashes == profile["source_sha256"], "Analyst source inventory differs")
    audit = b.read_json(data[prefix + "prepared-source-audit.json"])
    after = b.read_json(data[prefix + "source-after.json"])
    n.require(audit.get("match") is True and audit.get("expected") == hashes and audit.get("observed") == hashes and
              after.get("match") is True and after.get("source_sha256") == hashes,
              "Native before/after source audit differs")
    parent = b.read_json(data[prefix + "parent-source-audit.json"])
    n.require(parent.get("match") is True and parent.get("expected") == old_pins and parent.get("observed") == old_pins,
              "Native seed source audit differs")
    intent = b.read_json(data[prefix + "intent.json"])
    n.require(intent["command"] == record["command"] and intent["profile_sha256"] == b.sha(b.canonical(profile)) and
              intent["maximum_native_invocations"] == 1 and intent["model_calls"] == 0,
              "Native intent is not bound to actual command/profile")
    binding = NativeBinding(project, case["stage"], "analyst-control", bound["run_id"], b.digest_map(hashes),
                            b.policy_digest(), tuple(sorted(b.source_hashes(artifacts).items())))
    provenance = dict(case=case_id, expected=entry, reviewed_observation=observation,
                      root_gate_sha256=ROOT_GATE_SHA256, project_gate_sha256=b.sha(data[item["gate"]]),
                      reviewed_input_sha256={name: b.sha(raw) for name, raw in sorted(data.items())},
                      source_sha256=hashes, model_accepted_parent=False)
    return binding, artifacts, sources, provenance


def replay_control(project, case_id, repo=DEFAULT_REPO):
    binding, artifacts, sources, provenance = control_material(project, case_id, repo)
    extraction = n.audit_native(binding, artifacts, sources, analyst_source_sha256=provenance["source_sha256"])
    entry, observed = provenance["expected"], provenance["reviewed_observation"]
    outcomes = {}
    for row in extraction["rows"]:
        key = row["name"] if project == "dafny-vmc" else n.compact(row["identity"])
        outcomes.setdefault(key, []).append(row["status"])
    named = {key: outcomes.get(key, []) for key in entry["required_new_inventory"]}
    required = b.read_json(artifacts["scope.json"])["required_inventory"]
    missing = {key: dict(expected=count, observed=extraction["inventory"].get(key, 0))
               for key, count in required.items() if extraction["inventory"].get(key, 0) != count}
    n.require(extraction["inventory"] == observed["actual_inventory"] and named == observed["named_new_outcomes"] and
              missing == observed["missing_or_count_changed_required"] and
              b.canonical(extraction["native_flags"]) == b.canonical(observed["native_observation"]) and
              extraction["coverage_complete"] == observed["required_workspace_coverage"] and
              extraction["qualified_pass"] == observed["whole_workspace_proof_pass"] and
              extraction["warning_review"] == observed["warning_review"] and observed["expectation_match"] is True,
              "New native replay disagrees with independently reviewed control observation")
    n.require(all(named[key] == ([] if result == "Missing" else [result] * entry["required_new_inventory"][key])
                  for key, result in entry["expected_new_outcomes"].items()), "Named native control expectation differs")
    return dict(status="REVIEWED_ANALYST_CONTROL_REPLAY_PASSED", project=project, case=case_id,
                stage=binding.stage, eligible_as_accepted_stage_one=False, model_generated_growth=False,
                expected_kind=entry["expected_kind"], named_new_outcomes=named, missing_required=missing,
                unproved_parent_observation=observed["unproved_parent_observation"],
                provenance=provenance, extraction=extraction)


def _reject_known_analyst(native, metadata):
    """Labels cannot turn known actual analyst raw evidence into model evidence."""
    n.require(isinstance(native, NativeBinding), "Native binding required")
    bound = b.read_json(metadata["bound-record.json"])
    fingerprint = b.sha(b.canonical(sorted(bound.get("raw_sha256", {}).values())))
    for known in _catalog()["known_analyst_native_evidence"]:
        if known["project"] != native.project:
            continue
        n.require(native.run_id != known["run_id"] and bound.get("run_id") != known["run_id"] and
                  b.sha(metadata["bound-record.json"]) != known["bound_sha256"] and
                  b.sha(metadata["record.json"]) != known["record_sha256"] and
                  fingerprint != known["native_raw_fingerprint_sha256"],
                  "Known analyst native evidence cannot be relabeled as a model parent")


def audit_model_parent_native(native, metadata, sources, *, repo=DEFAULT_REPO, allow_synthetic=False):
    """Prospective source/native audit only; never issues acceptance.

    Synthetic fixtures use the same reviewed scope and body rules, but are
    permitted solely by an explicit test opt-in and remain visibly synthetic.
    """
    n.require(isinstance(native, NativeBinding) and native.stage == 1, "Separate stage-one native evidence required")
    n.require(native.origin == "model-candidate" or (allow_synthetic and native.origin == "synthetic-offline"),
              "Analyst or synthetic native evidence is not a model parent")
    _reject_known_analyst(native, metadata)
    descriptor = stage_one_scope(native.project, repo)
    n.require(b.sha(metadata["qualification-gate.json"]) == descriptor["qualification_gate_sha256"],
              "Candidate must use the actual externally reviewed stage-one qualification gate")
    scope, profile, record, tools = (b.read_json(metadata[name]) for name in
                                    ("scope.json", "profile.json", "record.json", "tools-before.json"))
    if any(x.get("synthetic_offline_fixture") is True for x in (profile, record, b.read_json(metadata["bound-record.json"]))):
        n.require(allow_synthetic and native.origin == "synthetic-offline",
                  "Marked synthetic native fixture cannot be relabeled as model evidence")
    n.exact(scope, {key: descriptor[key] for key in ("project", "stage", "readiness", "required_inventory",
                                                   "upstream_warnings", "warning_policy_sha256", "logical_command",
                                                   "toolchain", "tools_record_sha256")})
    n.require(profile.get("logical_command") == descriptor["logical_command"] and
              profile.get("toolchain") == descriptor["toolchain"] and
              _normalize_command(native.project, record.get("command")) == descriptor["command_template"],
              "Candidate native command/tool environment differs from reviewed stage-one scope")
    n.require(all(profile.get("resources", {}).get(k) == v for k, v in descriptor["resources"].items()),
              "Candidate resource/concurrency limits differ from qualification")
    n.require(b.sha(b.canonical(tools)) == descriptor["tools_record_sha256"], "Candidate tool closure differs")
    if native.project == "vest":
        n.exact(scope, dict(verus_metadata=descriptor["verus_metadata"]))
    unlogged = scope.get("unlogged_definitions", [])
    n.require([{k: x.get(k) for k in ("file", "unit", "counted_as_pass")} for x in unlogged] ==
              descriptor["fixed_unlogged_units"], "Candidate fixed unlogged-definition scope differs")
    extraction = n.audit_native(native, metadata, sources, allow_synthetic=allow_synthetic)
    extraction["host_scope_sha256"] = b.sha(b.canonical(descriptor))
    extraction["known_analyst_native_reuse_rejected"] = True
    return extraction


def validate_accepted_parent(child_stage_id, chain_id, sources, binding, artifacts, *,
                             allow_synthetic=False, repo=DEFAULT_REPO):
    stage, _, _ = b.stage_spec(child_stage_id)
    n.require(stage["stage"] == 2 and isinstance(binding, AcceptedParentBinding),
              "Stage two requires a host-pinned accepted-parent record")
    native = binding.native
    n.require(isinstance(native, NativeBinding) and native.project == stage["project"] and native.stage == 1,
              "A full-stage reference cannot become an accepted stage-one parent")
    n.require(binding.chain_id == chain_id and isinstance(chain_id, str) and b.IDENTITY.fullmatch(chain_id),
              "Accepted-parent lineage differs")
    n.require(isinstance(artifacts, dict) and {"accepted.json", "native-units.json"} <= set(artifacts),
              "Complete accepted-parent and native extraction artifacts required")
    n.require(b.sha(artifacts["accepted.json"]) == binding.receipt_sha256 and
              b.sha(artifacts["native-units.json"]) == binding.extraction_sha256,
              "Accepted-parent receipt/extraction changed")
    metadata = {name: raw for name, raw in artifacts.items() if name not in ("accepted.json", "native-units.json")}
    extraction = audit_model_parent_native(native, metadata, sources, repo=repo, allow_synthetic=allow_synthetic)
    n.require(extraction["qualified_pass"], "Failed, incomplete or unproved stage-one parent cannot advance")
    n.require(b.canonical(extraction) == artifacts["native-units.json"], "Derived native evidence is stale or substituted")
    receipt = b.read_json(artifacts["accepted.json"])
    n.exact(receipt, dict(schema="repodisco-growth-host-accepted-stage-one-v3", status="accepted", stage=1,
                          project=native.project, chain_id=chain_id, run_id=native.run_id,
                          origin=native.origin, source_revision_sha256=native.source_revision_sha256,
                          source_sha256=b.source_hashes(sources), policy_sha256=b.policy_digest(),
                          native_binding_sha256=b.sha(b.canonical(asdict(native))),
                          native_extraction_sha256=binding.extraction_sha256,
                          qualification_gate_sha256=b.sha(metadata["qualification-gate.json"]),
                          host_scope_sha256=extraction["host_scope_sha256"]))
    return dict(parent_run_id=native.run_id, parent_revision_sha256=native.source_revision_sha256,
                native_binding_sha256=b.sha(b.canonical(asdict(native))), extraction_sha256=binding.extraction_sha256,
                host_scope_sha256=extraction["host_scope_sha256"], origin=native.origin,
                evidence_replayed=True, acceptance_created_here=False, host_authenticity_established_here=False,
                native_calls_made=0, synthetic_fixture=native.origin == "synthetic-offline")
