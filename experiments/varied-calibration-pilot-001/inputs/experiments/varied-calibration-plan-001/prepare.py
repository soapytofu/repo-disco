"""Deterministic unapproved calibration proposal. No SDK, network, SSH or Dafny."""
import argparse,json,runpy,tempfile
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent;EXP=HERE.parent;REPO=EXP.parent
TASK=EXP/'varied-calibration-001';REV=TASK/'revision-002'
COMMON=EXP/'monorepo-reasoning-calibration-001/prepare.py'
common=runpy.run_path(str(COMMON))
load,save,sha,require,inventory=(common[k] for k in ['load','save','sha','require','inventory'])

def validate_plan(plan,tasks):
    byid={t['task_id']:t for t in tasks};require(len(byid)==16,'Sixteen distinct workspaces')
    reps=plan['replicates'];require(len(reps)==2,'Two replicates')
    flat=[]
    for rep in reps:
        require(len(rep)==4 and all(len(b)==4 for b in rep),'Four four-slot blocks')
        ids=sum(rep,[]);require(len(ids)==16 and set(ids)==set(byid),'Each workspace once per replicate')
        for block in rep:
            require(len({byid[t]['semantic_instance'] for t in block})==4,'Family balance within block')
            require(len({(byid[t]['depth'],byid[t]['sharing']) for t in block})==4,'Cell balance within block')
        for pos in range(4):
            require(len({byid[b[pos]]['semantic_instance'] for b in rep})==4,'Family position balance')
            require(len({(byid[b[pos]]['depth'],byid[b[pos]]['sharing']) for b in rep})==4,'Cell position balance')
        flat+=ids
    require(all(a!=b for a,b in zip(flat,flat[1:])),'No adjacent identical workspace')
    require(Counter(flat)=={tid:2 for tid in byid},'Two independent slots per workspace')
    require(plan['proposed_calls']==32 and plan['samples_per_workspace']==2,'Call bound')
    require(plan['max_output_tokens_total']==32*plan['inference_config']['maxTokens'],'Output bound')
    require(plan['sdk_total_max_attempts']==1 and plan['fresh_context_per_request'],'One dispatch attempt/fresh context')
    require(not any(plan[k] for k in ['execution_authorized','feedback','automatic_retries','reassign_unused','slurm_requeue','retry_or_repair_feedback']),'No authorization/retry/reassignment')

def prompt(task,seeds,rules):
    parts=['Complete the empty Prove bodies so the entire supplied workspace verifies.',
        'Required response keys and shape (replace the empty strings with proof bodies): '+json.dumps(dict.fromkeys(task['editable_files'],'')),
        (HERE/'syntax.txt').read_text().strip(),
        'Parameters: '+', '.join(rules['variables']),
        'Allowed lemma calls (argument counts): '+json.dumps(rules['calls'],sort_keys=True),
        'Allowed pure functions (argument counts): '+json.dumps(rules['pure'],sort_keys=True),
        'Only the explicitly listed calls are allowed, even if other definitions are visible in provider source. All files and declarations outside the requested empty bodies are immutable.',
        'Declared include/import map:\n'+json.dumps(common['source_map'](seeds),indent=2)]
    parts.extend(f'FILE {n}\n```dafny\n{s}```' for n,s in sorted(seeds.items()))
    parts.append('Return exactly one JSON object. Supply every requested body; omit outer lemma braces and do not modify contracts or imports.')
    return '\n\n'.join(parts)+'\n'

def evidence():
    index=load(TASK/'current-evidence.json');checks=load(REV/'checks.json')
    require(index['all_expected'] and index['current_controls']==126,'Incomplete fixture gate')
    require(index['outcomes']==dict(success=16,proof_failure=90,termination_failure=4,resolution_failure=16),'Unexpected diagnostic coverage')
    require(index['new_model_calls']==0,'Wrong evidence provenance')
    for n,h in load(REV/'manifest.json').items():require(sha(REV/n)==h,'Fixture/runtime input drift: '+n)
    byid={(c['task_id'],c['variant']):c for c in checks};seen=set();inputs=[]
    for row in index['rows']:
        key=(row['task_id'],row['variant']);require(key not in seen,'Duplicate evidence');seen.add(key)
        c=byid[key];p=TASK/row['evidence'];r=load(p)
        require(sha(p)==row['evidence_sha256'],'Raw evidence drift')
        require(r['source_sha256']==c['source_sha256']==row['source_sha256'],'Source/record drift')
        require(inventory(REV/c['path'])==c['source_sha256'],'Current fixture drift')
        require(inventory(p.parent/c['path'])==c['source_sha256'],'Archived fixture drift')
        require(r['matched'] and r['diagnostic']==c['expected'],'Diagnostic drift')
        require(r['exit_code']==dict(success=0,proof_failure=4,termination_failure=4,resolution_failure=2)[c['expected']],'Exit policy drift')
        require(r['attempts']==1 and r['model_calls']==0,'No retries/models in fixture gate')
        require('--verify-included-files' in r['command'],'Whole-repository verification required')
        text=(r['stdout']+'\n'+r['stderr']).lower();require('warning' not in text and 'parse error' not in text,'Unexpected warning/parse error')
        inputs+=[p,p.parent/'environment.json']
    require(seen==set(byid),'Missing control')
    return index,inputs

