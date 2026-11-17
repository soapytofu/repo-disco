"""Offline replay of request provenance, protected candidates and native evidence."""
import collections
import json
from pathlib import Path
import sys

import common as c
from capture import write
from gates.vmc import protocol as dg
from verify_candidates import files,make_command,qualification


def review_verification(project,root=c.ROOT):
    tasks,groups=c.validate_package(root)
    entries=[e for e in groups if tasks[e['task']]['project']==project]
    out=root/('verification-'+project+'-001');environment=c.read(out/'environment.json')
    c.require(environment['job_id']==c.read(root/'submissions'/(project+'.json'))['job_id'],'Verifier job provenance differs')
    c.require(environment['plan_sha256']==c.sha(root/'plan.json') and environment['runtime_sha256']==c.sha(root/'runtime-freeze.json'),'Worker gate/runtime differs')
    c.require(environment['cpus']==c.STAGES[project]['cpus'] and environment['model_calls']==0,'Worker resources/provenance differ')
    complete=c.read(out/'complete.json');c.require(complete['expected_candidates']==len(entries),'Missing candidates')
    c.require({p.name for p in out.iterdir() if p.is_dir()}=={'slot-%02d'%e['slot'] for e in entries},'Unexpected/missing trial folders')
    projects={p['id']:p for p in c.read(qualification(root)/'source-manifest.json')};rows=[]
    for entry in entries:
        tid=entry['task'];slot_id='slot-%02d'%entry['slot'];d=out/slot_id;task=tasks[tid]
        native=c.read(d/'record.json');profile=c.read(d/'profile.json');bound=c.read(d/'bound-record.json')
        raw={n:(d/n).read_bytes() for n in bound['raw_sha256']}
        dg.check_record(bound,profile,environment['job_id']+':'+slot_id,raw)
        expected={**projects[project]['files'],task['file']:entry['candidate_sha256']}
        command,logical,_,required,base=make_command(project,slot_id,root/'work'/project/slot_id,root)
        remote_root=environment['execution_root'];remote_outputs=str(Path(remote_root).parent)
        command=[a.replace(str(root.parent),remote_outputs) for a in command]
        c.require(native['command']==command and native['cwd']==remote_root,'Native command differs')
        c.require(native['model_calls']==0 and native['attempts']==1 and native['exit_code']==bound['exit_code'] and native['elapsed_seconds']==bound['elapsed_seconds'],'Native process differs')
        c.require(native['artifacts']=={n:dg.sha(raw[n]) for n in ['stdout.txt','stderr.txt','resources.txt']},'Native log hashes differ')
        expected_profile=dict(task=task,slot=entry,source_sha256=expected,logical_command=logical,toolchain=base['toolchain'],required=required)
        c.require(profile==expected_profile,'Expected source/scope profile differs')
        observation=c.verification_observation(project,native,raw,base)
        c.require(c.read(d/'observation.json')==observation,'Observation replay differs')
        if observation['qualified_scope_pass']:
            acceptance=c.read(d/'accepted.json')
            c.require(acceptance==dict(slot=entry['slot'],task=tid,candidate_sha256=entry['candidate_sha256'],protected_source_sha256=expected,
                                      observation_sha256=c.sha(d/'observation.json'),acceptance='qualified_declared_scope',live_repository_promoted=False),'Acceptance differs')
        else:c.require(not (d/'accepted.json').exists(),'Failed source accepted')
        row=dict(slot=entry['slot'],task=tid,category=observation['category'],qualified_scope_pass=observation['qualified_scope_pass'],
                 strict_zero_warning_pass=observation['strict_zero_warning_pass'],coverage_complete=observation['coverage_complete'],
                 warnings_match_upstream=observation['warnings_match_upstream'],exit_code=native['exit_code'],elapsed_seconds=native['elapsed_seconds'])
        rows.append(row)
    c.require(complete==dict(project=project,model_calls=0,results=rows,expected_candidates=len(entries)),'Worker summary differs')
    return dict(status='VERIFICATION_REVIEW_PASSED',project=project,results=rows,qualified_passes=sum(r['qualified_scope_pass'] for r in rows),
                candidates=len(rows),raw_files=files(out),no_new_model_calls=True)


if __name__=='__main__':
    project=sys.argv[1];c.require(project in c.STAGES,'Unknown project')
    report=review_verification(project);write(c.ROOT/('review-'+project+'-001.json'),report)
    print(json.dumps({k:v for k,v in report.items() if k!='raw_files'},indent=2))
