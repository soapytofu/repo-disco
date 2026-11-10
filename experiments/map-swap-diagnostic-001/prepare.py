"""Prepare six separate zero-model diagnostics; refuse existing input archives."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
PILOT = ROOT.parent / 'varied-calibration-pilot-001'
TASKROOT = ROOT.parent / 'varied-calibration-001/revision-002'

def load(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p): return {f.name: f.read_text() for f in sorted(p.glob('*.dfy'))}
def hashes(fs): return {n: hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(fs.items())}
def save(p,v):
    with p.open('x') as f: f.write(json.dumps(v,indent=2)+'\n')
def module(name,p):
    spec=importlib.util.spec_from_file_location(name,p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def main():
    guard=module('new_guard',ROOT/'policy/body_guard.py')
    old=module('old_guard',ROOT/'policy/old_body_guard.py')
    env=module('envelope',ROOT/'policy/extract_response.py')
    tasks=load(TASKROOT/'tasks.json');save(ROOT/'tasks.json',tasks)
    originals={str(p.relative_to(PILOT)):sha(p) for p in sorted(PILOT.rglob('*')) if p.is_file()}
    save(ROOT/'original-pilot-sha256.json',originals)
    pins={}
    for task in tasks:
        src=TASKROOT/'fixtures'/task['task_id']/'empty'
        shutil.copytree(src,ROOT/'seeds'/task['task_id'])
        for p in src.glob('*.dfy'): pins[str(p.relative_to(REPO))]=sha(p)
    for parent in sorted((PILOT/'model-001').glob('varied-cal-*')):
        dest=ROOT/'parents'/parent.name;dest.mkdir(parents=True)
        for name in ('task.json','trial.json','result.json','response.json','extraction.json','verification.json','candidate-hashes.json'):
            p=parent/name
            if p.exists():shutil.copy2(p,dest/name);pins[str(p.relative_to(REPO))]=sha(p)
        if (parent/'candidate').exists():
            shutil.copytree(parent/'candidate',dest/'candidate')
            for p in (parent/'candidate').glob('*.dfy'):pins[str(p.relative_to(REPO))]=sha(p)
    replays=[]
    for c in load(TASKROOT/'checks.json'):
        task=next(t for t in tasks if t['task_id']==c['task_id'])
        seed=files(ROOT/'seeds'/task['task_id']);target=files(TASKROOT/c['path']);bodies={}
        for name in task['editable_files']:
            pre,suf=old.split_seed(seed[name]);assert target[name].startswith(pre) and target[name].endswith(suf)
            bodies[name]=target[name][len(pre):-len(suf)]
        replays.append(dict(task_id=c['task_id'],variant=c['variant'],bodies=bodies,
                            admitted=c['expected']!='resolution_failure',source_sha256=c['source_sha256']))
    save(ROOT/'control-replays.json',replays)
    definitions=[('deep_shared_both',5,('k','j'),'success'),
                 ('deep_separate_both',15,('k','j'),'success'),
                 ('deep_shared_k_only',5,('k',),'proof_failure'),
                 ('deep_shared_j_only',5,('j',),'proof_failure'),
                 ('quantifier_original',27,(),'success'),
                 ('quantifier_false_control',27,(),'proof_failure')]
    cases=[];checks=[]
    for variant,index,keys,expected in definitions:
        trial=f'varied-cal-{index:02d}';parent=ROOT/'parents'/trial
        task=load(parent/'task.json');seed=files(ROOT/'seeds'/task['task_id'])
        raw=load(parent/'response.json')['text'];payload,_=env.extract_json(raw);original=json.loads(payload)
        bodies=dict(original);edits={}
        if keys:
            needle='      O2.SwapAt(m, k, j, q);'
            for name,body in bodies.items():
                assert body.count(needle)==1
                added=''.join(f'      O2.SwapAt(m, k, j, {key});\n' for key in keys)
                bodies[name]=body.replace(needle,added+needle);edits[name]=len(keys)
        elif variant=='quantifier_false_control':
            name=task['editable_files'][0]
            bodies[name]='assert forall fresh :: fresh == 0;\n'+bodies[name];edits[name]=1
        encoded=raw if variant=='quantifier_original' else json.dumps(bodies,indent=2)+'\n'
        policy=old if keys else guard
        candidate,decision=env.parse_response(encoded,seed,task,policy)
        for name in seed:
            if name not in task['editable_files']:assert candidate[name]==seed[name]
            else:
                pre,suf=old.split_seed(seed[name]);assert candidate[name]==pre+bodies[name]+suf
        dest=ROOT/'fixtures'/variant;dest.mkdir(parents=True)
        for name,text in candidate.items():(dest/name).write_text(text)
        meta=ROOT/'responses'/variant;meta.mkdir(parents=True)
        (meta/'body.json').write_text(encoded);save(meta/'extraction.json',decision)
        cases.append(dict(variant=variant,source_trial=trial,original_outcome=load(parent/'result.json')['outcome'],
            task_id=task['task_id'],policy=policy.VERSION,analyst_proof_edit=bool(edits),added_statements_per_body=edits,
            raw_response_unchanged=encoded==raw,body_strings_unchanged=bodies==original,new_model_calls=0,
            candidate_sha256=hashes(candidate),expected=expected))
        checks.append(dict(task_id=task['task_id'],variant=variant,path='fixtures/'+variant,
                           expected=expected,source_sha256=hashes(candidate)))
    save(ROOT/'cases.json',cases);save(ROOT/'checks.json',checks);save(ROOT/'original-input-sha256.json',pins)
    print('Prepared six verifier-only diagnostics, 32 saved responses and 126 control replays. No model calls.')

if __name__=='__main__': main()
