"""Replay exact saved bytes and deduplicate diagnostic compute; no native calls."""
import importlib.util
import json
from pathlib import Path
import body_guard as current
import common as c
from capture import write

REJECTED=[1,2,7,10,12,15,16]
GROUPS=[('vmc-swap',[1,2,15,16]),('vest-pair',[7,10]),('vmc-small-shuffle',[12])]

def legacy(root):
    spec=importlib.util.spec_from_file_location('legacy_guard',root/'legacy/body_guard.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def replay(root=c.ROOT, *, build=False):
    old=legacy(root);rows=[];candidates={};receipts={}
    tasks={t['id']:t for t in c.read(root/'tasks.json')}
    for i in range(1,17):
        d=root/'saved'/('slot-%02d'%i);slot=c.read(d/'slot.json');response=c.read(d/'response.json')
        expected=c.read(d/'extraction.json');tid=slot['task']
        c.require(response['stop_reason']=='end_turn' and response['retry_attempts']==0,'Parent response incomplete')
        try:
            previous,receipt=old.parse_response(response['text'],tid)
            observed=dict(outcome='ADMITTED',accepted=True,receipt=receipt)
        except (ValueError,TypeError,UnicodeError,RecursionError) as e:
            previous=None
            observed=dict(outcome='OUTPUT_REJECTED',accepted=False,error_type=type(e).__name__,reason=str(e))
        c.require(expected==observed,'Legacy replay differs')
        candidate,receipt=current.parse_response(response['text'],tid)
        c.require(receipt['prefix_sha256']==tasks[tid]['boundary']['prefix_sha256'] and
                  receipt['suffix_sha256']==tasks[tid]['boundary']['suffix_sha256'],'Protected boundary differs')
        if previous is not None:
            c.require(candidate==previous==(d/'legacy-candidate.txt').read_bytes(),'Previously admitted candidate changed')
        else:c.require(i in REJECTED,'Unexpected old rejection')
        candidates[i]=candidate;receipts[i]=receipt
        rows.append(dict(slot=i,task=tid,legacy_outcome=observed['outcome'],legacy_reason=observed.get('reason'),
                         response_sha256=c.sha(d/'response.json'),body_sha256=receipt['body_sha256'],
                         candidate_sha256=receipt['candidate_sha256'],receipt=receipt))
    c.require([r['slot'] for r in rows if r['legacy_outcome']=='OUTPUT_REJECTED']==REJECTED,'Old rejection set changed')
    groups=[]
    for tid,slots in GROUPS:
        first=slots[0];name='slot-%02d'%first;d=root/'candidates'/name
        c.require(all(candidates[s]==candidates[first] and
                      {k:v for k,v in receipts[s].items() if k!='envelope'}==
                      {k:v for k,v in receipts[first].items() if k!='envelope'}
                      for s in slots),'Reuse bytes differ')
        if build:
            d.mkdir(parents=True,exist_ok=False)
            (d/'candidate.txt').write_bytes(candidates[first]);write(d/'guard-receipt.json',receipts[first])
        else:
            c.require((d/'candidate.txt').read_bytes()==candidates[first] and c.read(d/'guard-receipt.json')==receipts[first],'Diagnostic candidate changed')
        groups.append(dict(slot=first,task=tid,project=tasks[tid]['project'],mapped_saved_slots=slots,
                           candidate_sha256=receipts[first]['candidate_sha256'],
                           body_sha256=receipts[first]['body_sha256'],
                           source_manifest_sha256=c.sha(root/'qualification/source-manifest.json'),
                           profile_sha256=c.sha(root/'qualification'/('coverage-001/profile.json' if tasks[tid]['project']=='dafny-vmc' else 'vest-coverage-001/profile.json'))))
    return dict(model_calls=0,native_invocations=0,legacy_admitted=9,legacy_rejected=7,new_admitted=16,
                unchanged_previously_admitted=9,diagnostic_outputs=7,distinct_candidates=3,rows=rows),groups

def preserve(repo):
    parent=c.read(c.ROOT/'parent-preservation.json')
    c.check_pins(repo,parent['files'])
    base=repo/'experiments/real-repository-repair-pilot-001'
    actual={p.relative_to(repo).as_posix() for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    c.require(actual==set(parent['files']),'Parent archive file set changed')
    return dict(parent_commit=parent['parent_commit'],unchanged_files=len(actual),original_score='7/16 qualified accepts',
                original_rejections=7,model_calls=0)

def main():
    root=c.ROOT;preserve(root.parent.parent)
    report,groups=replay(build=True);write(root/'offline-replay.json',report)
    write(root/'plan.json',dict(kind='retrospective_syntax_diagnostic',model_calls=0,native_invocations=3,
        saved_outputs=7,groups=groups,scope='Same full qualified native scopes and warning policy as original pilot',
        old_results_unchanged=True,candidate_bodies_unchanged=True,automatic_retries=False,
        reuse='Identical candidate files with identical parent inventory, toolchain and command; not independent trials',
        exclusions=['slot 8 frontend failure','slot 13 additional build warning','all other admitted candidates']))

if __name__=='__main__':main()