def build(out):
    plan=load(HERE/'plan.json');tasks=load(REV/'tasks.json');validate_plan(plan,tasks)
    prior=load(EXP/'witness-map-calibration-001/plan.json')
    for k in ['model_id','region','inference_config','verifier']:require(plan[k]==prior[k],'Prior setting continuity: '+k)
    index,input_files=evidence()
    guardpath=TASK/'protocol/body_guard.py';envelopepath=TASK/'protocol/extract_response.py'
    for n,h in load(TASK/'protocol/registry-freeze.json')['hashes'].items():require(sha(TASK/'protocol'/n)==h,'Registry drift: '+n)
    guard=common['guard'](guardpath);envelope=common['guard'](envelopepath)
    require(guard.VERSION==plan['guard_version'] and envelope.VERSION==plan['envelope_version'],'Policy version drift')
    out.mkdir(exist_ok=False);(out/'requests').mkdir();(out/'policy').mkdir();(out/'seeds').mkdir()
    (out/'policy/body_guard.py').write_bytes(guardpath.read_bytes());(out/'policy/extract_response.py').write_bytes(envelopepath.read_bytes())
    save(out/'tasks.json',tasks);save(out/'settings.json',plan)
    input_files+=[HERE/n for n in ['prepare.py','test_plan.py','plan.json','syntax.txt','system.txt']]
    input_files+=[COMMON,guardpath,envelopepath,TASK/'protocol/registry-freeze.json',TASK/'current-evidence.json',TASK/'structural-audit.json',REV/'manifest.json',REV/'tasks.json',REV/'checks.json',EXP/'witness-map-calibration-001/plan.json',EXP/'matched-corpus-002/plan.json']
    paths={};sizes=[]
    for task in tasks:
        tid=task['task_id'];seedpath=REV/'fixtures'/tid/'empty';refpath=REV/'fixtures'/tid/'reference'
        seeds=common['files'](seedpath);reference=common['files'](refpath)
        require(inventory(seedpath)==task['source_sha256'],'Seed drift')
        payload=common['body_payload'](guard,task,seeds,reference)
        candidate,decision=envelope.parse_response(json.dumps(payload),seeds,task,guard)
        require(candidate==reference,'Reference does not replay exactly')
        ref=next(r for r in index['rows'] if r['task_id']==tid and r['variant']=='reference')
        require(decision['body_guard']['candidate_sha256']==ref['source_sha256'],'Reference/evidence mismatch')
        rules=guard.policy(task);text=prompt(task,seeds,rules)
        for body in payload.values():require(body not in text,'Reference helper proof leaked into prompt')
        request=dict(modelId=plan['model_id'],system=[dict(text=(HERE/'system.txt').read_text())],messages=[dict(role='user',content=[dict(text=text)])],inferenceConfig=plan['inference_config'])
        paths[tid]='requests/'+tid+'.json';save(out/paths[tid],request)
        dest=out/'seeds'/tid;dest.mkdir()
        for n,s in seeds.items():(dest/n).write_text(s)
        input_files+=sorted(seedpath.glob('*.dfy'))+sorted(refpath.glob('*.dfy'))
        sizes.append(dict(task_id=tid,prompt_utf8_bytes=len(text.encode()),request_utf8_bytes=(out/paths[tid]).stat().st_size,editable_body_count=len(task['editable_files']),token_count=None))
    trials=[]
    for replicate,blocks in enumerate(plan['replicates'],1):
        for block,ids in enumerate(blocks,1):
            for position,tid in enumerate(ids,1):
                trials.append(dict(trial_id=f'varied-cal-{len(trials)+1:02d}',sequence=len(trials)+1,sample=replicate,block=block,position=position,task_id=tid,request_path=paths[tid],request_sha256=sha(out/paths[tid])))
    save(out/'trials.json',trials);save(out/'request-sizes.json',sizes)
    save(out/'freeze.json',dict(source_commit=plan['source_commit'],proposed_calls=32,execution_authorized=False,
        files=inventory(out),repository_inputs_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted(set(input_files))}))

def validate():
    with tempfile.TemporaryDirectory() as temp:
        out=Path(temp)/'frozen';build(out)
        require(inventory(out)==inventory(HERE/'frozen-001'),'Exact proposed-freeze drift')
    print('PASS: exact 16-prompt/32-slot rebuild, 126 reviewed controls, current policy and protected seeds. No model/verifier/network calls.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write',type=Path);a=p.parse_args()
    if a.write:build(a.write)
    else:validate()
