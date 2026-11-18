"""Sequential, one-shot native controls with isolated source and build state."""
import json
import os
from pathlib import Path
import shutil
import sys
import common as c
from capture import capture,write,digest
from gates.vmc import protocol as dg
from score import observe

def files(root,ignore_results=False):
    result={}
    for p in sorted(root.rglob('*')):
        c.require(not p.is_symlink(),'Symlink in source/evidence inventory')
        if p.is_file():
            name=p.relative_to(root).as_posix()
            if not(ignore_results and name.startswith('TestResults/')):result[name]=digest(p.read_bytes())
    return result

def qualification(root=c.ROOT):return root.parents[1]/'real-repository-qualification-001'

def tool_observation(project,root=c.ROOT):
    c.require(project in c.PROJECTS,'Unknown project');q=qualification(root)
    if project=='dafny-vmc':
        image='container-003';closure='coverage-001/results/tool-closure.json';base=q/'toolchains/dafny-vmc/unpacked'
    else:
        image='vest-container-004';closure='vest-container-004/results/verus-tool-closure.json';base=q/'vest-container-002/tools/unpacked'
    pins=c.read(root/'qualification'/closure);observed=c.sha(q/image/'runtime.sif')
    c.require(observed==c.read(root/'tool-image-pins.json')[image]['sif_sha256'],'Pinned image changed')
    c.check_pins(base,pins)
    return dict(project=project,image=str(q/image/'runtime.sif'),image_sha256=observed,
                closure_path=closure,closure_manifest_sha256=c.sha(root/'qualification'/closure),
                checked_tool_files=len(pins),toolchain=c.base_profile(project,root)['toolchain'])

def make_command(project,case_id,work,root=c.ROOT):
    entry=c.case(project,case_id,root);q=qualification(root);base=c.base_profile(project,root)
    resource=c.read(root/'plan.json')['resources'][project]
    if project=='dafny-vmc':
        additions=set(entry['overlay_sha256'])-set(entry['explicitly_omit_from_command'])
        logical=['verify','dfyconfig.toml',*sorted(set(base['explicit_sources'])|additions),
                 '--resource-limit','100000','--log-format','csv']
        prefix=['singularity','exec','--cleanenv','--bind',str(q.parent)+':'+str(q.parent),
                '--pwd',str(work),'--env','DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1',
                str(q/'container-003/runtime.sif'),str(q/'toolchains/dafny-vmc/unpacked/dafny/dafny')]
    else:
        prefix=list(c.read(root/'qualification/vest-container-004/results/invocation-prefix.json')['prefix'])
        old_q=prefix[prefix.index('--bind')+1].split(':')[0]
        prefix=[x.replace(old_q,str(q)) for x in prefix]
        prefix[prefix.index('--bind')+1]=str(q.parent)+':'+str(q.parent)
        prefix[prefix.index('--pwd')+1]=str(work)
        prefix[-1:-1]=['--env','CARGO_BUILD_JOBS=1']
        logical=['cargo','verus','verify','-p','vest_dev','--locked','--offline','--check-toolchain',
                 '--target-dir','<FRESH_TARGET>','--','--expand-errors','--output-json','--time-expanded','--num-threads','1']
    command=prefix+[str(root/'targets'/project/case_id) if x=='<FRESH_TARGET>' else x for x in logical]
    return command,logical,resource['native_wall_seconds']

def profile_for(project,case_id,root=c.ROOT):
    entry=c.case(project,case_id,root);base=c.base_profile(project,root)
    _,logical,_=make_command(project,case_id,root/'work'/project/case_id,root)
    return dict(project=project,case=entry,source_sha256={**c.project_sources(project,root),**entry['overlay_sha256']},
                logical_command=logical,toolchain=base['toolchain'],resources=c.read(root/'plan.json')['resources'][project],
                baseline_profile_sha256=c.sha(root/'qualification'/('coverage-001' if project=='dafny-vmc' else 'vest-coverage-001')/'profile.json'),
                reference_gate_sha256=c.sha(root/'reference-gates/aggregate.json'),
                project_reference_gate_sha256=c.sha(root/'reference-gates'/(project+'.json')),model_calls=0)

def summary_row(project,case_id,native,observation,d):
    return dict(project=project,case=case_id,category=observation['category'],expected_kind=observation['expected_kind'],
                expectation_match=observation['expectation_match'],whole_workspace_proof_pass=observation['whole_workspace_proof_pass'],
                required_workspace_coverage=observation['required_workspace_coverage'],exit_code=native['exit_code'],
                elapsed_seconds=native['elapsed_seconds'],stop_after_case=observation['stop_after_case'],
                execution_termination=observation['execution_termination'],
                observation_sha256=c.sha(d/'observation.json'))

