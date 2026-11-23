"""Construct the explicit effect-frame/proof revision; never invoke Dafny or a model."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PRIOR = REPO / "experiments/dafny-real-library-growth-001"
ORIGINAL = HERE.parent
FAILED = ORIGINAL.parent / "qualification-001/retrieved-stdlib/qualification-001/output-stdlib"
ORIGINAL_MANIFEST_SHA = "e979b605b1b908a7348e2c81c37e6d88f0000fba029d195aa3542a60ee7c403d"
PARENT = PRIOR / "execution-001/retrieved-001/model-001/slots/slot-01"
BASE_FILES = [
    "Source/DafnyStandardLibraries/src/Std/BoundedInts.dfy",
    "Source/DafnyStandardLibraries/src/Std/Wrappers.dfy",
    "Source/DafnyStandardLibraries/src/Std/DynamicArray.dfy",
]
APPEND = "growth/AppendAll.dfy"
EXPECTED = {
    BASE_FILES[0]: "4e209a0662b475a9cef4c78536f197f2d122cdba4278e243a773b5c69ab30fb4",
    BASE_FILES[1]: "b0db6d1cfce218f358e01e0eed52fba5246f8b64e9b5113d8187620903dc4c08",
    BASE_FILES[2]: "a55ebe2b2ba78856fb036689e852ac06ba3b6d3fad52619aed1b58dd6d7eeae7",
    APPEND: "f80de476f36e56198d9fcf944b2b0749a28fe76a7a26efa0239e374a1cf54a26",
}
BEGIN, END = "    // BEGIN REPLACEMENT\n", "    // END REPLACEMENT"
TASKS = {
    "stdlib-filter": dict(stage_id="stable-filter-below", template="StableFilterBelow.dfy",
        path="growth/StableFilterBelow.dfy", target="RepoDiscoStableFilter.StableFilterBelow",
        helper_declarations=["RepoDiscoStableFilter.KeepBelow"], bases=BASE_FILES),
    "stdlib-splice": dict(stage_id="splice-range", template="SpliceRange.dfy",
        path="growth/SpliceRange.dfy", target="RepoDiscoSplice.Splice",
        helper_declarations=[], bases=BASE_FILES + [APPEND]),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError("Preserve existing construction output: " + str(path))
    path.write_bytes(raw)


def save(path, value):
    write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Mutation must select exactly one body fragment: " + old)
    return text.replace(old, new, 1)


def render(template, body):
    prefix, suffix = template.split(BEGIN, 1)
    blank, suffix = suffix.split(END, 1)
    if blank.strip():
        raise ValueError("Template body is not empty")
    return (prefix + BEGIN + body + ("" if body.endswith("\n") else "\n") + END + suffix).encode()


def variants():
    filter_ref = (HERE / "bodies/filter-reference.txt").read_text()
    splice_ref = (HERE / "bodies/splice-reference.txt").read_text()
    return [
        ("filter-reference", "stdlib-filter", filter_ref, "PROOF_PASS", "Two-cursor stable compaction followed by tail pops."),
        ("filter-alternative", "stdlib-filter", (HERE / "bodies/filter-alternative.txt").read_text(), "PROOF_PASS", "Recursive pop/filter/reappend alternative; efficient shifting is not required by the contract."),
        ("filter-empty", "stdlib-filter", "    removed := 0;\n", "PROOF_FAILURE", "No filtering; [2] at limit 2 must become []."),
        ("filter-inclusive-threshold", "stdlib-filter", replace_once(filter_ref, "      if value < limit {", "      if value <= limit {"), "PROOF_FAILURE", "Incorrectly keeps an element equal to the strict threshold."),
        ("filter-no-tail-pop", "stdlib-filter", replace_once(filter_ref, "while a.size > write", "while a.size > originalSize"), "PROOF_FAILURE", "Compaction leaves the discarded tail present."),
        ("filter-wrong-write-index", "stdlib-filter", replace_once(filter_ref, "a.Put(write, value);", "a.Put(read, value);"), "PROOF_FAILURE", "Does not close gaps; [5,1] at limit 3 must become [1]."),
        ("filter-missing-prefix-invariant", "stdlib-filter", replace_once(filter_ref, "      invariant a.items[..write] == KeepBelow(original[..read], limit)\n", ""), "PROOF_FAILURE", "Omits the accumulated stable-prefix proof invariant; semantic algorithm remains the same."),
        ("filter-omitted", "stdlib-filter", "    removed := 0;\n", "COVERAGE_OMISSION", "Stages the exact failing empty body but omits its file from native roots."),
        ("splice-reference", "stdlib-splice", splice_ref, "PROOF_PASS", "Grow with accepted AppendAll, shift overlapping suffix in the safe direction, fill replacement, shrink tail."),
        ("splice-alternative", "stdlib-splice", (HERE / "bodies/splice-alternative.txt").read_text(), "PROOF_PASS", "Snapshot/rebuild through accepted AppendAll; overlap handling is not a necessary solution form."),
        ("splice-empty", "stdlib-splice", "    return;\n", "PROOF_FAILURE", "Does not implement the requested range edit."),
        ("splice-growth-wrong-order", "stdlib-splice", replace_once(splice_ref, "var sourceIndex := sourceStart + remaining;", "var sourceIndex := sourceStart + (suffixCount - 1 - remaining);"), "PROOF_FAILURE", "Uses forward source order with backward destinations in the growth branch."),
        ("splice-wrong-replacement-offset", "stdlib-splice", replace_once(splice_ref, "a.Put(position + index, replacement[index]);", "a.Put(index, replacement[index]);"), "PROOF_FAILURE", "Overwrites the preserved prefix when position is positive."),
        ("splice-no-tail-pop", "stdlib-splice", replace_once(splice_ref, "while a.size > targetSize", "while a.size > workingSize"), "PROOF_FAILURE", "Leaves extra elements when deletion exceeds insertion."),
        ("splice-missing-growth-call", "stdlib-splice", replace_once(splice_ref, "      Append.AppendAll(a, replacement[..growth]);\n", ""), "PROOF_FAILURE", "Does not establish the larger size before right-shift accesses."),
        ("splice-unproved-seed", "stdlib-splice", splice_ref, "PROOF_FAILURE", "Native-only trust control: accepted seed body replaced by return; seed contract unchanged. Ineligible under the model edit guard."),
        ("splice-omitted", "stdlib-splice", "    return;\n", "COVERAGE_OMISSION", "Stages the exact failing empty body but omits its file from native roots."),
    ]


def revision_metadata(destination):
    """Pin the original failed observations without copying or changing them."""
    original_manifest = ORIGINAL / "manifest.json"
    if sha(original_manifest.read_bytes()) != ORIGINAL_MANIFEST_SHA:
        raise ValueError("Original fixture manifest changed")
    old_files = json.loads(original_manifest.read_bytes())["files"]
    for name, expected in old_files.items():
        if sha((ORIGINAL / name).read_bytes()) != expected:
            raise ValueError("Original frozen fixture changed: " + name)
    original_cases = {item["id"]:item for item in json.loads((ORIGINAL / "cases.json").read_bytes())}
    pins = {original_manifest.relative_to(REPO).as_posix(): ORIGINAL_MANIFEST_SHA}
    observations = []
    for cid in ("filter-reference", "splice-reference"):
        folder = FAILED / cid
        record = json.loads((folder / "record.json").read_bytes())
        expected_sources = original_cases[cid]["source_sha256"]
        if record["exit_code"] != 4 or record["timeout"]:
            raise ValueError("Expected preserved ordinary failure record")
        if record["source_before_sha256"] != expected_sources or record["source_after_sha256"] != expected_sources:
            raise ValueError("Original failed source identity differs")
        if record["argv"] != original_cases[cid]["argv"]:
            raise ValueError("Original failed command identity differs")
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                pins[p.relative_to(REPO).as_posix()] = sha(p.read_bytes())
        text = (folder / "raw/stdout.txt").read_text()
        observations.append(dict(case_id=cid, run_id=record["run_id"], exit_code=record["exit_code"],
            diagnostic_count=text.count(": Error:"), source_sha256=expected_sources,
            record_path=(folder / "record.json").relative_to(REPO).as_posix(),
            status="PRESERVED_NATIVE_PROOF_FAILURE"))
    diffs = []
    for task in TASKS.values():
        name = "templates/" + task["template"]
        before, after = (ORIGINAL / name).read_text(), (HERE / name).read_text()
        if after != before.replace("    reads a, a.Repr\n    modifies a.Repr\n",
                                   "    reads *\n    modifies a, a.Repr\n", 1):
            raise ValueError("Unexpected protected-template delta")
        diffs.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                     fromfile="stdlib/" + name, tofile="stdlib/revision-002/" + name))
    write(destination / "header-diff.patch", "".join(diffs).encode())
    save(destination / "revision.json", dict(schema="dafny-library-harder-stdlib-revision-v2",
        prior_manifest_sha256=ORIGINAL_MANIFEST_SHA, preserved_input_pins=pins,
        failed_observations=observations,
        protected_header_delta={"reads": ["a, a.Repr", "*"], "modifies": ["a.Repr", "a, a.Repr"]},
        unchanged="All functional preconditions/postconditions, types, helper definitions, imports, exports, upstream and accepted-seed bytes, tool flags and limits.",
        frame_rationale="Exported PopFast has no explicit reads clause and modifies the object size/items fields. Opaque Valid? does not expose object membership in Repr. The new effect frame matches these API permissions without adding caller preconditions.",
        body_revision="Explicit loop frames and allocation freshness, natural-number slice counters/bounds, sequence-prefix and update equalities.",
        actual_v2_native_status="UNKNOWN", model_calls=0, native_calls=0))


def build(destination=HERE):
    destination = Path(destination).resolve()
    if (destination / "cases.json").exists():
        raise ValueError("Construction already exists; use a separate revision")
    revision_metadata(destination)
    base = {name: (PARENT / "candidate" / name).read_bytes() for name in EXPECTED}
    if {name: sha(raw) for name, raw in base.items()} != EXPECTED:
        raise ValueError("Accepted base source pins differ")
    prior_profile_path = PRIOR / "native-profiles/stdlib-002/stage0.json"
    prior_profile = json.loads(prior_profile_path.read_bytes())
    if sha(prior_profile_path.read_bytes()) != "46867dbadd5d9d9c40bfe2b4dce99741fe097dd4b35f10b3b77b42d209b667b4":
        raise ValueError("Qualified command origin differs")
    command_prefix = prior_profile["command"][:-len(prior_profile["verification_inputs"])]
    receipt = json.loads((PARENT / "parent-receipt.json").read_bytes())
    if receipt["origin"] != "model_candidate" or receipt["synthetic"] or not receipt["accepted"]:
        raise ValueError("Seed is not a saved accepted model addition")
    if receipt["source_revision_sha256"] != sha(canonical(EXPECTED)):
        raise ValueError("Seed receipt does not bind the complete base")
    origins = {
        "schema": "dafny-library-harder-stdlib-origins-v2",
        "sources": {name: dict(path=(PARENT / "candidate" / name).relative_to(REPO).as_posix(), sha256=EXPECTED[name]) for name in EXPECTED},
        "accepted_seed": dict(path=APPEND, slot_id="slot-01", project="stdlib", prior_chain_id=receipt["chain_id"],
                             request_id=receipt["request_id"], role="Immutable prior accepted source; not a dynamic current-run parent."),
        "evidence_pins": {},
        "command_origin": dict(path=prior_profile_path.relative_to(REPO).as_posix(), sha256=sha(prior_profile_path.read_bytes())),
        "guard_dependency_pins": {},
    }
    for name in ("parent-receipt.json", "response-binding.json", "native/record.json", "native-review.json"):
        p = PARENT / name
        origins["evidence_pins"][p.relative_to(REPO).as_posix()] = sha(p.read_bytes())
    for name in ("guard.py", "review_native.py"):
        p = PRIOR / "common" / name
        origins["guard_dependency_pins"][p.relative_to(REPO).as_posix()] = sha(p.read_bytes())
    for name, raw in base.items():
        write(destination / "base" / name, raw)
    license_source = PRIOR / "stdlib/upstream/LICENSE.txt"
    write(destination / "LICENSE.txt", license_source.read_bytes())
    origins["license_origin"] = dict(path=license_source.relative_to(REPO).as_posix(), sha256=sha(license_source.read_bytes()))
    save(destination / "origin-pins.json", origins)
    profiles = {}
    for project, task in TASKS.items():
        template = (HERE / "templates" / task["template"]).read_text()
        profile = dict(schema="dafny-library-edit-profile-v1", project=project, stage=1, stage_id=task["stage_id"],
            base_source_sha256={name: EXPECTED[name] for name in task["bases"]},
            addition=dict(path=task["path"], template_utf8=template, begin_marker=BEGIN, end_marker=END, kind="method"),
            registrations={}, verification_inputs=task["bases"] + [task["path"]], forbidden_identifiers=[], parent_requirement=None)
        save(destination / "profiles" / (project + ".json"), profile)
        profiles[project] = profile
    cases = []
    for cid, project, body, expected, purpose in variants():
        task, profile = TASKS[project], profiles[project]
        sources = {name: base[name] for name in task["bases"]}
        sources[task["path"]] = render(profile["addition"]["template_utf8"], body)
        invalid_seed = cid == "splice-unproved-seed"
        if invalid_seed:
            before, after = sources[APPEND].decode().split(BEGIN, 1)
            _, after = after.split(END, 1)
            sources[APPEND] = (before + BEGIN + "    return;\n" + END + after).encode()
        omitted = [task["path"]] if expected == "COVERAGE_OMISSION" else []
        roots = [name for name in profile["verification_inputs"] if name not in omitted]
        workspace = "cases/" + cid + "/workspace"
        for name, raw in sources.items():
            write(destination / workspace / name, raw)
        seed_target = "RepoDiscoStdAppend.AppendAll"
        required = ([seed_target] if project == "stdlib-splice" else []) + task["helper_declarations"] + [task["target"]]
        failed = [seed_target if invalid_seed else task["target"]] if expected == "PROOF_FAILURE" else []
        passed = ([seed_target] if project == "stdlib-splice" and not invalid_seed else []) + ([task["target"]] if expected == "PROOF_PASS" else [])
        cases.append(dict(id=cid, task_id=project, project=project, stage=1, stage_id=task["stage_id"],
            workspace_dir=workspace, source_sha256={name: sha(raw) for name, raw in sorted(sources.items())},
            declared_scope_files=profile["verification_inputs"], command_files=roots, argv=command_prefix + roots,
            required_targets=required, expected_category=expected,
            expected_native_category="PROOF_PASS" if omitted else expected,
            expected_failed_targets=failed, expected_passed_targets=passed,
            inspect_targets=[task["target"]] if invalid_seed else [],
            omit_from_command=omitted, omitted_targets=[task["target"]] if omitted else [],
            omitted_source_all_units=omitted, body_sha256=sha(body.encode()), control_purpose=purpose,
            analyst_authored=True, model_acceptance=False, native_status="UNKNOWN",
            actual_native_unit_labels=None, native_dispatch_authorized=False,
            gated_until_positive_review=cid not in ("filter-reference", "splice-reference"),
            protected_source_candidate=not invalid_seed, coverage_complete=not omitted,
            edit_profile_path="profiles/" + project + ".json",
            classification_requires_named_units_and_exact_inventory=True))
    save(destination / "cases.json", cases)
    save(destination / "design.json", dict(schema="dafny-library-harder-stdlib-design-v2",
        projects=list(TASKS), independent_stage_one_tasks=True, dynamic_current_run_parent=False,
        fixed_previous_model_seed=APPEND, native_status="UNKNOWN", new_model_calls=0, new_native_calls=0,
        body_edit_scope="One current method body only; fixed headers, helpers, exports, upstream and accepted seed.",
        capacity_guarantee=False, effect_frame="Explicit reads * and modifies a, a.Repr; see header-diff.patch and revision.json.",
        coherence="Explicit size == |items| pre/post avoids relying on unfolding opaque Valid?.",
        duplication_audit="Pinned DynamicArray's exported API has no stable threshold filter or splice method. This is a scope-local check, not an exhaustive claim about every upstream library module.",
        alternative_limits="Recursion and snapshot/rebuild alternatives deliberately show that loop shape, overlap shifting and particular call counts are not necessary solution conditions.",
        targets={project: {k:v for k,v in task.items() if k != "bases"} for project,task in TASKS.items()}))
    files = {p.relative_to(destination).as_posix(): sha(p.read_bytes()) for p in sorted(destination.rglob("*"))
             if p.is_file() and "reviews" not in p.relative_to(destination).parts and p.name != "manifest.json"}
    save(destination / "manifest.json", dict(schema="dafny-library-harder-stdlib-manifest-v2", files=files,
        native_status="UNKNOWN", fixtures_are_analyst_controls=True, mathematical_qualification=False))
    return dict(cases=len(cases), projects=len(TASKS), initial_reference_ids=["filter-reference", "splice-reference"],
                manifest_sha256=sha((destination / "manifest.json").read_bytes()), native_calls=0, model_calls=0)


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
