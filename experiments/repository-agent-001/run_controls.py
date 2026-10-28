"""Compute-only end-to-end agent controls with saved responses, zero API calls."""
import json,os,shutil,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'code'),str(ROOT/'guards')]
from repository_agent import RevisionStore,repair,atomic_json
from offline_gate import OfflineGate
from provider_guard import parse_response as provider_parse
from branch_guard import parse_response as branch_parse

def read(path):return {p.name:p.read_bytes() for p in path.glob('*.dfy')}

def main():
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():raise SystemExit('Slurm compute required')
    out=ROOT/'verification-001';out.mkdir(exist_ok=False)
    for name in ['code','guards','fixtures']:shutil.copytree(ROOT/name,out/name)
    shutil.copy2(__file__,out/'run_controls.py')
    atomic_json(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,response_mode='scripted_saved_fixtures',dafny=subprocess.check_output(['dafny','--version'],text=True).strip()))
    rows=[]
    for family in ['inductive','branch']:
        for condition in ['shared','separate']:
            name=family+'-'+condition;folder=out/name;folder.mkdir()
            base=read(ROOT/'fixtures'/family/(condition+'_empty'))
            positive=read(ROOT/'fixtures'/family/(condition+'_reference'))
            negative=read(ROOT/'fixtures'/family/(condition+('_no_recursive_step' if family=='inductive' else '_wrong_boundary')))
            editable=['Facts.dfy'] if family=='inductive' else ['ClientA.dfy','ClientB.dfy']
            deps={k:[] for k in base};deps.update({'All.dfy':['ClientA.dfy','ClientB.dfy'],'ClientA.dfy':['Facts.dfy'],'ClientB.dfy':['Facts.dfy']})
            manifest=dict(task_id=name,entry='All.dfy',editable=editable,dependencies=deps,context_policy='full_source_plus_declared_map')
            store=RevisionStore.create(folder/'store',base,manifest);original=store.snapshot()
            if family=='inductive':
                def decode(raw,snapshot):
                    content,_=provider_parse(raw,snapshot.files['Facts.dfy'].decode());return {'Facts.dfy':content.encode()}
                def guard(before,after):
                    content,_=provider_parse(json.dumps({'Facts.dfy':after.decode()}),before.decode())
                    assert content.encode()==after
                guards={'Facts.dfy':guard}
            else:
                def decode(raw,snapshot):
                    content,_=branch_parse(raw,{k:snapshot.files[k].decode() for k in editable});return {k:v.encode() for k,v in content.items()}
                guards={}
                for key in editable:
                    def guard(before,after,key=key):
                        source={k:base[k].decode() for k in editable};content,_=branch_parse(json.dumps({**source,key:after.decode()}),source);assert content[key].encode()==after
                    guards[key]=guard
            bad={k:positive[k].decode() for k in editable};bad[editable[0]]=bad[editable[0]].replace('ensures ','ensures false && ',1)
            responses=iter([json.dumps(bad),json.dumps({k:negative[k].decode() for k in editable}),json.dumps({k:positive[k].decode() for k in editable})])
            calls=[]
            def transport(prompt):calls.append(prompt);return next(responses)
            gate=OfflineGate(folder/'request-ledger',3,time.time()+300,transport)
            records=repair(store,gate,decode,guards,attempt_limit=3)
            assert [r['outcome'] for r in records]==['EDIT_REJECTED','PROOF_FAILURE','SUCCESS'],records
            assert store.snapshot().files==positive
            assert store.snapshot().revision!=original.revision
            assert calls[2]['feedback']['outcome']=='PROOF_FAILURE'
            assert all(p['files']=={k:v.decode() for k,v in sorted(base.items())} for p in calls)
            assert all((store.path/'revisions'/original.revision/'files'/k).read_bytes()==v for k,v in base.items())
            row=dict(case=name,records=records,scripted_requests=len(calls),actual_model_calls=0,original_bytes_preserved=True,accepted_reference_bytes_match=True)
            rows.append(row);atomic_json(folder/'summary.json',row);print(name,'passed',flush=True)
    atomic_json(out/'summary.json',dict(cases=rows,all_expected=True,model_calls=0,scripted_requests=12,verifier_checks=12))

if __name__=='__main__':main()
