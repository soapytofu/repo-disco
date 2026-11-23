"""Map three saved stdlib native inventories, then replay common review.

No native, provider, network or acceptance operations. The two earlier failed
references are recorded as excluded observations and ineligible parent evidence.
"""
import csv
import io
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
sys.path.insert(0,str(EXPERIMENT/"common"))
import guard
import review_native as native

BASELINE = "qualification-002/retrieved-stdlib/qualification-002/output-stdlib/baseline"
REFERENCE_ROOT = "qualification-003/retrieved-stdlib/qualification-003/output-stdlib"
PRIOR_ROOT = "qualification-002/retrieved-stdlib/qualification-002/output-stdlib"
PREFIX_FILES = {
    "Std.BoundedInts.": "Source/DafnyStandardLibraries/src/Std/BoundedInts.dfy",
    "Std.Wrappers.": "Source/DafnyStandardLibraries/src/Std/Wrappers.dfy",
    "Std.DynamicArray.": "Source/DafnyStandardLibraries/src/Std/DynamicArray.dfy",
    "RepoDiscoStdAppend.": "growth/AppendAll.dfy",
    "RepoDiscoStdRotate.": "growth/AppendRotated.dfy",
}


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x") as stream:
        json.dump(value,stream,indent=2,sort_keys=True)
        stream.write("\n")


def load_observation(relative):
    folder=EXPERIMENT/relative
    record=json.loads((folder/"record.json").read_bytes())
    sources={path.relative_to(folder/"workspace").as_posix():path.read_bytes()
             for path in sorted((folder/"workspace").rglob("*.dfy"))}
    raw={path.relative_to(folder/"raw").as_posix():path.read_bytes()
         for path in sorted((folder/"raw").rglob("*")) if path.is_file()}
    native.require(record["source_before_sha256"]==native.hashes(sources)==record["source_after_sha256"],
                   "Saved native source identity differs")
    native.require(record["raw_sha256"]==native.hashes(raw),"Saved native raw identity differs")
    native.require(record["toolchain"]==record["toolchain_after"],"Saved native tools changed")
    native.require(record["origin"]=="analyst_qualification","Unexpected saved origin")
    return folder,record,sources,raw


def declarations(sources):
    """Narrow reviewed mapping for these five source files, not a Dafny parser."""
    found=[]
    for path,raw in sources.items():
        text=raw.decode()
        module=re.findall(r"^module\s+([A-Za-z0-9_.]+)\s*\{",text,re.M)
        native.require(len(module)==1,"Expected one explicit module per mapped file")
        container=None
        for line_number,line in enumerate(text.splitlines(),1):
            # This exact source family has module members at two spaces and
            # class/datatype members at four. All mapping rows retain the line.
            match=re.match(r"^  (?:class|datatype) ([A-Za-z_][A-Za-z0-9_']*)",line)
            if match:
                container=match.group(1)
            if line=="  }":
                container=None
            kind_name=re.match(r"^(  |    )(?:(?:ghost|static) )?(const|newtype|type|function|predicate|method)\s+([A-Za-z_][A-Za-z0-9_'?]*)",line)
            constructor=re.match(r"^    constructor\(",line)
            if kind_name:
                indent,kind,name=kind_name.groups()
                owner=module[0]+("."+container if indent=="    " and container else "")
            elif constructor:
                native.require(container is not None,"Constructor container absent")
                owner,kind,name=module[0]+"."+container,"constructor","_ctor"
            else:
                continue
            full=owner+"."+name
            found.append(dict(name=full,kind=kind,file=path,line=line_number,source_line=line,
                              source_sha256=native.sha(raw)))
    native.require(len({row["name"] for row in found})==len(found),"Duplicate declaration mapping")
    return found


