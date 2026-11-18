"""Offline replay of full or explicitly timeout-stopped control evidence."""
from pathlib import Path
import json
import sys
import common as c
from capture import write
from gates.vmc import protocol as dg
from score import observe
from verify_controls import files,make_command,profile_for,summary_row

def review_case(project,entry,out,environment,root=c.ROOT):
    cid=entry['id'];d=out/cid;profile=c.read(d/'profile.json');bound=c.read(d/'bound-record.json');native=c.read(d/'native/record.json')
    raw={n:(d/'native'/n).read_bytes() for n in bound['raw_sha256']}
    dg.check_record(bound,profile,environment['job_id']+':'+cid,raw)
    c.require(profile==profile_for(project,cid,root),'Case source/scope profile differs')
    original=c.project_sources(project,root);expected=profile['source_sha256']
    c.require(c.read(d/'parent-source-audit.json')==dict(expected=original,observed=original,match=True),'Parent binding differs')
    c.require(c.read(d/'prepared-source-audit.json')==dict(expected=expected,observed=expected,match=True),'Prepared binding differs')
    c.require(c.read(d/'source-after.json')==dict(source_sha256=expected,match=True),'Source changed during verification')
    c.check_pins(d/'overlay',entry['overlay_sha256']);c.require(files(d/'overlay')==entry['overlay_sha256'],'Overlay inventory differs')
    remote=Path(environment['execution_root']);command,logical,limit=make_command(project,cid,remote/'work'/project/cid,root)
    command=[x.replace(str(root.parents[1]),str(remote.parents[1])) for x in command]
    c.require(native['command']==command and native['cwd']==str(remote),'Native command differs')
    c.require(native['attempts']==1 and native['model_calls']==0 and native['exit_code']==bound['exit_code'] and native['elapsed_seconds']==bound['elapsed_seconds'],'Native result differs')
    c.require(native['timeout']==(native['exit_code']==124),'Native timeout marker differs')
    c.require(native['artifacts']=={n:dg.sha(raw[n]) for n in ('stdout.txt','stderr.txt','resources.txt')},'Native raw bindings differ')
    c.require(c.read(d/'intent.json')==dict(project=project,case=cid,ordinal=entry['ordinal'],command=command,native_wall_seconds=limit,
              model_calls=0,maximum_native_invocations=1,profile_sha256=dg.sha(dg.canonical(profile))),'Case intent differs')
    image='container-003' if project=='dafny-vmc' else 'vest-container-004'
    closure='coverage-001/results/tool-closure.json' if project=='dafny-vmc' else 'vest-container-004/results/verus-tool-closure.json'
    expected_tools=dict(project=project,image=str(remote.parents[1]/'real-repository-qualification-001'/image/'runtime.sif'),
          image_sha256=c.read(root/'tool-image-pins.json')[image]['sif_sha256'],closure_path=closure,
          closure_manifest_sha256=c.sha(root/'qualification'/closure),checked_tool_files=len(c.read(root/'qualification'/closure)),
          toolchain=c.base_profile(project,root)['toolchain'])
    c.require(c.read(d/'tools-before.json')==c.read(d/'tools-after.json')==expected_tools,'Tool bindings differ')
    observation=observe(project,cid,native,raw,root)
    c.require(dg.canonical(observation)==dg.canonical(c.read(d/'observation.json')),'Observation replay differs')
    c.require(not(d/'observation-error.json').exists() and not(d/'accepted.json').exists(),'Contradictory case record')
    return summary_row(project,cid,native,observation,d)

def review_project(project,root=c.ROOT):
    c.validate_package(root);entries=c.cases(project,root);out=root/('verification-'+project+'-001')
    environment=c.read(out/'environment.json');submission=c.read(root/'submissions'/(project+'.json'))
    c.require(environment['project']==project,'Environment project identity differs')
    c.require(environment['job_id']==submission['job_id'] and environment['partition']==submission['partition'],'Submission identity differs')
    c.require(submission['no_requeue'] is True and environment['cpus']==1 and environment['model_calls']==0,'Resource/call provenance differs')
    c.require(environment['plan_sha256']==c.sha(root/'plan.json') and environment['runtime_sha256']==submission['runtime_sha256']==c.sha(root/'runtime-freeze.json'),'Runtime provenance differs')
    c.require(environment['aggregate_budget']==submission['aggregate_budget']==c.aggregate_budget(project,root),'Aggregate budget binding differs')
    existing=[n for n in ('complete.json','stopped.json','failure.json') if (out/n).exists()]
    c.require(existing in (['complete.json'],['stopped.json']),'Incomplete/error archive requires separate manual review')
    complete=c.read(out/existing[0]);count=len(complete['results'])
    c.require(0<count<=len(entries) and complete['project']==project and complete['native_invocations']==count and complete['model_calls']==0 and complete['no_resume'] is True,'Summary scope differs')
    c.require({p.name for p in out.iterdir() if p.is_dir()}=={e['id'] for e in entries[:count]},'Unexpected/missing case folders')
    rows=[]
    for entry in entries[:count]:
        rows.append(review_case(project,entry,out,environment,root))
        c.require(c.read(out/('progress-%02d.json'%entry['ordinal']))==dict(results=list(rows),model_calls=0),'Progress prefix differs')
    c.require(rows==complete['results'] and complete['undispatched']==[e['id'] for e in entries[count:]],'Summary/order differs')
    if complete['state']=='COMPLETE':c.require(count==len(entries) and not any(r['stop_after_case'] for r in rows),'Completed despite required halt')
    else:
        reason=('STOPPED_NATIVE_TERMINATION' if rows[-1]['execution_termination']=='UNRESOLVED_SIGNAL_OR_TIMEOUT'
                else 'STOPPED_AMBIGUOUS_NATIVE_EVIDENCE')
        c.require(complete['state']==reason and rows[-1]['stop_after_case'] and not any(r['stop_after_case'] for r in rows[:-1]),'Native evidence stop differs')
    return dict(status='CONTROL_EVIDENCE_REPLAY_PASSED',project=project,state=complete['state'],results=rows,
                matched_expectations=sum(r['expectation_match'] for r in rows),native_invocations=count,
                undispatched=complete['undispatched'],model_calls=0,no_rescore_of_prior_results=True,raw_files=files(out))

if __name__=='__main__':
    c.require(len(sys.argv)==2 and sys.argv[1] in c.PROJECTS,'Choose control project')
    result=review_project(sys.argv[1]);write(c.ROOT/('review-'+sys.argv[1]+'-001.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='raw_files'},indent=2))
