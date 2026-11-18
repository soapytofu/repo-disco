"""Exactly 23 frozen verifier controls; no retry, resume or model execution."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import socket

ROOT=Path(__file__).resolve().parent
PROJECTS=('dafny-vmc','vest')
STAGES={'dafny-vmc':dict(cpus=1,memory_gb=2,minutes=90),
        'vest':dict(cpus=1,memory_gb=4,minutes=240)}
AGGREGATE_SHA='0999050882566d8630dec4566ed5526e05fbabcd9f4f1092c9c9322322a82207'

def read(path):return json.loads(Path(path).read_bytes())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)

def check_pins(base,pins):
    for name,value in pins.items():
        p=PurePosixPath(name)
        require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,'Unsafe pinned path')
        current=base/name
        while current!=base:
            require(not current.is_symlink(),'Symlink in pinned path');current=current.parent
        require(not base.is_symlink() and sha(base/name)==value,'Pinned bytes changed: '+name)

def base_profile(project,root=ROOT):
    require(project in PROJECTS,'Unknown project')
    return read(root/'qualification'/('coverage-001' if project=='dafny-vmc' else 'vest-coverage-001')/'profile.json')

def project_sources(project,root=ROOT):
    require(project in PROJECTS,'Unknown project')
    return next(x['files'] for x in read(root/'qualification/source-manifest.json') if x['id']==project)

def cases(project,root=ROOT):
    require(project in PROJECTS,'Unknown project')
    return read(root/'plan.json')['cases'][project]

def case(project,case_id,root=ROOT):
    matches=[e for e in cases(project,root) if e['id']==case_id]
    require(len(matches)==1,'Case not in remaining fixed controls; completed references are excluded')
    return matches[0]

def aggregate_budget(project,root=ROOT):
    resource=read(root/'plan.json')['resources'][project]
    require(resource['cpus']==STAGES[project]['cpus']==1,'One CPU required')
    require(resource['job_minutes']==STAGES[project]['minutes'],'Aggregate job bound changed')
    require(resource['case_count']==len(cases(project,root)),'Case count changed')
    native_total=resource['case_count']*resource['native_wall_seconds']
    require(resource['job_minutes']*60>=native_total+600,'Insufficient aggregate wall allowance')
    return dict(native_cap_total_seconds=native_total,job_minutes=resource['job_minutes'],
                overhead_allowance_seconds=resource['job_minutes']*60-native_total,cpus=1)

def validate_inputs(root=ROOT):
    plan=read(root/'plan.json');aggregate=read(root/'reference-gates/aggregate.json')
    require(sha(root/'reference-gates/aggregate.json')==plan['reference_gate_sha256']==AGGREGATE_SHA,'Reference gate differs')
    require(aggregate['control_preparation_released'] is True and aggregate['model_calls_authorized']==0,'Reference gate scope differs')
    require(plan['model_calls']==0 and plan['native_invocations_max']==23 and plan['model_scope_authorized'] is False,'Invocation budget differs')
    require(set(plan['cases'])==set(PROJECTS) and set(plan['resources'])==set(PROJECTS),'Project scope differs')
    require(plan['completed_references_excluded']=={'dafny-vmc':'pair-reference','vest':'batch-reference'},'Completed references not excluded')
    require(plan['native_stop_exit_codes']==[124,137,143] and plan['stop_on_negative_exit'] is True,'Termination stop policy differs')
    require(plan['ambiguous_native_categories_halt']==['ENVIRONMENT_OR_BUILD_ERROR','ENVIRONMENT_OR_SOLVER_ERROR',
            'FRONTEND_OR_EXECUTION_ERROR','INCOMPLETE_OR_UNCLASSIFIED','NO_VERIFICATION_REPORT','UNCLASSIFIED'],
            'Ambiguous native evidence stop policy differs')
    require(sha(root/'source-catalogs/dafny.json')==aggregate['controls_source_bindings']['dafny-revision-002/controls-manifest.json'],'Dafny source catalog differs')
    require(sha(root/'source-catalogs/vest.json')==aggregate['controls_source_bindings']['qualification-001/plan.json'],'Vest source catalog differs')
    for project,count in [('dafny-vmc',11),('vest',12)]:
        entries=plan['cases'][project];ids=[e['id'] for e in entries]
        require(ids==aggregate['remaining_control_ids'][project] and len(ids)==count and len(set(ids))==count,'Control order/count differs')
        require(plan['completed_references_excluded'][project] not in ids,'Completed reference scheduled')
        gate_path=root/plan['reference_gates'][project]['file'];gate=read(gate_path)
        require(sha(gate_path)==plan['reference_gates'][project]['sha256']==aggregate['references'][project]['sha256'],'Project reference gate differs')
        require(gate['native_exit_code']==0 and gate['errors']==0 and gate['model_calls']==0,'Reference did not pass')
        require(base_profile(project,root)['source_sha256']==project_sources(project,root),'Baseline source profile differs')
        require(gate['source_sha256']=={**project_sources(project,root),**gate['overlay_sha256']},'Reference/base source binding differs')
        catalog=(read(root/'source-catalogs/dafny.json')['cases'] if project=='dafny-vmc'
                 else read(root/'source-catalogs/vest.json')['catalog']['vest'])
        catalog={e['id']:e for e in catalog}
        require({p.name for p in (root/'inputs'/project).iterdir()}==set(ids),'Unexpected control input directory')
        for ordinal,e in enumerate(entries,1):
            original=catalog[e['id']];pins=original['additions'] if project=='dafny-vmc' else original['overlay_sha256']
            require(e['ordinal']==ordinal and e['overlay_sha256']==pins,'Control source/ordinal differs')
            folder=root/'inputs'/project/e['id'];check_pins(folder,pins)
            require({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}==set(pins),'Unexpected overlay file')
            require(e['expected_kind'] in ('proof_pass','named_proof_failure','coverage_omission'),'Unknown control category')
            require(set(e['expected_observed_new_inventory'])|set(e['expected_missing_new_units'])==set(e['required_new_inventory']),'Observed/required scope mismatch')
            require(set(e['expected_observed_new_inventory']).isdisjoint(e['expected_missing_new_units']),'Omitted target scheduled')
            require(set(e['expected_failed_new_units'])<=set(e['expected_observed_new_inventory']),'Failed target absent')
        resource=plan['resources'][project];aggregate_budget(project,root)
        require(resource['memory_gb']==STAGES[project]['memory_gb'],'Memory allocation differs')
        require(resource['native_wall_seconds']==(300 if project=='dafny-vmc' else 900),'Native cap differs')
        if project=='dafny-vmc':require(resource['resource_limit']==100000,'Dafny budget differs')
        else:require(resource['cargo_build_jobs']==resource['verus_num_threads']==1,'Vest concurrency differs')
    return plan

def validate_package(root=ROOT):
    freeze=read(root/'runtime-freeze.json')
    require(freeze['model_calls']==0 and freeze['native_invocations_max']==23 and freeze['completed_reference_dispatch']==False,'Runtime scope differs')
    check_pins(root,freeze['files']);return validate_inputs(root)

def compute_environment(project):
    require(project in PROJECTS,'Unknown project')
    require(os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower(),'Compute allocation required')
    require(int(os.environ.get('SLURM_CPUS_PER_TASK','0'))==1,'One CPU allocation required')
    require(os.environ.get('SLURM_JOB_PARTITION') in ('test','shared'),'Unexpected partition')
    return dict(project=project,job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),
                partition=os.environ['SLURM_JOB_PARTITION'],cpus=1,execution_root=str(ROOT))