def inventory(sources,raw):
    rows=[]
    columns=None
    for path,data in sorted(raw.items()):
        if not path.startswith("csv/"): continue
        parsed=csv.DictReader(io.StringIO(data.decode(),newline=""),strict=True)
        native.require(tuple(parsed.fieldnames)==native.CSV_SCHEMAS[1],"Unexpected actual native CSV shape")
        columns=parsed.fieldnames
        for offset,row in enumerate(parsed,2):
            label=row["TestResult.DisplayName"]
            prefixes=[prefix for prefix in PREFIX_FILES if label.startswith(prefix)]
            native.require(len(prefixes)==1,"Unmapped/ambiguous native label: "+label)
            file=PREFIX_FILES[prefixes[0]]
            native.require(file in sources,"Logged obligation outside source scope")
            rows.append(dict(label=label,file=file,csv=path,row=offset,fields=row))
    native.require(rows and len({row["label"] for row in rows})==len(rows),"Missing/duplicate native units")
    native.require(all(row["fields"]["TestResult.Outcome"]=="Passed" for row in rows),
                   "Non-passing observation cannot define a positive native profile")
    defs=declarations(sources)
    by_name={row["name"]:row for row in defs}
    logged=set()
    for row in rows:
        name=row["label"].split(" (")[0]
        native.require(name in by_name,"Native label lacks an exact reviewed declaration: "+name)
        native.require(by_name[name]["file"]==row["file"],"Native label/declaration source disagrees")
        logged.add(name)
    unlogged=[dict(name=row["name"],file=row["file"],source_sha256=row["source_sha256"],
                   counted_as_pass=False,kind=row["kind"],line=row["line"],source_line=row["source_line"],
                   reason="No named CSV unit for this definition in the saved complete-scope observation; not a logged proof pass.")
              for row in defs if row["name"] not in logged]
    for row in defs:
        row["logged_units"]=[unit["label"] for unit in rows if unit["label"].split(" (")[0]==row["name"]]
        row["counted_as_pass"]=bool(row["logged_units"])
    native.require(set(row["file"] for row in rows)==set(sources),"A source lacks recorded obligation coverage")
    return columns,rows,defs,unlogged


