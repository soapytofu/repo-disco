"""Prepare package-root Converse inputs from reviewed native project profiles.

This is an offline preparation step, not a release/authorization issuer. The
caller is the trusted host selecting independently reviewed qualification
artifacts. Hash-consistent JSON is not evidence that that review occurred.
Draft-001 and its source scanner remain read-only historical inputs. Final
interfaces/context are built from the exact selected, qualified source scope.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DESTINATION = "pilot/draft-002"
RENDERER = "pilot/render_v2.py"
MODEL = "global.anthropic.claude-opus-4-5-20251101-v1:0"
INFERENCE = {"temperature": 1, "maxTokens": 4096}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked(root, name):
    require(isinstance(name, str) and name and not name.startswith("/") and "\\" not in name
            and all(x not in {"", ".", ".."} for x in name.split("/")), "Unsafe preparation path")
    path = root / name
    for part in (path, *path.parents):
        if part == root:
            break
        require(not part.is_symlink(), "Preparation source symlink")
    require(path.is_file(), "Missing preparation input: " + name)
    return path


def load(root, name):
    return json.loads(checked(root, name).read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()+b"\n")


def common(root):
    for name in ("review_native", "guard"):
        path = (root / "common" / (name + ".py")).resolve()
        if name in sys.modules:
            require(Path(sys.modules[name].__file__).resolve() == path, "Mixed common module during preparation")
            continue
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules["guard"]


def native_options(profile):
    argv, inputs = profile["command"], profile["verification_inputs"]
    require(isinstance(argv, list) and len(argv) > len(inputs) + 1 and argv[1] == "verify"
            and argv[-len(inputs):] == inputs, "Native command/source order differs")
    return argv[2:-len(inputs)]


def source_helpers(root):
    """Reuse the reviewed offset-preserving scanner, never a runtime import."""
    path = checked(root, "pilot/prepare.py")
    spec = importlib.util.spec_from_file_location("library_prompt_source_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(interface, number, display, context, forbidden, native_profile, system):
    parts = ["Implement " + interface["callable_name"] + " under its fixed contract.",
             "Pinned language: " + native_profile["toolchain"]["dafny_version"] +
             "\nExact qualified verifier options (source arguments are listed in the host inventory): " +
             json.dumps(native_options(native_profile), separators=(",", ":")),
             "Current editable file: " + interface["target_file"],
             "Only the marked body is empty and editable; its contracts and all other source bytes are fixed.",
             "Host-forbidden identifier tokens: " + json.dumps(forbidden), context["context_notice"]]
    for item in context["excerpts"]:
        parts += ["Verbatim upstream source: " + item["file"] + " lines " + str(item["first_line"]) +
                  "-" + str(item["last_line"]) + " (whole-source SHA-256 " + item["source_sha256"] + ")", item["text"]]
    parts += ["Exact source include/import declarations and module names:",
              json.dumps(context["dependency_inventory"], sort_keys=True, separators=(",", ":"))]
    if number == 2:
        parts += ["Previously accepted stage-one addition from this lineage (fixed, not editable):",
                  "{{ACCEPTED_PARENT_SOURCE}}"]
    parts += ["Current new-file template; replace only the marked body:", display,
              "Return one JSON object with exactly the body string. No outer declaration braces."]
    return dict(modelId=MODEL, system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": "\n\n".join(parts)}]}],
                inferenceConfig=copy.deepcopy(INFERENCE))


def prepare(root, specification, *, allow_synthetic=False):
    """Build draft-002 once, after all declared qualification inputs exist.

    specification has projects->{stdlib,aws}->{control_gate,native_profiles,
    reference_sources,base_sources,interfaces,native_adapter}; every file
    selector is {path,sha256}. interfaces maps "1"/"2" to stage_id,
    target_file, callable_name, kind. Original upstream files are all shown.
    reference_sources pins exactly the stage-one and stage-two addition bytes
    in the reviewed native observations, not a source of prompt solutions.
    region/batch_id and execution-001/execution-binding.json are supplied by
    the root host. This step reads the exact existing budget files. Tests may
    explicitly select synthetic qualification fixtures only in isolated roots.
    """
    root = Path(root).resolve()
    require(specification.get("schema") == "dafny-library-pilot-preparation-input-v2",
            "Unsupported preparation specification")
    synthetic = specification.get("synthetic") is True
    require(not synthetic or allow_synthetic, "Synthetic preparation is rejected by default")
    require(set(specification["projects"]) == {"stdlib", "aws"}, "Both project qualifications required")
    require(isinstance(specification.get("region"), str) and specification["region"]
            and isinstance(specification.get("batch_id"), str) and specification["batch_id"],
            "Host model region and batch identity required")
    execution_binding_path = "execution-001/execution-binding.json"
    execution_binding = load(root, execution_binding_path)
    budget_path = execution_binding["budget_snapshot_input"]
    require(sha(checked(root, budget_path).read_bytes()) == execution_binding["budget_snapshot_sha256"],
            "Root's frozen cumulative budget snapshot differs")
    budget = load(root, budget_path)
    require(budget["allocations"][-1]["runtime_execution_id"] == specification["batch_id"],
            "Root's twelve-slot allocation is for a different batch")
    guard = common(root)
    helpers = source_helpers(root)
    old_root = "pilot/draft-001/"
    old_scope = load(root, old_root + "scope.json")
    old_manifest = load(root, old_root + "draft-manifest.json")
    input_pins = {"pilot/draft-001/draft-manifest.json": sha(checked(root, old_root+"draft-manifest.json").read_bytes())}
    input_pins.update({name:sha(checked(root,name).read_bytes()) for name in
                      ("pilot/prepare.py", "pilot/prepare_v2.py", RENDERER,
                       "common/guard.py", "common/review_native.py", execution_binding_path, budget_path)})
    for name, digest in old_manifest["files"].items():
        path = old_root + name
        require(sha(checked(root, path).read_bytes()) == digest, "Historical draft drift: " + name)
        input_pins[path] = digest

    def pinned(entry):
        path = checked(root, entry["path"])
        require(sha(path.read_bytes()) == entry["sha256"], "Qualification pin drift: " + entry["path"])
        input_pins[entry["path"]] = entry["sha256"]
        return path

    output = {}
    projects = {}
    reference_audits = []
    qualification_dependencies = {execution_binding_path, budget_path}
    operation_dependencies = {"execution-001/ops.py", "execution-001/model.sbatch", "execution-001/test_ops.py",
                              "pilot/test_render_v2.py"}
    for project in ("stdlib", "aws"):
        selected = specification["projects"][project]
        gate_path = pinned(selected["control_gate"])
        gate = json.loads(gate_path.read_bytes())
        counts = gate.get("counts", {})
        require(gate.get("project") == project and gate.get("model_calls") == 0
                and type(counts.get("total_expected")) is int and counts["total_expected"] > 0
                and counts.get("total_matching") == counts["total_expected"]
                and len(gate.get("observations", [])) == counts["total_expected"]
                and all(row.get("expected_match") is True for row in gate["observations"]),
                "Project has no reviewed complete native gate")
        require(bool(gate.get("synthetic")) == synthetic, "Mixed synthetic/native qualification")
        qualification_dependencies.add(selected["control_gate"]["path"])
        require(set(selected["native_profiles"]) == {"1", "2"}
                and set(selected["reference_sources"]) == {"1", "2"}
                and set(selected["interfaces"]) == {"1", "2"}, "Both stage profiles/references/interfaces required")
        bases = copy.deepcopy(selected["base_sources"])
        require(len(bases) == 3, "These two qualified scopes each have exactly three upstream source files")
        sources = {}
        for name, entry in bases.items():
            require(gate.get("input_files", {}).get(entry["path"]) == entry["sha256"],
                    "Upstream source is not bound by the reviewed control gate")
            sources[name] = pinned(entry).read_bytes()
        trust = helpers.trust_inventory(sources)
        context = dict(schema="dafny-library-context-v2", project=project,
            excerpts=[helpers.excerpt(name, raw) for name, raw in sorted(sources.items())],
            source_files=len(sources), source_bytes=sum(map(len, sources.values())),
            omitted_or_partial_source_files=[],
            context_notice="Every original upstream source in this selected dependency scope is shown verbatim below. The host preserves all of these files; all new-file declarations, imports and contracts are fixed.",
            dependency_inventory=helpers.dependency_inventory(sources))
        output[DESTINATION + "/context/" + project + ".json"] = context
        output[DESTINATION + "/context/" + project + "-inherited-trust.json"] = trust
        stages = {}
        first_edit = None
        tools = None
        for number in (1, 2):
            index = str(number)
            interface = selected["interfaces"][index]
            require(interface["kind"] in {"method", "function"}, "Unknown editable body kind")
            reference = pinned(selected["reference_sources"][index]).read_bytes()
            text = reference.decode("utf-8")
            begin, end = helpers.BEGIN, helpers.END
            require(text.count(begin) == text.count(end) == 1, "Qualified reference needs the exact host body markers")
            body_start, body_end = text.index(begin)+len(begin), text.index(end)
            require(body_start <= body_end, "Qualified reference body markers reversed")
            template = text[:body_start] + text[body_end:]
            tokens = helpers.lex(template)
            require(tokens and tokens[0][1] in {"include", "module"}, "New file's initial module/import environment differs")
            metadata_prefix = template[:tokens[0][2]]
            display = template[len(metadata_prefix):]
            declarations = helpers.declaration_headers(template)
            require(sum(row["name"] == interface["callable_name"] and row["kind"] == interface["kind"]
                        for row in declarations) == 1, "Target callable declaration differs")
            edit = dict(schema="dafny-library-edit-profile-v1", project=project, stage=number,
                stage_id=interface["stage_id"], base_source_sha256={name:sha(raw) for name,raw in sources.items()},
                addition=dict(path=interface["target_file"], template_utf8=template,
                              begin_marker=begin, end_marker=end, kind=interface["kind"]),
                registrations={}, forbidden_identifiers=trust["forbidden_identifiers"],
                parent_requirement=None if number == 1 else dict(stage_id=first_edit["stage_id"],
                    addition_path=first_edit["addition"]["path"], guard_profile_sha256=sha(canonical(first_edit))))
            native_path = pinned(selected["native_profiles"][index])
            native = json.loads(native_path.read_bytes())
            require(gate.get("profiles", {}).get(index, {}).get("file_sha256") == sha(native_path.read_bytes()),
                    "Selected native profile is not the reviewed gate profile")
            reference_entry = selected["reference_sources"][index]
            require(gate.get("input_files", {}).get(reference_entry["path"]) == reference_entry["sha256"],
                    "Qualified reference source is not bound by the control gate")
            require(native.get("schema") == "dafny-library-native-profile-v1"
                    and native.get("inventory_status") == "qualified" and native.get("project") == project
                    and native.get("stage") == number and native.get("stage_id") == edit["stage_id"],
                    "Native stage qualification differs")
            require(native.get("synthetic") is not True, "Synthetic observations cannot be a live profile")
            require(bool(native.get("qualification_fixture_only")) == synthetic,
                    "Synthetic qualification must be explicit and test-only")
            require(isinstance(native.get("ineligible_parent_runs"), list)
                    and isinstance(native.get("ineligible_parent_raw_fingerprints"), list),
                    "Known analyst evidence exclusions required")
            if tools is None:
                tools = native["toolchain"]
            require(native["toolchain"] == tools, "Project stage toolchains differ")
            native_options(native)
            edit["verification_inputs"] = copy.deepcopy(native["verification_inputs"])
            if number == 2:
                edit["parent_requirement"]["guard_profile_sha256"] = sha(canonical(first_edit))
            prefix, suffix = guard._profile(edit)
            require(reference.startswith(prefix.encode()) and reference.endswith(suffix.encode()),
                    "Qualified reference bytes differ from the guarded template")
            reference_body = reference[len(prefix.encode()):len(reference)-len(suffix.encode())].decode()
            reconstructed, _ = guard.render_body(edit, reference_body)
            require(reconstructed == reference, "Qualified reference is not exact guarded reconstruction")
            reference_audits.append(dict(project=project, stage=number,
                source_sha256=sha(reference), body_sha256=sha(reference_body.encode()),
                guard_profile_sha256=sha(canonical(edit)),
                exact_guarded_reconstruction=True, analyst_body_model_visible=False))
            if number == 1:
                first_edit = copy.deepcopy(edit)
            profile_path = DESTINATION + "/guard-profiles/" + project + "-stage" + index + ".json"
            output[profile_path] = edit
            payload = request(interface, number, display, context, trust["forbidden_identifiers"], native, helpers.SYSTEM)
            payload_path = DESTINATION + "/payloads/" + project + "-stage" + index + (".json" if number == 1 else "-template.json")
            output[payload_path] = payload
            parent_prefix = ""
            if number == 2:
                first_host = first_edit["addition"]["template_utf8"]
                parent_prefix = first_host[:helpers.lex(first_host)[0][2]]
            stages[index] = dict(stage_id=edit["stage_id"], target_file=edit["addition"]["path"],
                edit_profile=profile_path, native_profile=selected["native_profiles"][index]["path"],
                base_sources=copy.deepcopy(bases), native_adapter=copy.deepcopy(selected["native_adapter"]),
                exact_payload_path=payload_path if number == 1 else None,
                child_template_payload_path=payload_path if number == 2 else None,
                exact_live_payload=None if number == 2 else payload_path,
                parent_display_fixed_prefix_utf8=parent_prefix)
            qualification_dependencies.add(selected["native_profiles"][index]["path"])
        projects[project] = dict(stages=stages, upstream_source_files=len(bases),
                                 qualification_gate=copy.deepcopy(selected["control_gate"]))

    slots = []
    for lineage, order in enumerate((("stdlib", "aws"), ("stdlib", "aws"), ("aws", "stdlib")), 1):
        for stage in (1, 2):
            for project in order:
                chain = project + "-lineage-" + str(lineage).zfill(2)
                slots.append(dict(id="slot-" + str(len(slots)+1).zfill(2), project=project, chain_id=chain,
                    stage=stage, cohort="pilot" if lineage == 1 else "expansion",
                    maximum_requests=1, independent_context=True,
                    parent_slot_id=next((s["id"] for s in slots if s["chain_id"] == chain and s["stage"] == 1), None)))
    scope_path = DESTINATION + "/scope.json"
    inputs_path = DESTINATION + "/renderer-inputs.json"
    manifest_path = DESTINATION + "/preparation-manifest.json"
    review_path = DESTINATION + "/preparation-review.json"
    output[review_path] = dict(schema="dafny-library-pilot-preparation-review-v2", synthetic=synthetic,
        qualification_origin="synthetic_fixture_only" if synthetic else "reviewed_analyst_native_controls",
        reference_reconstruction=reference_audits, input_files=input_pins,
        model_calls=0, native_calls=0, authorization_issued=False,
        changes_from_draft001=["Use qualified explicit source argument order and rebind the parent guard digest.",
            "Use the direct Converse envelope without changing temperature/maxTokens or legitimate source/context text.",
            "Replace the stale language/options statement with the exact qualified tool version/options.",
            "Use the bounded runner's declared pilot and expansion counterbalance order.",
            "Keep child payloads deferred until actual same-lineage model/native/request evidence is supplied."],
        trust_boundary="The root host selects reviewed qualification inputs and later owns live request/native provenance. Hashes and this preparation record do not authenticate arbitrary claims.")
    runtime_inputs = sorted(set(output) | qualification_dependencies | operation_dependencies | {inputs_path, manifest_path})
    scope = dict(schema="dafny-library-growth-scope-v1", batch_id=specification["batch_id"],
        max_calls=12, pilot_slots=4, renderer=RENDERER, runtime_inputs=runtime_inputs,
        settings=dict(model_id=MODEL, region=specification["region"], inference_config=copy.deepcopy(INFERENCE)),
        projects=projects, slots=slots, execution_binding=copy.deepcopy(execution_binding),
        response_schema=copy.deepcopy(old_scope["response_schema"]),
        expansion_gate=copy.deepcopy(old_scope["expansion_gate"]), child_gate=old_scope["child_gate"],
        study_limits=copy.deepcopy(old_scope["study_limits"]), synthetic_fixture_only=synthetic,
        preparation_status="SYNTHETIC_OFFLINE_STAGING_ONLY" if synthetic else "READY_FOR_ROOT_RUNTIME_REVIEW",
        qualification_release={p:copy.deepcopy(specification["projects"][p]["control_gate"]) for p in projects},
        execution_enabled=False, authorization_issued=False)
    output[scope_path] = scope
    destination = root / DESTINATION
    require(not destination.exists(), "Never replace a prepared draft")
    destination.mkdir(parents=True, exist_ok=False)
    for name, value in output.items():
        write(root / name, value)
    renderer_pins = {name: sha(checked(root, name).read_bytes()) for name in sorted(output)}
    renderer_pins.update({name: input_pins[name] for name in qualification_dependencies})
    renderer_pins.update({entry["path"]: entry["sha256"] for p in projects.values()
                         for stage in p["stages"].values() for entry in stage["base_sources"].values()})
    renderer_pins.update({name:sha(checked(root,name).read_bytes()) for name in ("common/guard.py","common/review_native.py")})
    write(root / inputs_path, dict(schema="dafny-library-renderer-inputs-v2", scope_path=scope_path,
        files=renderer_pins, renderer_sha256=sha(checked(root, RENDERER).read_bytes()),
        synthetic_fixture_only=synthetic, authorization_issued=False))
    write(root / manifest_path, dict(schema="dafny-library-pilot-preparation-manifest-v2",
        files={name:sha(checked(root,name).read_bytes()) for name in sorted(set(output)|{inputs_path})},
        code_sha256={name:sha(checked(root,name).read_bytes()) for name in (RENDERER,"pilot/prepare_v2.py")},
        preparation_status=scope["preparation_status"], synthetic_fixture_only=synthetic,
        model_calls=0,native_calls=0,authorization_issued=False))
    return dict(scope=scope_path, manifest=manifest_path, manifest_sha256=sha((root/manifest_path).read_bytes()),
                artifacts=len(output)+2, execution_enabled=False, model_calls=0, native_calls=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--specification", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, json.loads(args.specification.read_bytes())), indent=2))
