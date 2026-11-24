"""One-shot compute operations for the frozen eight-slot independent extension pilot.

Only an existing authenticated socket is used. No function reads a private
handoff, creates an allocation claim, constructs a provider client, or runs a
native verifier. The submitted production runner alone may do those things.
"""
import argparse
import datetime
import hashlib
import inspect as python_inspect
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import tarfile
import time

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
SOCKET=Path.home()/".ssh/repodisco-codex-21.sock"
HOST="sophiezeng@login.rc.fas.harvard.edu"
PYTHON="/n/home13/sophiezeng/.conda/envs/repodisco/bin/python"
JOB_NAME="dafny-varied-growth-8-001"
JOB_SECONDS=10800
FREEZE_NAME="execution-001/runtime-freeze.json"
MAX_ARCHIVE_BYTES=2*1024**3
ACCOUNTING_FIELDS=("JobID","State","Elapsed","ElapsedRaw","ExitCode","AllocCPUS",
                   "TotalCPU","CPUTimeRAW","MaxRSS","NodeList")
TERMINAL_STATES=frozenset(("BOOT_FAIL","CANCELLED","COMPLETED","DEADLINE","FAILED",
                          "NODE_FAIL","OUT_OF_MEMORY","PREEMPTED","REVOKED","TIMEOUT"))


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def read(path):return json.loads(Path(path).read_bytes())


def write(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def save(path,value):write(path,canonical(value)+b"\n")


def safe_name(name):
    return (isinstance(name,str) and name and not PurePosixPath(name).is_absolute()
            and "\\" not in name and all(p not in {"",".",".."} for p in name.split("/"))
            and all(32<=ord(c)<127 for c in name))


def canonical_location(value):
    path=Path(value)
    require(path.is_absolute() and str(path)==value and str(path.resolve())==value,"Noncanonical location")
    for parent in (path,*path.parents):require(not parent.is_symlink(),"Symlink in canonical location")
    return path


def regular_files(folder):
    folder=Path(folder);result={}
    require(folder.is_dir() and not folder.is_symlink(),"Nonregular evidence root")
    for path in sorted(folder.rglob("*")):
        mode=path.lstat().st_mode
        require(not stat.S_ISLNK(mode),"Symlink evidence cannot be archived")
        if stat.S_ISDIR(mode):continue
        require(stat.S_ISREG(mode),"Nonregular evidence")
        name=path.relative_to(folder).as_posix()
        require(safe_name(name),"Unsafe evidence name")
        result[name]=path.read_bytes()
    return result


def archive_members(raw):
    require(isinstance(raw,bytes) and len(raw)<=MAX_ARCHIVE_BYTES,"Transfer exceeds byte bound")
    members={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as archive:
        for member in archive.getmembers():
            require(member.isfile() and safe_name(member.name) and member.name not in members,
                    "Unsafe, nonregular or duplicate archive entry")
            require(0<=member.size<=MAX_ARCHIVE_BYTES
                    and sum(len(x) for x in members.values())+member.size<=MAX_ARCHIVE_BYTES,
                    "Expanded archive exceeds byte bound")
            data=archive.extractfile(member).read()
            require(len(data)==member.size,"Truncated archive member")
            members[member.name]=data
    require(members and not any(str(parent) in members for name in members
            for parent in PurePosixPath(name).parents),"Archive has file/directory path collision")
    return members


def make_archive(files):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode="w:gz") as archive:
        for name,data in sorted(files.items()):
            require(safe_name(name) and isinstance(data,bytes),"Invalid archive input")
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600
            archive.addfile(info,io.BytesIO(data))
    return buffer.getvalue()


def no_matching_queue(queue,binding):
    root=str(Path(binding["package_root"]).parent)
    for line in queue.splitlines():
        if not line.strip():continue
        fields=[x.strip() for x in line.split("|")]
        require(len(fields)==4 and fields[0],"Malformed queue listing")
        job,working,name,state=fields
        require(name!=JOB_NAME and working!=root and not working.startswith(root+"/"),
                "Matching execution is already queued")


def partition_seconds(text):
    pairs=re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9]*)=(\S+)",text)
    require(len({k for k,v in pairs})==len(pairs),"Duplicate partition fields")
    values=dict(pairs)
    require(values.get("PartitionName")=="test" and values.get("PreemptMode")=="OFF"
            and values.get("State")=="UP","Test partition must be live-confirmed UP/nonpreemptible")
    maximum=values.get("MaxTime","")
    if maximum=="UNLIMITED":seconds=None
    else:
        match=re.fullmatch(r"(?:(\d+)-)?(\d+):(\d{2}):(\d{2})",maximum)
        require(match is not None,"Unrecognized partition time limit")
        days,hours,minutes,secs=(int(x or 0) for x in match.groups())
        require(minutes<60 and secs<60,"Malformed partition time limit")
        seconds=((days*24+hours)*60+minutes)*60+secs
        require(seconds>=JOB_SECONDS,"Partition cannot fit fixed three-hour job")
    for key,minimum in (("MaxCPUsPerNode",1),("MaxMemPerNode",4096),("MaxMemPerCPU",4096)):
        if key not in values or values[key] in {"UNLIMITED","0"}:continue
        require(values[key].isdigit() and int(values[key])>=minimum,"Partition resource limit insufficient")
    return seconds


