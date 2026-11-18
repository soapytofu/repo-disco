"""TEST ONLY. Fabricated native evidence, never a real accepted revision.

The positive branch is synthetic and rejected by production defaults. This file
must not be used by a live host, copied into a paid runner or shown to a model.
"""
from dataclasses import asdict
from collections import defaultdict
import csv
import io
import json

import integration as p

b, n = p.b, p.n


def repin(native, metadata, *, run_id=None, origin=None, sources=None):
    """TEST ONLY: changing pins does not create trusted-host authority."""
    return p.NativeBinding(native.project, native.stage, origin or native.origin, run_id or native.run_id,
                           b.digest_map(b.source_hashes(sources)) if sources is not None else native.source_revision_sha256,
                           b.policy_digest(), tuple(sorted(b.source_hashes(metadata).items())))


def synthetic_parent(project="dafny-vmc", *, chain_id="synthetic-lineage", body=None, failed=False,
                     repo=p.DEFAULT_REPO):
    """Return binding, artifacts, sources for explicit allow_synthetic=True tests.

    Native rows are fabricated from the reviewed inventory, never borrowed from
    a saved analyst native stream. The alternative source is NOT claimed proved
    by this fixture. It is only used to exercise exact-parent reconstruction.
    """
    descriptor = p.stage_one_scope(project, repo)
    case = "move-alternative" if project == "dafny-vmc" else "frame-alternative"
    _, _, sources, _ = p.control_material(project, case, repo)
    stage_id = p.STAGES[project][0]
    stage, _, _ = b.stage_spec(stage_id)
    if body is not None:
        sources[stage["path"]] = b.render_source(stage_id, body)[0]
    hashes = b.check_workspace(project, 1, sources)
    run_id = "SYNTHETIC-ONLY:" + chain_id
    command = [x.replace("<WORKSPACE>", "/synthetic/" + chain_id).replace("<FRESH_TARGET>", "/synthetic/target/" + chain_id)
               for x in descriptor["command_template"]]
    profile = dict(project=project, source_sha256=hashes, logical_command=descriptor["logical_command"],
                   toolchain=descriptor["toolchain"], resources=descriptor["resources"],
                   synthetic_offline_fixture=True, model_calls=0)
    _, item, data, gate, _, _, _ = p._project(project, repo)
    ref = item["reference_case"]
    _, _, case_data, _, _, _, _, _ = p._case_bytes(project, ref, repo)
    case_root = next(x["root"] for x in item["cases"] if x["id"] == ref)
    tools_raw = case_data[case_root + "/tools-before.json"]
    count = sum(descriptor["required_inventory"].values())
    if project == "dafny-vmc":
        csvbuf = io.StringIO(newline="")
        writer = csv.writer(csvbuf)
        writer.writerow(["TestResult.DisplayName", "TestResult.Outcome", "TestResult.Duration", "TestResult.ResourceCount"])
        for name in sorted(descriptor["required_inventory"]):
            bad = failed and name == "RepoDiscoGrowthShift.MoveToFront (well-formedness)"
            writer.writerow([name, "Failed" if bad else "Passed", "00:00:00", "0"])
        text = "SYNTHETIC TEST OUTPUT; NO VERIFIER WAS RUN\n" + "\n".join(descriptor["upstream_warnings"]) + "\n"
        text += f"Dafny program verifier finished with {count - int(failed)} verified, {int(failed)} errors\n"
        raw = {"stdout.txt": text.encode(), "stderr.txt": b"", "resources.txt": b"SYNTHETIC TEST RESOURCES\n",
               "csv/synthetic-only.csv": csvbuf.getvalue().encode()}
        exit_code = 4 if failed else 0
    else:
        groups = defaultdict(lambda: defaultdict(list))
        for key, occurrences in descriptor["required_inventory"].items():
            crate, module, label, mode = json.loads(key)
            bad = failed and label == "vest_dev::formats::growth_frame::frame_roundtrip"
            for _ in range(occurrences):
                groups[crate][module].append(dict(function=label, **{"mode:": mode}, success=not bad,
                                                   synthetic_test_fixture=True))
        reports = []
        summary_counts = {"vstd": 2102, "vest_lib": 3279, "vest_dev": 341}
        for crate, modules in sorted(groups.items()):
            bad = failed and crate == "vest_dev"
            reports.append({"verus": descriptor["verus_metadata"]["version"],
                "verification-results": {"encountered-vir-error": False, "encountered-error": bool(bad),
                    "errors": int(bad), "verified": summary_counts[crate] - int(bad),
                    "is-verifying-entire-crate": True, "success": not bad},
                "times-ms": {"num-threads": 1, "smt": {"smt-run-module-times": [
                    {"module": module, "function-breakdown": records} for module, records in sorted(modules.items())]}}})
        stdout = "SYNTHETIC TEST OUTPUT; NO VERIFIER WAS RUN\n" + "\n".join(json.dumps(r, sort_keys=True) for r in reports) + "\n"
        stderr = "\n\n".join(descriptor["upstream_warnings"]) + "\n\n"
        raw = {"stdout.txt": stdout.encode(), "stderr.txt": stderr.encode(), "resources.txt": b"SYNTHETIC TEST RESOURCES\n"}
        exit_code = 101 if failed else 0
    record = dict(command=command, cwd="/synthetic", model_calls=0, attempts=1, timeout=False,
                  exit_code=exit_code, elapsed_seconds=1.0, synthetic_offline_fixture=True,
                  artifacts={name: b.sha(raw[name]) for name in ("stdout.txt", "stderr.txt", "resources.txt")})
    bound = dict(run_id=run_id, project=project, profile_sha256=b.sha(b.canonical(profile)),
                 source_sha256=hashes, source_after_sha256=hashes, logical_command=profile["logical_command"],
                 toolchain=profile["toolchain"], raw_sha256=b.source_hashes(raw), exit_code=exit_code,
                 elapsed_seconds=1.0, attempts=1, model_calls=0, synthetic_offline_fixture=True)
    scope = dict(schema="repodisco-native-growth-scope-v2", project=project, stage=1,
                 qualification_gate_sha256=descriptor["qualification_gate_sha256"],
                 command_sha256=b.sha(b.canonical(command)), readiness=descriptor["readiness"],
                 logical_command=descriptor["logical_command"], toolchain=descriptor["toolchain"],
                 tools_record_sha256=descriptor["tools_record_sha256"], required_inventory=descriptor["required_inventory"],
                 upstream_warnings=descriptor["upstream_warnings"], warning_policy_sha256=descriptor["warning_policy_sha256"],
                 unlogged_definitions=[dict(x, source_sha256=hashes[x["file"]]) for x in descriptor["fixed_unlogged_units"]])
    if project == "vest":
        scope["verus_metadata"] = descriptor["verus_metadata"]
    metadata = {**raw, "scope.json": b.canonical(scope), "qualification-gate.json": data[item["gate"]],
                "profile.json": b.canonical(profile), "bound-record.json": b.canonical(bound),
                "record.json": b.canonical(record), "tools-before.json": tools_raw, "tools-after.json": tools_raw}
    native = p.NativeBinding(project, 1, "synthetic-offline", run_id, b.digest_map(hashes), b.policy_digest(),
                             tuple(sorted(b.source_hashes(metadata).items())))
    extraction = p.audit_model_parent_native(native, metadata, sources, allow_synthetic=True, repo=repo)
    extraction_raw = b.canonical(extraction)
    receipt = dict(schema="repodisco-growth-host-accepted-stage-one-v3", status="accepted", project=project,
                   stage=1, chain_id=chain_id, run_id=run_id, origin="synthetic-offline", synthetic_offline_fixture=True,
                   source_revision_sha256=native.source_revision_sha256, source_sha256=hashes,
                   policy_sha256=b.policy_digest(), native_binding_sha256=b.sha(b.canonical(asdict(native))),
                   native_extraction_sha256=b.sha(extraction_raw), qualification_gate_sha256=descriptor["qualification_gate_sha256"],
                   host_scope_sha256=extraction["host_scope_sha256"])
    receipt_raw = b.canonical(receipt)
    artifacts = {**metadata, "native-units.json": extraction_raw, "accepted.json": receipt_raw}
    return p.AcceptedParentBinding(native, chain_id, b.sha(receipt_raw), b.sha(extraction_raw)), artifacts, sources