def build(destination=None):
    destination=Path(destination or HERE/"stdlib-001").resolve()
    destination.mkdir(parents=True,exist_ok=False)
    specs=[("baseline",0,"baseline",BASELINE),
           ("append-reference",1,"append-all",REFERENCE_ROOT+"/append-reference"),
           ("rotate-reference",2,"append-rotated",REFERENCE_ROOT+"/rotate-reference")]
    observations={name:load_observation(path) for name,_,_,path in specs}
    excluded={name:load_observation(PRIOR_ROOT+"/"+name)
              for name in ("append-reference","rotate-reference")}
    all_known=[value for value in observations.values()]+list(excluded.values())
    denied_runs=sorted(value[1]["run_id"] for value in all_known)
    denied_raw=sorted(native.sha(native.canonical(native.hashes(value[3]))) for value in all_known)
    input_files={}
    for folder,record,sources,raw in all_known:
        for path in [folder/"record.json",*sorted((folder/"workspace").rglob("*.dfy")),
                     *[p for p in sorted((folder/"raw").rglob("*")) if p.is_file()]]:
            input_files[path.relative_to(EXPERIMENT).as_posix()]=native.sha(path.read_bytes())
    for relative in ("common/guard.py","common/review_native.py","native-profiles/build_stdlib.py",
                     "pilot/draft-001/guard-profiles/stdlib-stage1.json",
                     "pilot/draft-001/guard-profiles/stdlib-stage2.json"):
        input_files[relative]=native.sha((EXPERIMENT/relative).read_bytes())
    excluded_report=[]
    for name,(folder,record,sources,raw) in excluded.items():
        summaries=native.SUMMARY.findall(raw["stdout.txt"].decode())
        native.require(record["exit_code"]==4 and len(summaries)==1 and int(summaries[0][1])>0,
                       "Earlier failed reference status changed")
        excluded_report.append(dict(case=name,path=folder.relative_to(EXPERIMENT).as_posix(),
            run_id=record["run_id"],exit_code=record["exit_code"],qualifies=False,
            reason="Original failed source-body observation retained; not used to establish positive inventory/profile.",
            raw_fingerprint_sha256=native.sha(native.canonical(native.hashes(raw)))))
    profiles={}
    reports=[]
    baseline_source_hashes=native.hashes(observations["baseline"][2])
    prior_units=set()
    for name,stage,stage_id,path in specs:
        folder,record,sources,raw=observations[name]
        native.require(record["exit_code"]==0 and not record["timeout"],"Positive case is incomplete")
        native.require(all(native.sha(sources[file])==digest for file,digest in baseline_source_hashes.items()),
                       "Upstream source changed between stages")
        columns,rows,defs,unlogged=inventory(sources,raw)
        source_args=record["argv"][-len(sources):]
        native.require(set(source_args)==set(sources),"Actual explicit roots do not match all sources")
        profile=dict(schema=native.PROFILE_SCHEMA,project="stdlib",stage=stage,stage_id=stage_id,
            inventory_status="qualified",command=record["argv"],verification_inputs=source_args,
            toolchain=record["toolchain"],csv_columns=columns,random_seed=0,
            required_units={row["label"]:row["file"] for row in sorted(rows,key=lambda row:row["label"])},
            unitless_files={},unlogged_definitions=unlogged,inherited_warnings=[],
            ineligible_parent_runs=denied_runs,ineligible_parent_raw_fingerprints=denied_raw,
            scope_origin="actual analyst qualification observation; not a model-accepted revision",
            source_observation=dict(path=path,run_id=record["run_id"],
                record_file_sha256=native.sha((folder/"record.json").read_bytes()),
                source_revision_sha256=native.sha(native.canonical(native.hashes(sources)))),
            execution_release_issued=False,negative_controls_release="pending separate review")
        if stage:
            edit=json.loads((EXPERIMENT/"pilot/draft-001/guard-profiles"/("stdlib-stage"+str(stage)+".json")).read_bytes())
            prefix,suffix=guard._profile(edit)
            candidate=sources[edit["addition"]["path"]]
            native.require(candidate.startswith(prefix.encode()) and candidate.endswith(suffix.encode()),
                           "Revised positive source changed fixed declaration boundaries")
            body=candidate[len(prefix.encode()):-len(suffix.encode())].decode()
            guard.check_body(body,edit["addition"]["kind"],edit["forbidden_identifiers"])
            contract_review=dict(fixed_prefix_sha256=native.sha(prefix.encode()),fixed_suffix_sha256=native.sha(suffix.encode()),
                template_profile_sha256=native.sha(native.canonical(edit)),body_sha256=native.sha(body.encode()),
                original_template_contracts_unchanged=True)
        else:
            contract_review=None
        if stage==2:
            native.require(sources["growth/AppendAll.dfy"]==observations["append-reference"][2]["growth/AppendAll.dfy"],
                           "Stage-two reference did not preserve exact revised stage-one control")
        pins=native.EvidencePins(native.sha(native.canonical(profile)),native.sha(native.canonical(record)),
            native.sha(native.canonical(native.hashes(sources))),tuple(sorted(native.hashes(raw).items())),
            record["run_id"],record["origin"])
        report=native.review(profile,sources,record,raw,pins)
        native.require(report["qualified_success"] and report["strict_zero_warning_success"],
                       "Actual reference replay did not qualify")
        current=set(profile["required_units"])
        native.require(prior_units<=current,"Earlier native obligations disappeared")
        delta=sorted(current-prior_units)
        prior_units=current
        report["source_contract_review"]=contract_review
        report["new_units_vs_previous_stage"]=delta
        profile_path="stage"+str(stage)+".json"
        write(destination/profile_path,profile)
        write(destination/("mapping-stage"+str(stage)+".json"),dict(definitions=defs,units=rows,
            unlogged_definition_count=len(unlogged),source_hashes=native.hashes(sources),
            no_unlogged_definition_counted_as_pass=True))
        write(destination/"replay-001"/(name+".json"),report)
        profiles[str(stage)]=dict(path=profile_path,profile_sha256=native.sha(native.canonical(profile)),
                                 file_sha256=native.sha((destination/profile_path).read_bytes()))
        reports.append(dict(case=name,stage=stage,stage_id=stage_id,run_id=record["run_id"],
            category=report["category"],logged_passes=report["passed_units"],warnings=report["warnings"],
            unlogged_definitions=len(unlogged),source_files=len(sources),
            new_units_vs_previous_stage=delta if stage else "baseline inventory",
            elapsed_seconds=record["elapsed_seconds"],resources=report["resources"],
            model_origin_parent=False,acceptance_issued=False))
    summary=dict(schema="dafny-library-native-profile-review-v1",project="stdlib",status="POSITIVE_NATIVE_INVENTORY_REPLAYED",
        observations=reports,profiles=profiles,excluded_failed_references=excluded_report,
        input_files=input_files,actual_observations_replayed=3,new_native_calls=0,model_calls=0,
        execution_release_issued=False,negative_controls_release="pending separate review",
        independent_profile_mapping_review="pending root review",unlogged_definitions_are_not_passes=True)
    write(destination/"review.json",summary)
    print(json.dumps({key:summary[key] for key in ("status","observations","actual_observations_replayed",
          "new_native_calls","model_calls","execution_release_issued")},indent=2))
    return summary


if __name__=="__main__":
    build()