def terminal_accounting(accounting,job):
    require(isinstance(job,str) and re.fullmatch(r"[1-9][0-9]*",job),"Invalid exact parent JobID")
    lines=[line for line in accounting.splitlines() if line.strip()]
    require(lines and tuple(x.strip() for x in lines[0].split("|"))==ACCOUNTING_FIELDS,
            "Unexpected accounting header")
    rows=[];seen=set();ignored=[]
    for line in lines[1:]:
        values=[x.strip() for x in line.split("|")]
        require(len(values)==len(ACCOUNTING_FIELDS),"Malformed accounting row")
        row=dict(zip(ACCOUNTING_FIELDS,values));ident=row["JobID"]
        require(ident,"Missing accounting JobID")
        if ident!=job and not ident.startswith(job+"."):
            ignored.append(ident);continue
        require(ident==job or re.fullmatch(re.escape(job)+r"\.[A-Za-z0-9_-]+",ident),"Malformed relevant step")
        require(ident not in seen,"Duplicate parent or step");seen.add(ident)
        state=row["State"]
        if state.endswith("+"):state=state[:-1].rstrip()
        match=re.fullmatch(r"([A-Z_]+)(?: by ([0-9]+))?",state)
        require(match and (match.group(2) is None or match.group(1)=="CANCELLED"),"Unknown state syntax")
        require(match.group(1) in TERMINAL_STATES,"Nonterminal/unknown parent or step")
        rows.append(dict(job_id=ident,state=row["State"],normalized_state=match.group(1)))
    require(sum(r["job_id"]==job for r in rows)==1,"Missing exact parent accounting")
    return dict(parent_job_id=job,rows=rows,ignored_job_ids=ignored,all_relevant_rows_terminal=True,
                accounting_sha256=sha(accounting.encode()))


def command(argv,seconds=20):
    result=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    require(result.returncode==0,"Read-only cluster command failed: "+argv[0])
    return result.stdout.decode("utf-8")


def inspect_state(binding):
    package=canonical_location(binding["package_root"]);root=package.parent
    output=canonical_location(binding["output_path"]);claim=canonical_location(binding["allocation_claim_path"])
    budget=canonical_location(binding["budget_snapshot_path"])
    queue=command(["squeue","-u","sophiezeng","-h","-o","%i|%Z|%j|%T"],15)
    return dict(package_exists=package.exists(),output_exists=output.exists(),claim_exists=claim.exists(),
        budget_exists=budget.exists(),budget_sha256=sha(budget.read_bytes()) if budget.is_file() else None,
        authorization_exists=(root/"authorization.json").exists(),
        stage_intent_exists=(root/"stage.intent.json").exists(),
        submission_files=[p.name for p in (root/"submissions").iterdir()] if (root/"submissions").exists() else [],
        ledger_files=[p.relative_to(root).as_posix() for p in root.rglob("*ledger*")
                      if p.relative_to(root).parts[0]!="synthetic-smoke"] if root.exists() else [],
        synthetic_smoke_exists=(root/"synthetic-smoke").exists(),
        queue=queue)


def fresh_state(state,binding,*,staging=False):
    require(not state["output_exists"] and not state["claim_exists"] and not state["submission_files"]
            and not state["ledger_files"] and not state["authorization_exists"],"Existing execution/claim/ledger: no restart")
    no_matching_queue(state["queue"],binding)
    if staging:
        require(not state["package_exists"] and not state["stage_intent_exists"],"Existing stage: no restage")
    else:require(state["package_exists"],"Frozen remote package absent")
    if state["budget_exists"]:
        require(state["budget_sha256"]==binding["budget_snapshot_sha256"],"Existing cumulative snapshot differs")


