"""Review the three saved UInt-only AWS reference observations, offline.

All observations remain analyst controls. Function-method contracts are checked
in their actual named well-formedness units; no correctness label is invented.
The separate negative/omission gate is required before a pilot release.
"""
from collections import Counter
import csv
import importlib.util
import io
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
sys.path.insert(0, str(EXPERIMENT/"common"))
import guard
import review_native as native

spec = importlib.util.spec_from_file_location("aws_source_scanner", EXPERIMENT/"pilot/prepare.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)
spec = importlib.util.spec_from_file_location("saved_native_loader", HERE/"build_stdlib.py")
saved = importlib.util.module_from_spec(spec)
spec.loader.exec_module(saved)

REFERENCE_ROOT = "qualification-005/retrieved-aws/qualification-005/output-aws"
SOURCE_ROOT = "aws/revision-002"
MODULE_FILES = {
    "StandardLibrary.UInt": "StandardLibrary/src/UInt.dfy",
    "BoundedInts": "libraries/src/BoundedInts.dfy",
    "Wrappers": "libraries/src/Wrappers.dfy",
    "RepoDiscoU16Frame": "StandardLibrary/src/RepoDiscoU16Frame.dfy",
    "RepoDiscoFramePair": "StandardLibrary/src/RepoDiscoFramePair.dfy",
}
STAGES = [("baseline",0,"baseline"), ("stage1-reference",1,"u16-frame"), ("stage2-reference",2,"frame-pair")]
TARGETS = {1:"RepoDiscoU16Frame.ReadU16Frame (well-formedness)",
           2:"RepoDiscoFramePair.ReadFramePair (well-formedness)"}


def declarations(sources):
    """Narrow source-position mapping for the five fixed AWS files.

    Module options and legacy `function method`/`predicate method` are retained.
    Wrappers' datatype members use their actual containing datatype names.
    This is an audited mapping for pinned sources, not a general Dafny parser.
    """
    found = []
    for file, raw in sorted(sources.items()):
        text = raw.decode()
        module = re.findall(r"^module\s+(?:\{:[^\n]*?\}\s*)*([A-Za-z_][A-Za-z0-9_.]*)\s*\{", text, re.M)
        native.require(len(module)==1 and MODULE_FILES.get(module[0])==file,
                       "Module/source ownership not in reviewed scope: "+file)
        by_line = {}
        container = None
        for number,line in enumerate(text.splitlines(),1):
            datatype = re.match(r"^  datatype\s+([A-Za-z_][A-Za-z0-9_']*)",line)
            if datatype:
                container = datatype.group(1)
            by_line[number] = container
            if line == "  }":
                container = None
            simple = re.match(r"^  (const|newtype|type|datatype)\s+([A-Za-z_][A-Za-z0-9_']*)",line)
            if simple:
                kind,name = simple.groups()
                found.append(dict(name=module[0]+"."+name,kind=kind,file=file,line=number,
                    source_line=line,source_sha256=native.sha(raw)))
        for declaration in scanner.declaration_headers(text):
            number = declaration["line"]
            line = text.splitlines()[number-1]
            indent = len(line)-len(line.lstrip())
            native.require(indent in {2,4}, "Unexpected declaration indentation requires review")
            owner = module[0]
            if indent == 4:
                native.require(by_line[number] is not None, "Nested declaration lacks a reviewed datatype owner")
                owner += "."+by_line[number]
            found.append(dict(name=owner+"."+declaration["name"],kind=declaration["kind"],file=file,line=number,
                source_line=line,source_sha256=native.sha(raw),attributes=declaration["attributes"]))
    native.require(len({row["name"] for row in found})==len(found),"Duplicate source declaration identity")
    return sorted(found,key=lambda row:(row["file"],row["line"],row["name"]))


def inventory(sources,raw):
    rows = []
    columns = None
    for path,data in sorted(raw.items()):
        if not path.startswith("csv/"):
            continue
        parsed = csv.DictReader(io.StringIO(data.decode(),newline=""),strict=True)
        native.require(tuple(parsed.fieldnames)==native.CSV_SCHEMAS[1],"Actual CSV schema differs")
        columns = parsed.fieldnames
        for offset,row in enumerate(parsed,2):
            label = row["TestResult.DisplayName"]
            owners = [module for module in MODULE_FILES if label.startswith(module+".")]
            native.require(len(owners)==1,"Native source ownership is ambiguous: "+label)
            file = MODULE_FILES[owners[0]]
            native.require(file in sources,"Native unit source not in exact workspace")
            rows.append(dict(label=label,file=file,csv=path,row=offset,fields=row))
    counts = Counter(row["label"] for row in rows)
    native.require(rows and all(count==1 for count in counts.values()),
                   "Missing/duplicate native units; do not silently deduplicate")
    native.require(all(row["fields"]["TestResult.Outcome"]=="Passed" for row in rows),
                   "Failed observations cannot establish positive profiles")
    definitions = declarations(sources)
    by_name = {row["name"]:row for row in definitions}
    for row in rows:
        name = row["label"].split(" (")[0]
        native.require(name in by_name and by_name[name]["file"]==row["file"],
                       "Native label lacks matching source declaration: "+name)
    unlogged = []
    for row in definitions:
        row["logged_units"]=[unit["label"] for unit in rows if unit["label"].split(" (")[0]==row["name"]]
        row["has_logged_units"]=bool(row["logged_units"])
        if not row["logged_units"]:
            unlogged.append(dict(name=row["name"],file=row["file"],source_sha256=row["source_sha256"],
                counted_as_pass=False,kind=row["kind"],line=row["line"],source_line=row["source_line"],
                reason="No named CSV unit for this source definition in the saved complete-scope observation; not a logged proof pass."))
    native.require({row["file"] for row in rows}==set(sources),"A staged source lacks actual native unit coverage")
    return columns,rows,definitions,unlogged,dict(sorted(counts.items()))


def body_review(stage,sources,baseline):
    name = MODULE_FILES["RepoDiscoU16Frame" if stage==1 else "RepoDiscoFramePair"]
    template = (EXPERIMENT/SOURCE_ROOT/"templates"/Path(name).name).read_text()
    parent = None if stage==1 else dict(stage_id="u16-frame",addition_path=MODULE_FILES["RepoDiscoU16Frame"],guard_profile_sha256="0"*64)
    # This is a reconstruction-only profile, never an accepted-parent receipt.
    profile = dict(schema=guard.SCHEMA,project="aws",stage=stage,stage_id=STAGES[stage][2],
        base_source_sha256=native.hashes(baseline),addition=dict(path=name,template_utf8=template,
            begin_marker=scanner.BEGIN,end_marker=scanner.END,kind="function"),registrations={},
        verification_inputs=sorted(sources),forbidden_identifiers=scanner.trust_inventory(baseline)["forbidden_identifiers"],
        parent_requirement=parent)
    prefix,suffix=guard._profile(profile)
    source=sources[name]
    native.require(source.startswith(prefix.encode()) and source.endswith(suffix.encode()),"New function changed fixed declaration bytes")
    body=source[len(prefix.encode()):len(source)-len(suffix.encode())].decode()
    rebuilt,lexical=guard.render_body(profile,body)
    native.require(rebuilt==source,"Reference is not byte-exact guarded reconstruction")
    return dict(file=name,source_sha256=native.sha(source),body_sha256=native.sha(body.encode()),
        fixed_prefix_sha256=native.sha(prefix.encode()),fixed_suffix_sha256=native.sha(suffix.encode()),
        template_path=SOURCE_ROOT+"/templates/"+Path(name).name,template_sha256=native.sha(template.encode()),
        lexical_review=lexical,exact_guarded_reconstruction=True,acceptance_issued=False)


def build(destination=None):
    destination=Path(destination or HERE/"aws-001").resolve()
    observations={name:saved.load_observation(REFERENCE_ROOT+"/"+name) for name,_,_ in STAGES}
    denied_runs=sorted(row[1]["run_id"] for row in observations.values())
    denied_raw=sorted(native.sha(native.canonical(native.hashes(row[3]))) for row in observations.values())
    input_files={}
    for folder,record,sources,raw in observations.values():
        for path in [folder/"record.json",*sorted((folder/"workspace").rglob("*.dfy")),
                     *[p for p in sorted((folder/"raw").rglob("*")) if p.is_file()]]:
            input_files[path.relative_to(EXPERIMENT).as_posix()]=native.sha(path.read_bytes())
    for name in ("common/guard.py","common/review_native.py","native-profiles/build_aws.py",
                 "native-profiles/build_stdlib.py","pilot/prepare.py",SOURCE_ROOT+"/cases.json",
                 SOURCE_ROOT+"/templates/RepoDiscoU16Frame.dfy",SOURCE_ROOT+"/templates/RepoDiscoFramePair.dfy"):
        input_files[name]=native.sha((EXPERIMENT/name).read_bytes())
    baseline=observations["baseline"][2]
    native.require(len(baseline)==3,"AWS qualified base must be exactly the narrowed three-file scope")
    destination.mkdir(parents=True,exist_ok=False)
    previous=set()
    reports=[]
    profiles={}
    for name,stage,stage_id in STAGES:
        folder,record,sources,raw=observations[name]
        native.require(record["exit_code"]==0 and not record["timeout"],"Positive record is not a complete success")
        native.require(all(sources[file]==data for file,data in baseline.items()),"Upstream source changed across stages")
        columns,rows,defs,unlogged,multiplicities=inventory(sources,raw)
        inputs=record["argv"][-len(sources):]
        native.require(len(inputs)==len(set(inputs)) and set(inputs)==set(sources),"Native source coverage/order differs")
        native.require(record["argv"][record["argv"].index("--cores")+1]=="1","Native CPU count differs")
        profile=dict(schema=native.PROFILE_SCHEMA,project="aws",stage=stage,stage_id=stage_id,
            inventory_status="qualified",command=record["argv"],verification_inputs=inputs,
            toolchain=record["toolchain"],csv_columns=columns,random_seed=0,
            required_units={row["label"]:row["file"] for row in sorted(rows,key=lambda row:row["label"])},
            unitless_files={},unlogged_definitions=unlogged,inherited_warnings=[],
            ineligible_parent_runs=denied_runs,ineligible_parent_raw_fingerprints=denied_raw,
            scope_origin="actual analyst qualification observation on the UInt-only dependency closure; not a model-accepted revision",
            source_observation=dict(path=folder.relative_to(EXPERIMENT).as_posix(),run_id=record["run_id"],
                record_file_sha256=native.sha((folder/"record.json").read_bytes()),
                source_revision_sha256=native.sha(native.canonical(native.hashes(sources)))),
            actual_function_target_units=[TARGETS[n] for n in range(1,stage+1)],
            function_contract_encoding="The function methods have actual well-formedness units; no separate correctness unit is fabricated.",
            execution_release_issued=False,negative_controls_release="pending separate review")
        for target in profile["actual_function_target_units"]:
            native.require(target in profile["required_units"],"Actual function contract unit absent")
        contract=body_review(stage,sources,baseline) if stage else None
        if stage==2:
            native.require(sources[MODULE_FILES["RepoDiscoU16Frame"]]==observations["stage1-reference"][2][MODULE_FILES["RepoDiscoU16Frame"]],
                           "Stage two changed the saved stage-one reference")
        pins=native.EvidencePins(native.sha(native.canonical(profile)),native.sha(native.canonical(record)),
            native.sha(native.canonical(native.hashes(sources))),tuple(sorted(native.hashes(raw).items())),record["run_id"],record["origin"])
        review=native.review(profile,sources,record,raw,pins)
        native.require(review["qualified_success"] and review["strict_zero_warning_success"],"Native reference did not qualify under common reviewer")
        current=set(profile["required_units"])
        native.require(previous<=current,"A prior stage's native obligations disappeared")
        delta=sorted(current-previous)
        previous=current
        review.update(source_contract_review=contract,new_units_vs_previous_stage=delta,analyst_parent_ineligible=True)
        path="stage"+str(stage)+".json"
        saved.write(destination/path,profile)
        saved.write(destination/("mapping-stage"+str(stage)+".json"),dict(definitions=defs,units=rows,
            native_unit_multiplicities=multiplicities,source_hashes=native.hashes(sources),
            unlogged_definition_count=len(unlogged),no_unlogged_definition_counted_as_pass=True))
        saved.write(destination/"replay-001"/(name+".json"),review)
        profiles[str(stage)]=dict(path=path,file_sha256=native.sha((destination/path).read_bytes()),canonical_sha256=native.sha(native.canonical(profile)))
        reports.append(dict(case=name,stage=stage,stage_id=stage_id,run_id=record["run_id"],category=review["category"],
            logged_passes=review["passed_units"],warnings=review["warnings"],unlogged_definitions=len(unlogged),
            source_files=len(sources),new_units_vs_previous_stage=delta if stage else "baseline inventory",
            elapsed_seconds=record["elapsed_seconds"],resources=review["resources"],
            model_origin_parent=False,acceptance_issued=False,expected_match=True))
    summary=dict(schema="dafny-library-native-profile-review-v1",project="aws",status="POSITIVE_NATIVE_INVENTORY_REPLAYED",
        observations=reports,profiles=profiles,input_files=input_files,actual_observations_replayed=3,
        new_native_calls=0,model_calls=0,execution_release_issued=False,negative_controls_release="pending separate review",
        independent_profile_mapping_review="pending root review",unlogged_definitions_are_not_passes=True,
        scope_limits=["Three original source files plus two executable additions; not the complete AWS MPL repository.",
            "No UTF8 or encryption-context scope; the earlier 102-file baseline remains unqualified historical evidence."])
    saved.write(destination/"review.json",summary)
    print(json.dumps({key:summary[key] for key in ("status","observations","actual_observations_replayed",
        "new_native_calls","model_calls","execution_release_issued")},indent=2))
    return summary


if __name__=="__main__":
    build()
