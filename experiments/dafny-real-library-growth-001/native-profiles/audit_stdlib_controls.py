"""Replay nine saved native controls and preserve the three positive scopes.

Omission observations are rejected against the original complete command;
their records/profiles are never patched into purported full-scope successes.
"""
import copy
import json
from pathlib import Path

from build_stdlib import (EXPERIMENT, HERE, BASELINE, REFERENCE_ROOT,
                         load_observation, write, guard, native)

CONTROL_ROOT="qualification-004/retrieved-stdlib/qualification-004/output-stdlib"
CASES=[
    ("append-alternative",1,"VERIFIED",[]),
    ("append-empty",1,"PROOF_FAILURE",["RepoDiscoStdAppend.AppendAll (correctness)"]),
    ("append-reverse",1,"PROOF_FAILURE",["RepoDiscoStdAppend.AppendAll (correctness)"]),
    ("rotate-direct",2,"VERIFIED",[]),
    ("rotate-empty",2,"PROOF_FAILURE",["RepoDiscoStdRotate.AppendRotated (correctness)"]),
    ("rotate-original-order",2,"PROOF_FAILURE",["RepoDiscoStdRotate.AppendRotated (correctness)"]),
    ("rotate-unproved-append",2,"PROOF_FAILURE",["RepoDiscoStdAppend.AppendAll (correctness)"]),
    ("append-omitted",1,"INPUT_COVERAGE_REJECTED",[]),
    ("rotate-omitted",2,"INPUT_COVERAGE_REJECTED",[]),
]


def pins(profile,record,sources,raw):
    return native.EvidencePins(native.sha(native.canonical(profile)),native.sha(native.canonical(record)),
        native.sha(native.canonical(native.hashes(sources))),tuple(sorted(native.hashes(raw).items())),
        record["run_id"],record["origin"])