def verify_package(binding,expected_runtime,*,allow_drift=False):
    package=canonical_location(binding["package_root"])
    freeze_raw=(package/FREEZE_NAME).read_bytes()
    require(sha(freeze_raw)==expected_runtime,"Remote manifest differs")
    freeze=json.loads(freeze_raw)
    require(freeze["schema"]=="dafny-library-execution-runtime-v1","Unknown runtime schema")
    differences=[]
    for name,digest in freeze["files"].items():
        require(safe_name(name),"Unsafe frozen input")
        target=package/name
        for parent in (target,*target.parents):
            if parent==package.parent:break
            require(not parent.is_symlink(),"Symlink frozen input")
        if not target.is_file() or sha(target.read_bytes())!=digest:differences.append(name)
    require(allow_drift or not differences,"Remote frozen input drift")
    return freeze,dict(expected_runtime_sha256=expected_runtime,changed_or_missing=sorted(differences),
                       all_input_pins_match=not differences)


def stage_remote(binding,expected_runtime,payload):
    before=inspect_state(binding);fresh_state(before,binding,staging=True)
    files=archive_members(payload)
    require(FREEZE_NAME in files and sha(files[FREEZE_NAME])==expected_runtime,"Wrong staged manifest")
    freeze=json.loads(files[FREEZE_NAME])
    require(set(files)==set(freeze["files"])|{FREEZE_NAME},"Archive is not exact manifest-only package")
    require(all(sha(files[name])==digest for name,digest in freeze["files"].items()),"Staged input digest differs")
    scope=json.loads(files[freeze["scope"]])
    require(scope["execution_binding"]==binding,"Staged execution binding differs")
    budget_raw=files[binding["budget_snapshot_input"]]
    require(sha(budget_raw)==binding["budget_snapshot_sha256"],"Staged budget digest differs")
    package=Path(binding["package_root"]);root=package.parent
    root.mkdir(parents=True,exist_ok=True)
    save(root/"stage.intent.json",dict(runtime_sha256=expected_runtime,prior_state=before,no_retry=True))
    package.mkdir()
    for name,data in files.items():write(package/name,data)
    budget=Path(binding["budget_snapshot_path"])
    budget.parent.mkdir(parents=True,exist_ok=True)
    if budget.exists():require(budget.read_bytes()==budget_raw,"Existing immutable budget differs")
    else:write(budget,budget_raw)
    Path(binding["allocation_claim_path"]).parent.mkdir(parents=True,exist_ok=True)
    require(not Path(binding["allocation_claim_path"]).exists(),"Staging must never create allocation claim")
    verify_package(binding,expected_runtime)
    result=dict(runtime_sha256=expected_runtime,files=len(freeze["files"]),package_root=str(package),
                external_budget_sha256=sha(budget.read_bytes()),allocation_claim_created=False,
                model_calls=0,native_verifier_calls=0)
    save(root/"stage-001.json",result)
    return result


def preflight_remote(binding,expected_runtime):
    before=inspect_state(binding);fresh_state(before,binding)
    freeze,_=verify_package(binding,expected_runtime)
    package=Path(binding["package_root"]);root=package.parent
    require(not (root/"preflight-001.json").exists(),"Preflight already recorded")
    require(not (root/"synthetic-smoke").exists() and not (root/"synthetic-smoke").is_symlink(),
            "Packaged renderer smoke must start from an absent synthetic output")
    save(root/"preflight.intent.json",dict(runtime_sha256=expected_runtime,prior_state=before,no_retry=True))
    # Imports/config construction only: no SDK client, credential, network probe.
    try:
        import boto3,botocore
        from botocore.config import Config
        config=Config(connect_timeout=15,read_timeout=180,retries={"mode":"standard","total_max_attempts":1})
        sdk=dict(boto3_version=boto3.__version__,botocore_version=botocore.__version__,client_created=False,
                 connect_timeout=config.connect_timeout,read_timeout=config.read_timeout,retries=config.retries,
                 private_handoff_read=False,provider_calls=0,installed=True)
    except BaseException as error:
        sdk=dict(installed=False,error_type=type(error).__name__,client_created=False,
                 private_handoff_read=False,provider_calls=0)
        save(root/"sdk-imports.json",sdk)
        write(root/"preflight.stdout.txt",b"")
        message="SDK import/config preflight failed: "+type(error).__name__+"\n"
        write(root/"preflight.stderr.txt",message.encode())
        result=dict(runtime_sha256=expected_runtime,exit_code=2,timed_out=False,sdk=sdk,
                    tests_started=False,stdout="",stderr=message,model_calls=0,native_verifier_calls=0,
                    canonical_claim_created=False)
        save(root/"preflight-001.json",result)
        return result
    save(root/"sdk-imports.json",sdk)
    argv=[PYTHON,"-B","-m","unittest","-v","test_runner","test_native_host","test_build_runtime","test_allocation","test_ops","test_review_collection"]
    unit,out,err=capture_preflight(argv,package/"execution-001",60)
    write(root/"preflight.stdout.txt",out);write(root/"preflight.stderr.txt",err)
    require(not Path(binding["allocation_claim_path"]).exists(),"Fake preflight created canonical allocation claim")
    smoke=None
    if unit["exit_code"]==0 and not unit["timed_out"]:
        smoke=capture_renderer_smoke(binding,expected_runtime,freeze)
    passed=unit["exit_code"]==0 and not unit["timed_out"] and smoke is not None and smoke["status"]=="PASS"
    result=dict(runtime_sha256=expected_runtime,argv=argv,exit_code=0 if passed else 2,
                unit_result=unit,renderer_smoke=smoke,
                renderer_smoke_record_sha256=sha((root/"renderer-smoke.json").read_bytes()) if smoke else None,
                timed_out=unit["timed_out"] or bool(smoke and smoke["timed_out"]),
                sdk=sdk,stdout=out.decode(errors="replace"),stderr=err.decode(errors="replace"),
                model_calls=0,native_verifier_calls=0,canonical_claim_created=False,
                synthetic_temporary_claim_tests=True)
    save(root/"preflight-001.json",result)
    return result


