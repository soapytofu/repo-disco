"""Replay the actual nine UInt-only controls; no native/model invocation."""
import copy
import json
from pathlib import Path
import re

from build_aws import (EXPERIMENT, HERE, MODULE_FILES, REFERENCE_ROOT, SOURCE_ROOT,
                       STAGES, TARGETS, body_review, saved, native)

CONTROL_ROOT = "qualification-006/retrieved-aws/qualification-006/output-aws"


def pins(profile,record,sources,raw):
    return native.EvidencePins(native.sha(native.canonical(profile)),native.sha(native.canonical(record)),
        native.sha(native.canonical(native.hashes(sources))),tuple(sorted(native.hashes(raw).items())),
        record["run_id"],record["origin"])


def materialize(profile,sources):
    """After protected-byte review, change only whole-file unlogged SHA pins."""
    result=copy.deepcopy(profile)
    for row in result["unlogged_definitions"]:
        row["source_sha256"]=native.sha(sources[row["file"]])
    return result


def run(destination=None):
    destination=Path(destination or HERE/"aws-002").resolve()
    previous=json.loads((HERE/"aws-001/review.json").read_bytes())
    cases=[row for row in json.loads((EXPERIMENT/SOURCE_ROOT/"cases.json").read_bytes()) if row["gated_until_positive_review"]]
    native.require(len(cases)==9,"Exactly nine declared controls required")
    controls={row["id"]:saved.load_observation(CONTROL_ROOT+"/"+row["id"]) for row in cases}
    positives={name:saved.load_observation(REFERENCE_ROOT+"/"+name) for name,_,_ in STAGES}
    all_observations=list(positives.values())+list(controls.values())
    denied_runs=sorted(row[1]["run_id"] for row in all_observations)
    denied_raw=sorted(native.sha(native.canonical(native.hashes(row[3]))) for row in all_observations)
    native.require(len(set(denied_runs))==12,"Duplicate actual observation identity")
    input_files=dict(previous["input_files"])
    for path in sorted((HERE/"aws-001").rglob("*.json")):
        input_files[path.relative_to(EXPERIMENT).as_posix()]=native.sha(path.read_bytes())
    for folder,record,sources,raw in all_observations:
        for path in [folder/"record.json",*sorted((folder/"workspace").rglob("*.dfy")),
                     *[p for p in sorted((folder/"raw").rglob("*")) if p.is_file()]]:
            input_files[path.relative_to(EXPERIMENT).as_posix()]=native.sha(path.read_bytes())
    input_files["native-profiles/audit_aws_controls.py"]=native.sha(Path(__file__).read_bytes())
    destination.mkdir(parents=True,exist_ok=False)
    profiles={}
    for stage in (0,1,2):
        profile=json.loads((HERE/"aws-001"/("stage"+str(stage)+".json")).read_bytes())
        profile["ineligible_parent_runs"]=denied_runs
        profile["ineligible_parent_raw_fingerprints"]=denied_raw
        profile["negative_controls_release"]="Nine actual controls replayed; final execution release remains host-owned"
        profile["execution_release_issued"]=False
        profiles[stage]=profile
        saved.write(destination/("stage"+str(stage)+".json"),profile)
        saved.write(destination/("mapping-stage"+str(stage)+".json"),
            json.loads((HERE/"aws-001"/("mapping-stage"+str(stage)+".json")).read_bytes()))
    baseline=positives["baseline"][2]
    baseline_units=set(profiles[0]["required_units"])
    summaries=[]
    for name,stage,stage_id in STAGES:
        folder,record,sources,raw=positives[name]
        result=native.review(profiles[stage],sources,record,raw,pins(profiles[stage],record,sources,raw))
        native.require(result["qualified_success"] and result["strict_zero_warning_success"],"Prior positive observation changed")
        saved.write(destination/"replay-001"/(name+".json"),result)
        summaries.append(dict(case=name,stage=stage,run_id=record["run_id"],expected="VERIFIED",observed=result["category"],
            expected_match=True,logged_passes=result["passed_units"],model_parent_eligible=False,
            new_native_trial=False,reuse_of_saved_observation=True))
    for declared in cases:
        name,stage=declared["id"],declared["stage"]
        folder,record,sources,raw=controls[name]
        native.require(native.hashes(sources)==declared["source_sha256"],"Actual control source differs from declared fixture")
        native.require(record["argv"]==declared["argv"],"Actual control command differs from declared fixture")
        native.require(all(sources[path]==data for path,data in baseline.items()),"Control changed an original upstream file")
        checks=[]
        for number in range(1,stage+1):
            names=set(baseline)|{MODULE_FILES["RepoDiscoU16Frame"]}
            if number==2:
                names.add(MODULE_FILES["RepoDiscoFramePair"])
            checks.append(body_review(number,{path:sources[path] for path in names},baseline))
        profile=materialize(profiles[stage],sources)
        profile_path="replay-001/"+name+"-materialized-profile.json"
        saved.write(destination/profile_path,profile)
        rows=native._csv(profile,raw)
        actual={row["name"]:row["outcome"] for row in rows}
        native.require(len(actual)==len(rows),"Duplicate native row was not preserved")
        native.require(baseline_units<=set(actual) and all(actual[label]=="Passed" for label in baseline_units),
                       "Original baseline obligations missing or failed")
        failed=sorted(label for label,outcome in actual.items() if outcome!="Passed")
        required_failed=[target+" (well-formedness)" for target in declared["expected_failed_targets"]]
        inspected=[target+" (well-formedness)" for target in declared["inspect_targets"]]
        native.require(set(required_failed)<=set(failed) and set(failed)<=set(required_failed+inspected),
                       "Failure occurred outside the expected/explicitly inspected target units")
        native.require(all(actual[label]=="Failed" for label in failed),"Resource/unknown result is not a proof failure")
        native.require(all(actual[target+" (well-formedness)"]=="Passed" for target in declared["expected_passed_targets"]),
                       "Expected passing target did not pass")
        if declared["expected_category"]=="COVERAGE_OMISSION":
            expected="INPUT_COVERAGE_REJECTED"
            error=None
            try:
                native.review(profile,sources,record,raw,pins(profile,record,sources,raw))
            except native.EvidenceError as caught:
                error=str(caught)
            native.require(error=="Exact native command differs","Omitted module did not fail complete-command review")
            native.require(record["argv"]==profile["command"][:-1] and record["exit_code"]==0 and not record["timeout"],
                           "Unexpected omission command/native state")
            summary=native.SUMMARY.findall(raw["stdout.txt"].decode())
            native.require(len(summary)==1 and int(summary[0][0])==len(actual) and int(summary[0][1])==0,
                           "Omission summary/inventory differs")
            native.require(not re.search(r"\bWarning\s*:|\bError\s*:",raw["stdout.txt"].decode()+raw["stderr.txt"].decode()),
                           "Unexpected omission diagnostics")
            native.require(record["toolchain"]==profile["toolchain"],"Omission toolchain differs")
            missing=sorted(set(profile["required_units"])-set(actual))
            native.require(missing==["RepoDiscoFramePair.HasFramePair (well-formedness)",TARGETS[2]],
                           "Omission does not identify the exact excluded function/spec source")
            native.require(sources==controls["stage2-always-failure"][2],"Omitted source is not the exact tested failing workspace")
            result=dict(schema="dafny-library-omission-control-review-v1",category=expected,qualified_success=False,
                proof_coverage_complete=False,reviewer_exception=error,run_id=record["run_id"],origin=record["origin"],
                exit_code=record["exit_code"],actual_native_verified=len(actual),actual_native_errors=0,
                units=rows,missing_named_units=missing,omitted_source=MODULE_FILES["RepoDiscoFramePair"],
                actual_command=record["argv"],required_full_command=profile["command"],
                source_revision_sha256=native.sha(native.canonical(native.hashes(sources))),
                same_workspace_failure_control="stage2-always-failure",exact_native_record_unchanged=True,
                profile_sha256=native.sha(native.canonical(profile)),record_sha256=native.sha(native.canonical(record)),
                resources=native._resources(raw["resources.txt"]),acceptance_issued=False)
        else:
            expected="PROOF_FAILURE"
            result=native.review(profile,sources,record,raw,pins(profile,record,sources,raw))
            native.require(result["category"]==expected and not result["qualified_success"]
                and result["warnings"]==0 and result["proof_coverage_complete"],"Unexpected proof/warning/coverage classification")
        if name=="unproved-parent-reference-child":
            native.require(actual[TARGETS[1]]=="Failed","Unproved-parent target did not fail")
            result["actual_child_outcome"]=actual[TARGETS[2]]
            result["passed_client_does_not_mask_unproved_parent"]=actual[TARGETS[2]]=="Passed"
            native.require(sources[MODULE_FILES["RepoDiscoFramePair"]]==positives["stage2-reference"][2][MODULE_FILES["RepoDiscoFramePair"]],
                           "Unproved-parent control changed the child reference body")
        result.update(fixed_source_contract_checks=checks,materialized_profile_path=profile_path,
            materialized_unlogged_fields_only=True,analyst_control_not_model_parent=True)
        saved.write(destination/"replay-001"/(name+".json"),result)
        summaries.append(dict(case=name,stage=stage,run_id=record["run_id"],expected=expected,observed=result["category"],
            expected_match=True,logged_passes=sum(outcome=="Passed" for outcome in actual.values()),failed_units=failed,
            missing_units=result.get("missing_named_units",[]),qualified_success=False,model_parent_eligible=False,
            actual_child_outcome=result.get("actual_child_outcome"),actual_saved_observation_replayed=True,new_native_trial=False))
    summary=dict(schema="dafny-library-native-control-gate-v1",project="aws",status="TWELVE_EXPECTED_OBSERVATIONS_MATCH",
        observations=summaries,counts=dict(total_expected=12,total_matching=12,reused_positive_observations=3,
            new_control_observations=9,ordinary_proof_failures=8,exit_zero_omissions_rejected=1),
        profiles={str(stage):dict(path="stage"+str(stage)+".json",canonical_sha256=native.sha(native.canonical(profile)),
            file_sha256=native.sha((destination/("stage"+str(stage)+".json")).read_bytes())) for stage,profile in profiles.items()},
        input_files=input_files,previous_positive_review_sha256=native.sha((HERE/"aws-001/review.json").read_bytes()),
        new_native_calls=0,model_calls=0,execution_release_issued=False,
        independent_control_mapping_review="pending root review",unlogged_definition_counts={str(n):len(p["unlogged_definitions"]) for n,p in profiles.items()},
        actual_function_contract_units=TARGETS,source_scope="UInt-only: three original files, then one/two executable additions; no UTF8/context or whole-MPL claim")
    saved.write(destination/"control-gate.json",summary)
    print(json.dumps({key:summary[key] for key in ("status","counts","observations","new_native_calls","model_calls","execution_release_issued")},indent=2))
    return summary


if __name__=="__main__":
    run()