def run(destination=None):
    destination=Path(destination or HERE/"stdlib-002").resolve()
    destination.mkdir(parents=True,exist_ok=False)
    previous=json.loads((HERE/"stdlib-001/review.json").read_bytes())
    controls={name:load_observation(CONTROL_ROOT+"/"+name) for name,_,_,_ in CASES}
    profiles={str(stage):json.loads((HERE/"stdlib-001"/("stage"+str(stage)+".json")).read_bytes())
              for stage in (0,1,2)}
    input_files=dict(previous["input_files"])
    for path in sorted((HERE/"stdlib-001").rglob("*.json")):
        input_files[path.relative_to(EXPERIMENT).as_posix()]=native.sha(path.read_bytes())
    for folder,record,sources,raw in controls.values():
        for path in [folder/"record.json",*sorted((folder/"workspace").rglob("*.dfy")),
                     *[path for path in sorted((folder/"raw").rglob("*")) if path.is_file()]]:
            input_files[path.relative_to(EXPERIMENT).as_posix()]=native.sha(path.read_bytes())
    input_files["native-profiles/audit_stdlib_controls.py"]=native.sha(Path(__file__).read_bytes())
    control_run_ids=[value[1]["run_id"] for value in controls.values()]
    control_raw_ids=[native.sha(native.canonical(native.hashes(value[3]))) for value in controls.values()]
    final_profiles={}
    for stage,profile in profiles.items():
        profile["ineligible_parent_runs"]=sorted(set(profile["ineligible_parent_runs"]+control_run_ids))
        profile["ineligible_parent_raw_fingerprints"]=sorted(set(profile["ineligible_parent_raw_fingerprints"]+control_raw_ids))
        profile["negative_controls_release"]="Nine actual controls replayed; final execution release remains host-owned"
        profile["execution_release_issued"]=False
        final_profiles[stage]=profile
        write(destination/("stage"+stage+".json"),profile)
        mapping=json.loads((HERE/"stdlib-001"/("mapping-stage"+stage+".json")).read_bytes())
        for definition in mapping["definitions"]:
            definition["has_logged_units"]=definition.pop("counted_as_pass")
        mapping["interpretation"]="Definitions identify source ownership. Only individual named CSV observations contribute logged pass counts; absent definitions are not passes."
        write(destination/("mapping-stage"+stage+".json"),mapping)
    summaries=[]
    for name,stage,path in [("baseline",0,BASELINE),("append-reference",1,REFERENCE_ROOT+"/append-reference"),
                            ("rotate-reference",2,REFERENCE_ROOT+"/rotate-reference")]:
        folder,record,sources,raw=load_observation(path)
        profile=final_profiles[str(stage)]
        result=native.review(profile,sources,record,raw,pins(profile,record,sources,raw))
        native.require(result["qualified_success"],"Previously passing observation changed")
        write(destination/"replay-001"/(name+".json"),result)
        summaries.append(dict(case=name,stage=stage,run_id=record["run_id"],observed=result["category"],
            expected="VERIFIED",expected_match=True,logged_passes=result["passed_units"],
            reuse_of_saved_observation=True,new_native_trial=False,model_parent_eligible=False))
    baseline_units=set(final_profiles["0"]["required_units"])
    baseline_hashes=load_observation(BASELINE)[1]["source_before_sha256"]
    for name,stage,expected,failed_labels in CASES:
        folder,record,sources,raw=controls[name]
        profile=final_profiles[str(stage)]
        native.require(all(native.sha(sources[path])==digest for path,digest in baseline_hashes.items()),
                       "Control mutated upstream source")
        contract_checks=[]
        for index in range(1,stage+1):
            edit=json.loads((EXPERIMENT/"pilot/draft-001/guard-profiles"/("stdlib-stage"+str(index)+".json")).read_bytes())
            prefix,suffix=guard._profile(edit)
            data=sources[edit["addition"]["path"]]
            native.require(data.startswith(prefix.encode()) and data.endswith(suffix.encode()),
                           "Control changed a protected declaration boundary")
            body=data[len(prefix.encode()):-len(suffix.encode())].decode()
            guard.check_body(body,edit["addition"]["kind"],edit["forbidden_identifiers"])
            contract_checks.append(dict(file=edit["addition"]["path"],fixed_prefix_sha256=native.sha(prefix.encode()),
                fixed_suffix_sha256=native.sha(suffix.encode()),body_sha256=native.sha(body.encode()),
                lexical_guard_admitted=True,analyst_control_not_model_parent=True))
        rows=native._csv(profile,raw)
        actual={row["name"]:row["outcome"] for row in rows}
        native.require(baseline_units<=set(actual) and all(actual[label]=="Passed" for label in baseline_units),
                       "Original baseline obligations missing/failed in control")
        actual_failed=sorted(label for label,outcome in actual.items() if outcome!="Passed")
        native.require(actual_failed==failed_labels,"Named control failure differs")
        if expected=="INPUT_COVERAGE_REJECTED":
            error=None
            try:
                native.review(profile,sources,record,raw,pins(profile,record,sources,raw))
            except native.EvidenceError as caught:
                error=str(caught)
            native.require(error=="Exact native command differs","Omission was not rejected at exact input command boundary")
            omitted_path=profile["verification_inputs"][-1]
            native.require(record["argv"]==profile["command"][:-1],"Unexpected omission command edit")
            summaries_raw=native.SUMMARY.findall(raw["stdout.txt"].decode())
            native.require(len(summaries_raw)==1 and int(summaries_raw[0][1])==0
                and int(summaries_raw[0][0])==len(actual) and record["exit_code"]==0
                and not record["timeout"],"Omission native pass observation inconsistent")
            native.require(record["toolchain"]==profile["toolchain"],"Omission tool scope differs")
            native.require(not __import__('re').search(r"\bWarning\s*:|\bError\s*:",raw["stdout.txt"].decode()+raw["stderr.txt"].decode()),
                           "Unexpected omission diagnostics")
            missing=sorted(set(profile["required_units"])-set(actual))
            native.require(missing and all(profile["required_units"][label]==omitted_path for label in missing),
                           "Omission missing labels do not identify excluded source")
            failure_case="append-empty" if stage==1 else "rotate-empty"
            native.require(sources==controls[failure_case][2],"Omitted source is not byte-identical to tested failing workspace")
            result=dict(schema="dafny-library-omission-control-review-v1",category=expected,
                qualified_success=False,proof_coverage_complete=False,reviewer_exception=error,
                run_id=record["run_id"],origin=record["origin"],exit_code=record["exit_code"],
                actual_native_verified=len(actual),actual_native_errors=0,units=rows,
                missing_named_units=missing,omitted_source=omitted_path,
                actual_command=record["argv"],required_full_command=profile["command"],
                source_revision_sha256=native.sha(native.canonical(native.hashes(sources))),
                same_workspace_failure_control=failure_case,exact_native_record_unchanged=True,
                resources=native._resources(raw["resources.txt"]),acceptance_issued=False,
                profile_sha256=native.sha(native.canonical(profile)),record_sha256=native.sha(native.canonical(record)))
        else:
            result=native.review(profile,sources,record,raw,pins(profile,record,sources,raw))
            native.require(result["category"]==expected,"Native outcome category differs")
            native.require(result["warnings"]==0 and result["proof_coverage_complete"],"Unexpected warnings/coverage")
            native.require(result["qualified_success"]==(expected=="VERIFIED"),"Control success gate differs")
        if name=="rotate-unproved-append":
            native.require(actual["RepoDiscoStdAppend.AppendAll (correctness)"]=="Failed"
                and actual["RepoDiscoStdRotate.AppendRotated (correctness)"]=="Passed"
                and actual["RepoDiscoStdRotate.AppendRotated (well-formedness)"]=="Passed",
                "Required failed-parent/passed-child observation absent")
            result["passed_client_does_not_mask_unproved_parent"]=True
        result["fixed_source_contract_checks"]=contract_checks
        write(destination/"replay-001"/(name+".json"),result)
        summaries.append(dict(case=name,stage=stage,run_id=record["run_id"],expected=expected,
            observed=result["category"],expected_match=True,logged_passes=sum(v=="Passed" for v in actual.values()),
            failed_units=actual_failed,qualified_success=result["qualified_success"],
            missing_units=result.get("missing_named_units",[]),model_parent_eligible=False,
            new_native_trial=False,actual_saved_observation_replayed=True))
    summary=dict(schema="dafny-library-native-control-gate-v1",project="stdlib",status="TWELVE_EXPECTED_OBSERVATIONS_MATCH",
        observations=summaries,counts=dict(total_expected=12,total_matching=12,new_control_observations=9,
            reused_positive_observations=3,alternative_native_successes=2,ordinary_proof_failures=5,
            exit_zero_omissions_rejected=2),profiles={stage:dict(path="stage"+stage+".json",
            canonical_sha256=native.sha(native.canonical(profile)),
            file_sha256=native.sha((destination/("stage"+stage+".json")).read_bytes()))
            for stage,profile in final_profiles.items()},input_files=input_files,
        previous_positive_review_sha256=native.sha((HERE/"stdlib-001/review.json").read_bytes()),
        excluded_prior_failures=previous["excluded_failed_references"],
        new_native_calls=0,model_calls=0,execution_release_issued=False,
        independent_control_mapping_review="pending root review",unlogged_definitions_not_counted_as_passes=44)
    write(destination/"control-gate.json",summary)
    print(json.dumps({key:summary[key] for key in ("status","counts","observations","new_native_calls","model_calls","execution_release_issued")},indent=2))
    return summary


if __name__=="__main__":
    run()