def capture_preflight(argv,cwd,seconds):
    import signal
    child=None;timed_out=False
    try:
        child=subprocess.Popen(argv,cwd=cwd,stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        try:out,err=child.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out=True
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            out,err=child.communicate(timeout=10)
        return dict(exit_code=child.returncode,timed_out=timed_out,wall_cap_seconds=seconds),out,err
    except BaseException as error:
        return dict(exit_code=None,timed_out=timed_out,wall_cap_seconds=seconds,
                    error_type=type(error).__name__),b"",("Preflight process failed: "+type(error).__name__+"\n").encode()
    finally:
        if child is not None:
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            child.wait(timeout=10)


def validate_smoke_receipt(receipt,summary,expected_runtime,renderer):
    expected=dict(mode="smoke",synthetic=True,provider_calls=0,native_processes=0,
        fake_transport_dispatches=8,fake_native_observations=8,reserved=8,completed=8,
        accepted_synthetic_stages=8,exact_base_view_assertions=8,default_synthetic_rejection_assertions=8,actual_renderer=renderer,
        staged_module_path_verified=True,manifest_sha256=expected_runtime)
    require(type(receipt) is dict and all(type(receipt.get(k)) is type(v) and receipt[k]==v
            for k,v in expected.items()),"Renderer smoke receipt is incomplete, mismatched or not synthetic")
    expected_summary=dict(status="COMPLETE",synthetic=True,reserved=8,completed=8,
                          accepted_stages=8,independent_trials=True,
                          native_dispatches=8,native_observations=8)
    require(type(summary) is dict and all(type(summary.get(k)) is type(v) and summary[k]==v
            for k,v in expected_summary.items()),"Renderer smoke summary differs from completed fake run")


def capture_renderer_smoke(binding,expected_runtime,freeze):
    package=Path(binding["package_root"]);root=package.parent
    script="pilot/test_render.py"
    require(script in freeze["files"] and not (root/"synthetic-smoke").exists(),
            "Missing frozen smoke entry point or preexisting synthetic run")
    argv=[PYTHON,"-B",str(package/script),"--smoke",str(package),freeze["scope"]]
    process,out,err=capture_preflight(argv,package,120)
    write(root/"renderer-smoke.stdout.txt",out);write(root/"renderer-smoke.stderr.txt",err)
    record=dict(schema="dafny-library-renderer-smoke-host-v1",argv=argv,runtime_sha256=expected_runtime,
                synthetic=True,provider_calls=0,native_verifier_calls=0,status="FAIL",**process)
    receipt=None
    try:
        require(process["exit_code"]==0 and not process["timed_out"] and not err,
                "Packaged renderer smoke process did not complete cleanly")
        receipt=json.loads(out.decode("utf-8"))
        summary=read(root/"synthetic-smoke/summary.json")
        scope=read(package/freeze["scope"])
        validate_smoke_receipt(receipt,summary,expected_runtime,scope["renderer"])
        require(not Path(binding["allocation_claim_path"]).exists()
                and not Path(binding["output_path"]).exists(),"Smoke touched canonical paid state")
        record["synthetic_artifacts"]={name:sha(data) for name,data in regular_files(root/"synthetic-smoke").items()}
        record["status"]="PASS"
    except BaseException as error:
        record["validation_error_type"]=type(error).__name__
    save(root/"renderer-smoke-receipt.json",receipt)
    record["evidence_sha256"]={name:sha((root/name).read_bytes()) for name in
        ("renderer-smoke.stdout.txt","renderer-smoke.stderr.txt","renderer-smoke-receipt.json")}
    save(root/"renderer-smoke.json",record)
    return record


def verify_smoke_evidence(binding,expected_runtime,freeze,preflight):
    package=Path(binding["package_root"]);root=package.parent
    path=root/"renderer-smoke.json"
    require(path.is_file() and not path.is_symlink()
            and sha(path.read_bytes())==preflight.get("renderer_smoke_record_sha256"),
            "Persisted renderer smoke record differs from completed preflight")
    record=read(path)
    require(record==preflight.get("renderer_smoke") and record.get("status")=="PASS"
            and record.get("runtime_sha256")==expected_runtime and record.get("synthetic") is True
            and record.get("exit_code")==0 and record.get("timed_out") is False,
            "Successful matching packaged renderer smoke required")
    expected_names={"renderer-smoke.stdout.txt","renderer-smoke.stderr.txt","renderer-smoke-receipt.json"}
    require(set(record.get("evidence_sha256",{}))==expected_names,"Incomplete smoke evidence inventory")
    for name,digest in record["evidence_sha256"].items():
        require((root/name).is_file() and not (root/name).is_symlink()
                and sha((root/name).read_bytes())==digest,"Smoke stdout/stderr/receipt drifted")
    require(record.get("synthetic_artifacts")=={name:sha(data) for name,data in regular_files(root/"synthetic-smoke").items()},
            "Synthetic smoke workspace/source/ledger changed")
    receipt=read(root/"renderer-smoke-receipt.json")
    require(json.loads((root/"renderer-smoke.stdout.txt").read_bytes())==receipt
            and not (root/"renderer-smoke.stderr.txt").read_bytes(),"Smoke output receipt differs")
    validate_smoke_receipt(receipt,read(root/"synthetic-smoke/summary.json"),expected_runtime,
                           read(package/freeze["scope"])["renderer"])


def submit_remote(binding,expected_runtime,authorization_raw):
    before=inspect_state(binding);fresh_state(before,binding)
    freeze,_=verify_package(binding,expected_runtime)
    package=Path(binding["package_root"]);root=package.parent
    pre=read(root/"preflight-001.json")
    require(pre["runtime_sha256"]==expected_runtime and pre["exit_code"]==0 and not pre["timed_out"]
            and pre["sdk"]["client_created"] is False and pre["canonical_claim_created"] is False,
            "Completed matching fake preflight required")
    verify_smoke_evidence(binding,expected_runtime,freeze,pre)
    import sys
    sys.path.insert(0,str(package/"execution-001"))
    from runtime import validate_authorization
    from allocation import validate_execution_binding
    scope=read(package/freeze["scope"]);auth=json.loads(authorization_raw)
    validate_authorization(auth,sha((package/freeze["scope"]).read_bytes()),expected_runtime,time.time())
    validate_execution_binding(auth,scope,package,Path(binding["output_path"]))
    partition=command(["scontrol","show","partition","test"],15)
    partition_seconds(partition)
    # Final queue inspection immediately precedes exclusive intent/submission.
    queue=command(["squeue","-u","sophiezeng","-h","-o","%i|%Z|%j|%T"],15)
    no_matching_queue(queue,binding)
    record=dict(schema="dafny-library-model-submission-v1",runtime_sha256=expected_runtime,
        authorization_sha256=sha(authorization_raw),partition="test",partition_record=partition,
        prior_state=before,final_queue=queue,resources=dict(cpus=1,memory_gb=4,seconds=JOB_SECONDS,no_requeue=True),
        submission_attempts=1,no_retry=True)
    save(root/"submissions/model.intent.json",record)
    write(root/"authorization.json",authorization_raw)
    argv=["sbatch","--parsable","--partition=test","--nodes=1","--ntasks=1","--cpus-per-task=1",
          "--mem=4G","--time=03:00:00","--no-requeue","--job-name="+JOB_NAME,
          "--chdir="+str(root),str(package/"execution-001/model.sbatch"),
          str(package/freeze["scope"]),expected_runtime]
    record["argv"]=argv
    try:
        result=subprocess.run(argv,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
        record.update(exit_code=result.returncode,stdout=result.stdout.decode(errors="replace"),
                      stderr=result.stderr.decode(errors="replace"))
        match=re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*",record["stdout"])
        if result.returncode==0 and match:record["job_id"]=match.group(1)
        elif result.returncode==0:record["ambiguous_submission"]=True
    except BaseException as error:
        record.update(error_type=type(error).__name__,ambiguous_submission=True)
    save(root/"submissions/model.json",record)
    return record


def accounting(job):
    require(re.fullmatch(r"[1-9][0-9]*",job),"Invalid submitted JobID")
    return command(["sacct","-j",job,"-P",
        "--format=JobID%40,State%80,Elapsed,ElapsedRaw,ExitCode,AllocCPUS,TotalCPU,CPUTimeRAW,MaxRSS,NodeList"],20)


def transfer_files(binding,expected_runtime,job):
    package=Path(binding["package_root"]);root=package.parent
    text=accounting(job);terminal=terminal_accounting(text,job)
    queue=command(["squeue","-u","sophiezeng","-h","-o","%i|%Z|%j|%T"],15)
    no_matching_queue(queue,binding)
    freeze,integrity=verify_package(binding,expected_runtime,allow_drift=True)
    require(not (root/"fetch.intent.json").exists(),"A final transfer was already claimed")
    files={}
    for name in sorted(freeze["files"]):
        path=package/name
        if path.exists():files["package/"+name]=path.read_bytes()
    files["package/"+FREEZE_NAME]=(package/FREEZE_NAME).read_bytes()
    required=("stage.intent.json","stage-001.json","preflight.intent.json","sdk-imports.json",
              "preflight-001.json","preflight.stdout.txt","preflight.stderr.txt",
              "renderer-smoke.json","renderer-smoke.stdout.txt","renderer-smoke.stderr.txt","renderer-smoke-receipt.json",
              "authorization.json","submissions/model.intent.json","submissions/model.json")
    for name in required:
        path=root/name
        require(path.is_file() and not path.is_symlink(),"Missing submission/provenance evidence")
        files[name]=path.read_bytes()
    receipt=json.loads(files["submissions/model.json"])
    require(receipt.get("job_id")==job,"Remote submission identity differs")
    output=Path(binding["output_path"])
    if output.exists():
        files.update({"model-001/"+name:data for name,data in regular_files(output).items()})
    files.update({"synthetic-smoke/"+name:data for name,data in regular_files(root/"synthetic-smoke").items()})
    claim=Path(binding["allocation_claim_path"])
    if claim.exists():
        require(claim.is_file() and not claim.is_symlink(),"Nonregular allocation claim")
        files["canonical-allocation-claim.json"]=claim.read_bytes()
    budget=Path(binding["budget_snapshot_path"])
    require(budget.is_file() and not budget.is_symlink(),"Canonical budget snapshot absent")
    files["canonical-budget-snapshot.json"]=budget.read_bytes()
    for path in sorted(root.glob("library-growth-"+job+".*")):
        require(path.is_file() and not path.is_symlink(),"Nonregular scheduler log")
        files[path.name]=path.read_bytes()
    require(any(name.startswith("library-growth-") or name.startswith("model-001/") for name in files),
            "No scheduler or model output evidence")
    files["accounting.txt"]=text.encode()
    files["accounting-review.json"]=canonical(terminal)
    files["runtime-integrity.json"]=canonical(integrity)
    inventory={name:dict(bytes=len(data),sha256=sha(data)) for name,data in sorted(files.items())}
    return files,dict(job_id=job,source_bytes=sum(len(data) for data in files.values()),
        regular_files=len(files),inventory=inventory,inventory_sha256=sha(canonical(inventory)))


def fetch_remote(binding,expected_runtime,job,expected_inventory):
    files,inventory=transfer_files(binding,expected_runtime,job)
    require(inventory==expected_inventory,"Terminal evidence changed after read-only size estimate")
    root=Path(binding["package_root"]).parent
    save(root/"fetch.intent.json",dict(job_id=job,inventory_sha256=inventory["inventory_sha256"],no_retry=True))
    return make_archive(files)


def identity():
    from build_runtime import validate_complete
    path=ROOT/"runtime-freeze.json"
    frozen=read(path);digest=sha(path.read_bytes())
    freeze,scope,stages=validate_complete(PACKAGE,frozen["scope"],path,digest)
    binding=read(ROOT/"execution-binding.json")
    require(scope["execution_binding"]==binding,"Local scope/binding differs")
    required={"execution-001/ops.py","execution-001/model.sbatch","execution-001/test_ops.py",
              "execution-001/execution-binding.json","execution-001/budget-snapshot.json","pilot/test_render.py"}
    require(required<=set(freeze["files"]),"Operations or budget inputs are not frozen")
    return freeze,binding,digest


REMOTE_FUNCTIONS=(require,sha,canonical,read,write,save,safe_name,canonical_location,regular_files,
                 archive_members,make_archive,no_matching_queue,partition_seconds,terminal_accounting,
                 command,inspect_state,fresh_state,verify_package,stage_remote,preflight_remote,
                 capture_preflight,validate_smoke_receipt,capture_renderer_smoke,verify_smoke_evidence,
                 submit_remote,accounting,transfer_files,fetch_remote)


def remote_program(action,binding,digest,job=None,inventory=None):
    require(action in {"inspect","stage","preflight","submit","status","estimate","fetch"},"Unknown action")
    preamble="import hashlib,io,json,os,re,stat,subprocess,tarfile,time,sys\nfrom pathlib import Path,PurePosixPath\n"
    constants=dict(JOB_NAME=JOB_NAME,JOB_SECONDS=JOB_SECONDS,FREEZE_NAME=FREEZE_NAME,
        MAX_ARCHIVE_BYTES=MAX_ARCHIVE_BYTES,ACCOUNTING_FIELDS=ACCOUNTING_FIELDS,TERMINAL_STATES=TERMINAL_STATES,
        PYTHON=PYTHON,BINDING=binding,DIGEST=digest,JOB=job,INVENTORY=inventory)
    code=preamble+"\n".join(k+"="+repr(v) for k,v in constants.items())+"\n"
    code+="\n".join(python_inspect.getsource(f) for f in REMOTE_FUNCTIONS)
    endings=dict(inspect="print(json.dumps(inspect_state(BINDING)))",
        stage="print(json.dumps(stage_remote(BINDING,DIGEST,sys.stdin.buffer.read())))",
        preflight="print(json.dumps(preflight_remote(BINDING,DIGEST)))",
        submit="print(json.dumps(submit_remote(BINDING,DIGEST,sys.stdin.buffer.read())))",
        status="print(json.dumps(dict(job_id=JOB,accounting=accounting(JOB),state=inspect_state(BINDING))))",
        estimate="print(json.dumps(transfer_files(BINDING,DIGEST,JOB)[1]))",
        fetch="sys.stdout.buffer.write(fetch_remote(BINDING,DIGEST,JOB,INVENTORY))")
    return code+"\n"+endings[action]+"\n"


def remote(action,binding,digest,*,payload=None,seconds=45,job=None,inventory=None):
    # ProxyCommand=false and BatchMode forbid fallback to a fresh authentication
    # session if the already-authenticated multiplexing socket has disappeared.
    argv=["ssh","-S",str(SOCKET),"-o","ControlMaster=no","-o","BatchMode=yes",
          "-o","ConnectTimeout=10","-o","ProxyCommand=false","-o","NumberOfPasswordPrompts=0",HOST]
    program=remote_program(action,binding,digest,job,inventory)
    program_bytes=program.encode("utf-8")
    require(0<len(program_bytes)<=2*1024**2,"Bounded remote source program required")
    require(payload is None or isinstance(payload,bytes),"Exact remote payload bytes required")
    require(payload is None or len(payload)<=MAX_ARCHIVE_BYTES,"Remote payload exceeds bound")
    bootstrap=("import sys; n=int.from_bytes(sys.stdin.buffer.read(8),'big'); "
        "assert 0<n<=2097152; code=sys.stdin.buffer.read(n); assert len(code)==n; "
        "exec(compile(code,'<repodisco-bounded-stdin>','exec'))")
    remote_command=" ".join(shlex.quote(x) for x in [PYTHON,"-B","-c",bootstrap])
    require(len(remote_command.encode())<4096,"Remote argv bound exceeded")
    wire=len(program_bytes).to_bytes(8,"big")+program_bytes+(payload or b"")
    result=subprocess.run(argv+[remote_command],input=wire,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=seconds)
    if result.returncode:
        raise RuntimeError("Bounded SSH operation failed (exit "+str(result.returncode)+"): "+
                           result.stderr.decode(errors="replace")[-4000:])
    return result.stdout


def inspect_remote():
    freeze,binding,digest=identity()
    print(remote("inspect",binding,digest).decode())


def local_fresh(kind):
    if kind=="stage":
        names=("stage.intent.json","stage-001.json")
    elif kind=="submit":
        names=("submissions/model.intent.json","submissions/model.json","submissions/model.transport-failure.json")
    elif kind=="preflight":
        names=("preflight.intent.json","preflight-001.json")
    else:names=("fetch.intent.json","transfer-001.json","retrieved-001","transfer-001.tar.gz")
    require(not any((ROOT/name).exists() for name in names),"Existing local "+kind+" intent/evidence; no retry")


def stage():
    freeze,binding,digest=identity();local_fresh("stage")
    before=json.loads(remote("inspect",binding,digest));fresh_state(before,binding,staging=True)
    files={name:(PACKAGE/name).read_bytes() for name in freeze["files"]}
    files[FREEZE_NAME]=(ROOT/"runtime-freeze.json").read_bytes()
    payload=make_archive(files)
    save(ROOT/"stage.intent.json",dict(runtime_sha256=digest,prior_state=before,no_retry=True))
    raw=remote("stage",binding,digest,payload=payload,seconds=180)
    write(ROOT/"stage-001.json",raw);print(raw.decode())


def preflight():
    freeze,binding,digest=identity();local_fresh("preflight")
    before=json.loads(remote("inspect",binding,digest));fresh_state(before,binding)
    save(ROOT/"preflight.intent.json",dict(runtime_sha256=digest,prior_state=before,no_retry=True))
    raw=remote("preflight",binding,digest,seconds=240)
    write(ROOT/"preflight-001.json",raw)
    result=json.loads(raw)
    print(json.dumps({k:result[k] for k in ("exit_code","timed_out","sdk")},indent=2))
    require(result["exit_code"]==0 and not result["timed_out"],"Fake/import preflight failed")


def submit(authorization):
    from runtime import validate_authorization
    from allocation import BINDING_FIELDS
    freeze,binding,digest=identity();local_fresh("submit")
    raw_authorization=Path(authorization).read_bytes();auth=json.loads(raw_authorization)
    scope=read(PACKAGE/freeze["scope"])
    validate_authorization(auth,sha((PACKAGE/freeze["scope"]).read_bytes()),digest,time.time())
    require(all(auth.get(k)==binding[k] for k in BINDING_FIELDS),"Canonical authorization differs")
    pre=read(ROOT/"preflight-001.json")
    require(pre["runtime_sha256"]==digest and pre["exit_code"]==0 and not pre["timed_out"],"Local fake preflight absent")
    before=json.loads(remote("inspect",binding,digest));fresh_state(before,binding)
    save(ROOT/"submissions/model.intent.json",dict(runtime_sha256=digest,prior_state=before,
         authorization_sha256=sha(raw_authorization),no_retry=True,maximum_submission_attempts=1))
    try:raw=remote("submit",binding,digest,payload=raw_authorization,seconds=75)
    except BaseException as error:
        save(ROOT/"submissions/model.transport-failure.json",dict(error_type=type(error).__name__,
             ambiguous_submission=True,no_retry=True));raise
    write(ROOT/"submissions/model.json",raw)
    result=json.loads(raw)
    print(json.dumps({k:v for k,v in result.items() if k not in {"prior_state","final_queue","partition_record"}},indent=2))
    require("job_id" in result and not result.get("ambiguous_submission"),"Submission failed/ambiguous; no retry")


def submitted_job():
    record=read(ROOT/"submissions/model.json")
    job=record.get("job_id")
    require(isinstance(job,str) and re.fullmatch(r"[1-9][0-9]*",job)
            and not record.get("ambiguous_submission"),"No unambiguous submitted JobID")
    return job


def status():
    freeze,binding,digest=identity()
    print(remote("status",binding,digest,job=submitted_job(),seconds=45).decode())


def check_space(estimate,*,archive_saved=False):
    size=estimate["source_bytes"]
    require(type(size) is int and 0<size<=MAX_ARCHIVE_BYTES,"Transfer estimate outside bound")
    required=(1 if archive_saved else 2)*size+64*1024**2
    available=shutil.disk_usage(ROOT).free
    require(available>=required,"Insufficient disk for raw archive plus extraction")
    return dict(required_free_bytes=required,available_free_bytes=available)


def fetch():
    freeze,binding,digest=identity();local_fresh("fetch");job=submitted_job()
    estimate=json.loads(remote("estimate",binding,digest,job=job,seconds=90))
    require(estimate["job_id"]==job,"Archive estimate is for another job")
    space=check_space(estimate)
    save(ROOT/"fetch.intent.json",dict(job_id=job,inventory_sha256=estimate["inventory_sha256"],no_retry=True))
    raw=remote("fetch",binding,digest,job=job,inventory=estimate,seconds=240)
    write(ROOT/"transfer-001.tar.gz",raw)
    files=archive_members(raw)
    inventory={name:dict(bytes=len(data),sha256=sha(data)) for name,data in sorted(files.items())}
    require(inventory==estimate["inventory"] and sha(canonical(inventory))==estimate["inventory_sha256"],
            "Full archive differs from terminal estimate")
    check_space(estimate,archive_saved=True)
    destination=ROOT/"retrieved-001";destination.mkdir()
    for name,data in files.items():write(destination/name,data)
    save(ROOT/"transfer-001.json",dict(job_id=job,archive_sha256=sha(raw),compressed_bytes=len(raw),
         files=inventory,read_only_estimate=estimate,local_disk=space))
    print(json.dumps(dict(job_id=job,files=len(files),compressed_bytes=len(raw))))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("inspect","stage","preflight","submit","status","fetch"))
    parser.add_argument("--authorization",type=Path)
    args=parser.parse_args()
    require((args.action=="submit")==(args.authorization is not None),"Only submit accepts explicit authorization")
    if args.action=="submit":submit(args.authorization)
    elif args.action=="inspect":inspect_remote()
    else:globals()[args.action]()