def verify_case(project,case_id,out,job_id,root=c.ROOT,native_capture=capture):
    entry=c.case(project,case_id,root);d=out/case_id;work=root/'work'/project/case_id
    c.require(not d.exists() and not work.exists() and not(root/'targets'/project/case_id).exists(),
              'Existing case state: no restart or resume')
    d.mkdir();profile=profile_for(project,case_id,root);write(d/'profile.json',profile)
    before_tools=tool_observation(project,root);write(d/'tools-before.json',before_tools)
    original=c.project_sources(project,root);work.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(qualification(root)/'upstream'/project,work)
    parent=files(work);write(d/'parent-source-audit.json',dict(expected=original,observed=parent,match=parent==original))
    c.require(parent==original,'Parent source differs')
    source=root/'inputs'/project/case_id;c.check_pins(source,entry['overlay_sha256'])
    for name in entry['overlay_sha256']:
        target=work/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((source/name).read_bytes())
        saved=d/'overlay'/name;saved.parent.mkdir(parents=True,exist_ok=True)
        with saved.open('xb') as f:f.write((source/name).read_bytes())
    prepared=files(work);write(d/'prepared-source-audit.json',dict(expected=profile['source_sha256'],observed=prepared,match=prepared==profile['source_sha256']))
    c.require(prepared==profile['source_sha256'],'Prepared source differs')
    command,logical,limit=make_command(project,case_id,work,root)
    write(d/'intent.json',dict(project=project,case=case_id,ordinal=entry['ordinal'],command=command,native_wall_seconds=limit,
                             model_calls=0,maximum_native_invocations=1,profile_sha256=dg.sha(dg.canonical(profile))))
    native=native_capture('native',command,root,d,dict(os.environ),limit)
    raw={n:(d/'native'/n).read_bytes() for n in ('stdout.txt','stderr.txt','resources.txt')}
    if project=='dafny-vmc':
        for f in sorted(work.rglob('*.csv')):
            name='csv/'+f.relative_to(work).as_posix();raw[name]=f.read_bytes()
            dest=d/'native'/name;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as stream:stream.write(raw[name])
    after=files(work,ignore_results=project=='dafny-vmc');write(d/'source-after.json',dict(source_sha256=after,match=after==profile['source_sha256']))
    bound=dict(run_id=job_id+':'+case_id,profile_sha256=dg.sha(dg.canonical(profile)),source_sha256=prepared,source_after_sha256=after,
               logical_command=logical,toolchain=profile['toolchain'],raw_sha256={n:dg.sha(b) for n,b in sorted(raw.items())},
               model_calls=0,attempts=1,exit_code=native['exit_code'],elapsed_seconds=native['elapsed_seconds'])
    write(d/'bound-record.json',bound);dg.check_record(bound,profile,job_id+':'+case_id,raw)
    after_tools=tool_observation(project,root);write(d/'tools-after.json',after_tools)
    c.require(before_tools==after_tools,'Tools changed during case')
    try:observation=observe(project,case_id,native,raw,root)
    except Exception as exc:
        write(d/'observation-error.json',dict(type=type(exc).__name__,message=str(exc),raw_preserved=True,no_retry=True));raise
    write(d/'observation.json',observation)
    return summary_row(project,case_id,native,observation,d)

def run_cases(project,out,job_id,root=c.ROOT,native_capture=capture):
    c.require(not any((out/n).exists() for n in ('complete.json','stopped.json','failure.json')) and
              not list(out.glob('progress-*.json')) and not any(p.is_dir() for p in out.iterdir()),
              'Existing project execution state: no restart or resume')
    rows=[];expected_runtime=c.sha(root/'runtime-freeze.json')
    try:
        for entry in c.cases(project,root):
            c.require(c.sha(root/'runtime-freeze.json')==expected_runtime,'Runtime changed between cases');c.validate_package(root)
            row=verify_case(project,entry['id'],out,job_id,root,native_capture);rows.append(row)
            write(out/('progress-%02d.json'%entry['ordinal']),dict(results=list(rows),model_calls=0))
            if row['stop_after_case']:
                stopped=dict(state=('STOPPED_NATIVE_TERMINATION' if row['execution_termination']=='UNRESOLVED_SIGNAL_OR_TIMEOUT'
                                    else 'STOPPED_AMBIGUOUS_NATIVE_EVIDENCE'),project=project,results=rows,native_invocations=len(rows),
                             undispatched=[e['id'] for e in c.cases(project,root)[len(rows):]],model_calls=0,no_resume=True)
                write(out/'stopped.json',stopped);return stopped
        complete=dict(state='COMPLETE',project=project,results=rows,native_invocations=len(rows),undispatched=[],model_calls=0,no_resume=True)
        write(out/'complete.json',complete);return complete
    except BaseException as exc:
        write(out/'failure.json',dict(state='STOPPED_INTEGRITY_PARSER_OR_EXECUTION_ERROR',project=project,type=type(exc).__name__,
              message=str(exc),completed_results=rows,model_calls=0,no_resume=True,no_retry=True,raw_evidence_preserved=True));raise

def main():
    c.require(len(sys.argv)==2 and sys.argv[1] in c.PROJECTS,'Choose one fixed control project')
    project=sys.argv[1];environment=c.compute_environment(project);c.validate_package();c.aggregate_budget(project)
    out=c.ROOT/('verification-'+project+'-001');out.mkdir(exist_ok=False)
    write(out/'environment.json',dict(**environment,model_calls=0,plan_sha256=c.sha(c.ROOT/'plan.json'),
                                     runtime_sha256=c.sha(c.ROOT/'runtime-freeze.json'),aggregate_budget=c.aggregate_budget(project)))
    result=run_cases(project,out,environment['job_id']);return 0 if result['state']=='COMPLETE' else 2

if __name__=='__main__':sys.exit(main())
