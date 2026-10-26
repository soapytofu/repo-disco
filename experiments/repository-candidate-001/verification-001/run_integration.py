"""Compute-only guarded candidates from saved fixtures; zero model calls."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'code'),str(ROOT/'guards')]
from agenda import LocalAgenda, Object
from language.dafny.repository import snapshot_agenda_repository
from language.dafny.candidate import hashes, prepare_candidate, verify_candidate
from provider_guard import parse_response as provider_parse
from branch_guard import parse_response as branch_parse

def save(path,data): path.write_text(json.dumps(data,indent=2)+'\n')
def sources(folder): return {p.name:p.read_bytes() for p in folder.glob('*.dfy')}

async def main():
    if not os.environ.get('SLURM_JOB_ID') or 'login' in socket.gethostname():
        raise SystemExit('Requires Slurm compute node')
    out=ROOT/'verification-001';out.mkdir(exist_ok=False)
    for name in ['code','guards','fixtures']: shutil.copytree(ROOT/name,out/name)
    shutil.copy2(__file__,out/'run_integration.py')
    save(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),python=sys.version,
        dafny=subprocess.run(['dafny','--version'],capture_output=True,text=True,check=True).stdout.strip(),model_calls=0))
    reports=[];rejections=[]
    for family in ['inductive','branch']:
        for condition in ['shared','separate']:
            base=sources(ROOT/'fixtures'/family/(condition+'_empty'))
            agenda=LocalAgenda(checkpoint_interval=None,benchmark_codebase_time=None)
            try:
                paths={}
                for name,content in base.items():
                    paths[name]=await agenda.create_object(Object(path='sources/'+name,type='dafny-program',content=content))
                snapshot=await snapshot_agenda_repository(agenda,paths,'All.dfy')
                editable=['Facts.dfy'] if family=='inductive' else ['ClientA.dfy','ClientB.dfy']
                guards={}
                if family=='inductive':
                    def guard(before,after):
                        parsed,_=provider_parse(json.dumps({'Facts.dfy':after.decode()}),before.decode())
                        if parsed.encode()!=after: raise ValueError('guard changed bytes')
                    guards['Facts.dfy']=guard
                else:
                    originals={name:base[name].decode() for name in editable}
                    for name in editable:
                        def guard(before,after,name=name):
                            payload={**originals,name:after.decode()}
                            parsed,_=branch_parse(json.dumps(payload),originals)
                            if parsed[name].encode()!=after: raise ValueError('guard changed bytes')
                        guards[name]=guard
                for variant in ['reference', 'no_recursive_step' if family=='inductive' else 'wrong_boundary']:
                    fixture=sources(ROOT/'fixtures'/family/(condition+'_'+variant))
                    replacements={name:fixture[name] for name in editable}
                    candidate=prepare_candidate(snapshot,replacements,entry='All.dfy',expected_hashes=hashes(snapshot),guards=guards)
                    assert dict(candidate.files)==fixture
                    result=verify_candidate(candidate)
                    for name in base: assert (await agenda.get_object(paths[name])).content==base[name]
                    expected=0 if variant=='reference' else 4
                    report=dict(family=family,condition=condition,variant=variant,expected_exit=expected,
                        matched=result.verification.status==expected,agenda_bytes_unchanged=True,**result.evidence)
                    save(out/(family+'-'+condition+'-'+variant+'.json'),report);reports.append(report)
                    print(family,condition,variant,result.verification.status,flush=True)
                # Contract mutation must be rejected before any verification call.
                reference=sources(ROOT/'fixtures'/family/(condition+'_reference'))
                target=editable[0];changed=reference[target].replace(b'ensures ',b'ensures false && ',1)
                assert changed!=reference[target]
                try:
                    prepare_candidate(snapshot,{target:changed},entry='All.dfy',expected_hashes=hashes(snapshot),guards=guards)
                except ValueError as error:
                    rejections.append(dict(family=family,condition=condition,reason=str(error),verifier_calls=0))
                else: raise AssertionError('contract mutation accepted')
            finally: agenda._patch_executor.shutdown(wait=True)
    save(out/'guard-rejections.json',rejections)
    save(out/'summary.json',dict(checks=len(reports),matched=sum(r['matched'] for r in reports),guard_rejections=len(rejections),model_calls=0))
    if not all(r['matched'] for r in reports): raise SystemExit(1)

if __name__=='__main__': asyncio.run(main())
