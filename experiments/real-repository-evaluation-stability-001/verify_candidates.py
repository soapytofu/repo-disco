"""A single sequential verifier worker for one repository; no model/SDK imports."""
import json
import os
from pathlib import Path
import shutil
import sys

import common as c
from capture import capture,write,digest
from gates.vmc import protocol as dg


def files(root,*,ignore_results=False):
    return {p.relative_to(root).as_posix():digest(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and not(ignore_results and p.relative_to(root).as_posix().startswith('TestResults/'))}


def qualification(root=c.ROOT):
    return root/'qualification'


def remote_qualification(root=c.ROOT):
    return root.parent/'real-repository-qualification-001'


def validate_tools(project,root=c.ROOT):
    q=remote_qualification(root);saved=qualification(root)
    if project=='dafny-vmc':
        image='container-003';closure='coverage-001/results/tool-closure.json';base=q/'toolchains/dafny-vmc/unpacked'
    else:
        image='vest-container-004';closure='vest-container-004/results/verus-tool-closure.json';base=q/'vest-container-002/tools/unpacked'
    # Image records are pinned in the execution bundle, not guessed by filename.
    image_pin=c.read(root/'tool-image-pins.json')[image]
    c.require(c.sha(q/image/'runtime.sif')==image_pin['sif_sha256'],'Image changed')
    c.check_pins(base,c.read(saved/closure))
    return q


def make_command(project,slot_id,work,root=c.ROOT):
    c.require(project=='dafny-vmc','Only the fixed Dafny resource experiment is executable')
    slot=int(slot_id.split('-')[1]);entry=next(e for e in c.read(root/'plan.json')['cases'] if e['slot']==slot)
    q=remote_qualification(root);base=c.read(qualification(root)/'coverage-001/profile.json')
    logical=['verify','dfyconfig.toml',*sorted(base['explicit_sources']),'--resource-limit',str(entry['resource_limit']),'--log-format','csv']
    prefix=['singularity','exec','--cleanenv','--bind',str(q.parent)+':'+str(q.parent),'--pwd',str(work),'--env','DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1',str(q/'container-003/runtime.sif'),str(q/'toolchains/dafny-vmc/unpacked/dafny/dafny')]
    return prefix+logical,logical,entry['wall_seconds'],base['required_units'],base


def verify_one(entry,task,project,out,job_id,*,root=c.ROOT,native_capture=capture):
    slot_id='slot-%02d'%entry['slot'];source=root/'sources'/(entry['source']+'.txt')
    c.require(c.sha(source)==entry['candidate_sha256'],'Reviewed candidate changed')
    q=remote_qualification(root);projects={p['id']:p for p in c.read(qualification(root)/'source-manifest.json')}
    original=projects[project]['files'];work=root/'work'/project/slot_id
    work.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(q/'upstream'/project,work)
    c.require(files(work)==original,'Parent source differs')
    candidate=source.read_bytes();(work/task['file']).write_bytes(candidate)
    expected={**original,task['file']:entry['candidate_sha256']}
    c.require(files(work)==expected,'Candidate source differs')
    command,logical,limit,required,base=make_command(project,slot_id,work,root)
    c.require(not (root/'targets'/slot_id).exists(),'Existing build target; no restart')
    record=native_capture(slot_id,command,root,out,dict(os.environ),limit)
    d=out/slot_id;raw={n:(d/n).read_bytes() for n in ['stdout.txt','stderr.txt','resources.txt']}
    if project=='dafny-vmc':
        for f in sorted(work.rglob('*.csv')):
            n='csv/'+f.relative_to(work).as_posix();raw[n]=f.read_bytes()
            dest=d/n;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as stream:stream.write(raw[n])
    after=files(work,ignore_results=project=='dafny-vmc')
    c.require(after==expected,'Source changed during verification')
    profile=dict(task=task,slot=entry,source_sha256=expected,logical_command=logical,toolchain=base['toolchain'],required=required)
    bound=dict(run_id=job_id+':'+slot_id,profile_sha256=dg.sha(dg.canonical(profile)),source_sha256=expected,source_after_sha256=after,
               logical_command=logical,toolchain=base['toolchain'],raw_sha256={n:dg.sha(b) for n,b in sorted(raw.items())},
               model_calls=0,attempts=1,exit_code=record['exit_code'],elapsed_seconds=record['elapsed_seconds'])
    write(d/'profile.json',profile);write(d/'bound-record.json',bound);dg.check_record(bound,profile,job_id+':'+slot_id,raw)
    observation=c.verification_observation(project,record,raw,base);write(d/'observation.json',observation)
    if observation['qualified_scope_pass']:
        write(d/'accepted.json',dict(slot=entry['slot'],task=task['id'],candidate_sha256=entry['candidate_sha256'],
                                   protected_source_sha256=expected,observation_sha256=c.sha(d/'observation.json'),
                                   acceptance='diagnostic_pass_only',live_repository_promoted=False))
    return dict(slot=entry['slot'],task=task['id'],category=observation['category'],qualified_scope_pass=observation['qualified_scope_pass'],
                strict_zero_warning_pass=observation['strict_zero_warning_pass'],coverage_complete=observation['coverage_complete'],
                warnings_match_upstream=observation['warnings_match_upstream'],exit_code=record['exit_code'],elapsed_seconds=record['elapsed_seconds'])


def main():
    c.require(len(sys.argv)==2 and sys.argv[1] in ('dafny-vmc',),'Choose one verifier stage')
    project=sys.argv[1];environment=c.compute_environment(project)
    tasks,groups=c.validate_package()
    out=c.ROOT/('verification-'+project+'-001');out.mkdir(exist_ok=False)
    write(out/'environment.json',dict(**environment,model_calls=0,plan_sha256=c.sha(c.ROOT/'plan.json'),runtime_sha256=c.sha(c.ROOT/'runtime-freeze.json')))
    rows=[]
    try:
        q=validate_tools(project)
        entries=[e for e in groups if tasks[e['task']]['project']==project]
        for entry in entries:
            c.validate_package()
            rows.append(verify_one(entry,tasks[entry['task']],project,out,environment['job_id']))
        write(out/'complete.json',dict(project=project,model_calls=0,results=rows,expected_candidates=len(entries)))
    except BaseException as e:
        write(out/'failure.json',dict(type=type(e).__name__,message=str(e),completed=rows,model_calls=0))
        raise


if __name__=='__main__':main()
