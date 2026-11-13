"""Reproducible, offline-only repair/control prompt freeze. No execution path."""
from collections import Counter
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import protocol

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
EXP=HERE.parent
PILOT=EXP/'map-development-pilot-002'
DIAG=EXP/'map-order-diagnostic-002'
CSV_LINE=re.compile(r'^Results File: /tmp/repodisco-targets-[^/\r\n]+/TestResults/[^\r\n]+\.csv\r?\n?',re.M)
NOTICE='Detailed verifier diagnostics are not supplied for this attempt.'
OPEN='<verifier_feedback>\n';CLOSE='\n</verifier_feedback>'

def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def files(p):return {x.name:x.read_text() for x in p.glob('*.dfy')}
def require(c,m):
    if not c:raise ValueError(m)
def module(path):
    spec=importlib.util.spec_from_file_location(path.stem,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def feedback(raw):
    require(raw['exit_code']==4,'Expected saved proof failure')
    text,count=CSV_LINE.subn('',raw['stdout'])
    require(count==1,'Expected exactly one incidental CSV path')
    return dict(exit_code=raw['exit_code'],stdout=text,stderr=raw['stderr'])

def source_map(base):
    return {n:dict(includes=re.findall(r'^include "([^"]+)"',s,re.M),
        imports=[dict(alias=a,module=m,view=v or 'default') for a,m,v in
            re.findall(r'^\s*import (\w+) = (\w+)(?:`(\w+))?',s,re.M)]) for n,s in sorted(base.items())}

def prompt(task,base,rules,feedback_text):
    parts=['Repair the current proof bodies so the entire supplied workspace verifies. The current workspace failed whole-workspace verification.',
        'Return complete replacement bodies for these editable files: '+json.dumps(dict.fromkeys(task['editable_files'],'')),
        'The existing failing bodies are shown below. You may replace them with any proof within the permitted grammar; all other source bytes are immutable.',
        (HERE/'syntax.txt').read_text().strip(),
        'Parameters: '+', '.join(rules['variables']),
        'Allowed lemma calls (argument counts): '+json.dumps(rules['calls'],sort_keys=True),
        'Allowed pure functions (argument counts): '+json.dumps(rules['pure'],sort_keys=True),
        'Only explicitly listed calls are permitted, even if other definitions are visible. All files and declarations outside the requested bodies are immutable.',
        'Declared include/import map:\n'+json.dumps(source_map(base),indent=2)]
    parts.extend(f'FILE {n}\n```dafny\n{s}```' for n,s in sorted(base.items()))
    parts += [OPEN+feedback_text+CLOSE,
        'Return exactly one JSON object containing all requested complete replacement bodies. Omit outer lemma braces and preserve the contracts and imports.']
    return '\n\n'.join(parts)+'\n'

def validate(plan,tasks):
    require(plan['proposed_calls']==8 and plan['max_calls_per_trial']==1,'Eight one-call trials required')
    require(plan['sdk_total_max_attempts']==1 and plan['fresh_context_per_request'],'One dispatch/fresh context')
    require(not any(plan[k] for k in ['execution_authorized','feedback_after_repair','automatic_retries','reassign_unused','slurm_requeue']),'Unauthorized execution/retry')
    require(plan['max_output_tokens_total']==8*plan['inference_config']['maxTokens'],'Token bound')
    require(set(tasks)==set(plan['parent_trials']) and len(tasks)==4,'Four parent observations')
    require(len(plan['order'])==8 and Counter(tuple(x) for x in plan['order'])==
        Counter((tid,arm) for tid in tasks for arm in plan['feedback_conditions']),'Parent/arm coverage')
    cells=[(tasks[t]['sharing'],a) for t,a in plan['order']]
    require(cells[4:]==list(reversed(cells[:4])) and len(set(cells[:4]))==4,'Reverse counterbalance')
    for c in set(cells):require(sum(i+1 for i,x in enumerate(cells) if x==c)==9,'Cell position balance')

def build(out):
    plan=load(HERE/'plan.json');prior=load(PILOT/'results-review.json')
    require(prior['all_completed'] and prior['dispatched']==16 and prior['verified']==12,'Original completed cohort')
    archive=load(PILOT/'model-001-sha256.json');require(len(archive)==812,'Archive count')
    for n,h in archive.items():require(sha(PILOT/'model-001'/n)==h,'Original archive changed: '+n)
    diagnostic=load(DIAG/'results-review.json');require(diagnostic['all_expected'] and diagnostic['model_calls']==0,'Analyst diagnostic gate')
    for n,h in load(DIAG/'verification-001-sha256.json').items():require(sha(DIAG/'verification-001'/n)==h,'Diagnostic archive changed')
    require(diagnostic['reviewer_sha256']==sha(DIAG/'review.py'),'Diagnostic reviewer changed')
    original_plan=load(PILOT/'frozen-001/settings.json')
    for key in ['model_id','region','inference_config','verifier']:require(plan[key]==original_plan[key],'Setting changed')
    tasks={tid:load(PILOT/'model-001'/tid/'task.json') for tid in plan['parent_trials']};validate(plan,tasks)
    out.mkdir(exist_ok=False)
    for n in ['parents','requests','policy']:(out/n).mkdir()
    inputs=[HERE/n for n in ['prepare.py','test_plan.py','protocol.py','plan.json','system.txt','syntax.txt']]
    inputs += [PILOT/'results-review.json',PILOT/'model-001-sha256.json',PILOT/'frozen-001/freeze.json',
        PILOT/'frozen-001/settings.json',DIAG/'results-review.json',DIAG/'verification-001-sha256.json',DIAG/'review.py']
    policy=PILOT/'frozen-001/policy/merge_restrict'
    for n in ['body_guard.py','extract_response.py']:
        shutil.copy2(policy/n,out/'policy'/n);inputs.append(policy/n)
    guard=module(policy/'body_guard.py');envelope=module(policy/'extract_response.py')
    parents={};paths={};comparisons=[];requests={};replays=[]
    for tid,task in tasks.items():
        folder=PILOT/'model-001'/tid;base=files(folder/'candidate');seedpath=PILOT/'frozen-001/seeds'/task['task_id'];seed=files(seedpath)
        raw=load(folder/'verification.json');require(raw['source_sha256']==protocol.hashes(base),'Parent source association')
        require(raw['attempts']==1 and raw['model_calls']==0 and task['depth']=='deep' and task['semantic_instance']=='merge_restrict','Parent scope')
        rendered,decision=protocol.apply_response(load(folder/'response.json')['text'],base,seed,task,raw['source_sha256'],guard,envelope)
        require(rendered==base,'Failing response reconstruction')
        require(load(folder/'extraction.json')==dict(accepted=True,**decision['original_guard_decision']),'Original admission')
        fixed=files(DIAG/'fixtures'/(tid+'-reordered'));bodies={}
        for n in task['editable_files']:
            pre,suf=guard.split_seed(seed[n]);bodies[n]=fixed[n][len(pre):-len(suf)]
        repaired,_=protocol.apply_response(json.dumps(bodies),base,seed,task,raw['source_sha256'],guard,envelope)
        require(repaired==fixed,'Verified analyst repair is not representable')
        dcase=next(c for c in diagnostic['checks'] if c['parent_trial']==tid)
        require(protocol.hashes(fixed)==dcase['source_sha256'] and dcase['matched'],'Analyst source mismatch')
        replays.append(dict(parent_trial=tid,original_exact=True,analyst_repair_exact=True,diagnostic_case=dcase['case_id']))
        dest=out/'parents'/tid;dest.mkdir()
        for n in ['task.json','trial.json','response.json','extraction.json','verification.json']:
            shutil.copy2(folder/n,dest/n);inputs.append(folder/n)
        for name,source in [('base',folder/'candidate'),('template',seedpath)]:
            shutil.copytree(source,dest/name);inputs += list(source.glob('*.dfy'))
        inputs += list((DIAG/'fixtures'/(tid+'-reordered')).glob('*.dfy'))
        cleaned=feedback(raw);save(dest/'feedback.json',cleaned)
        parents[tid]=dict(task_id=task['task_id'],sharing=task['sharing'],source_sha256=raw['source_sha256'],
            base_path='parents/'+tid+'/base',template_path='parents/'+tid+'/template',
            task_path='parents/'+tid+'/task.json',feedback_path='parents/'+tid+'/feedback.json',
            original_verifier_path='parents/'+tid+'/verification.json')
        pair={}
        for arm in plan['feedback_conditions']:
            supplied=json.dumps(cleaned,indent=2) if arm=='verifier_diagnostics' else NOTICE
            message=prompt(task,base,guard.policy(task),supplied)
            require(all(body not in message for body in bodies.values()),'Analyst solution leaked')
            payload=dict(modelId=plan['model_id'],system=[dict(text=(HERE/'system.txt').read_text())],
                messages=[dict(role='user',content=[dict(text=message)])],inferenceConfig=plan['inference_config'])
            path='requests/deep-'+task['sharing']+'-'+arm+'.json'
            if path in requests:require(payload==requests[path],'Duplicate workspace prompt mismatch')
            else:save(out/path,payload);requests[path]=payload
            paths[(tid,arm)]=path;pair[arm]=message
        require(pair['verifier_diagnostics'].replace(OPEN+json.dumps(cleaned,indent=2)+CLOSE,OPEN+NOTICE+CLOSE)==pair['failure_notice_only'],'Non-feedback condition change')
        comparisons.append(dict(parent_trial=tid,only_feedback_block_differs=True,removed_csv_path_lines=1,
            original_stdout_sha256=hashlib.sha256(raw['stdout'].encode()).hexdigest(),
            normalized_stdout_sha256=hashlib.sha256(cleaned['stdout'].encode()).hexdigest()))
    require(len(requests)==4 and len({tuple(sorted(p['source_sha256'].items())) for p in parents.values()})==2,'Unique input count')
    trials=[dict(trial_id=f'map-repair-{i:02d}',sequence=i,parent_trial=tid,sharing=tasks[tid]['sharing'],
        feedback_condition=arm,request_path=paths[(tid,arm)],request_sha256=sha(out/paths[(tid,arm)]),
        replicate=1 if i<=4 else 2,max_calls=1) for i,(tid,arm) in enumerate(plan['order'],1)]
    scope=load(PILOT/'frozen-001/target-scope.json');scope['tasks']={k:v for k,v in scope['tasks'].items() if k.startswith('merge_restrict-deep-')}
    inputs.append(PILOT/'frozen-001/target-scope.json')
    save(out/'target-scope.json',scope);save(out/'settings.json',plan);save(out/'parents.json',parents);save(out/'trials.json',trials)
    save(out/'prompt-review.json',dict(condition_comparisons=comparisons,unique_requests=4,unique_bases=2,
        reference_repairs_in_prompts=False,analyst_advice_in_prompts=False,feedback_after_repair=False))
    save(out/'offline-evidence.json',dict(new_model_calls=0,new_dafny_runs=0,original_archive_files_preserved=812,
        original_score_unchanged='12/16',verified_analyst_replays=replays,diagnostic_report_sha256=sha(DIAG/'results-review.json')))
    save(out/'request-sizes.json',[dict(path=n,utf8_bytes=(out/n).stat().st_size,token_count=None) for n in sorted(requests)])
    save(out/'freeze.json',dict(source_commit=plan['source_commit'],proposed_calls=8,execution_authorized=False,
        files=inventory(out),repository_inputs_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted(set(inputs))}))

def rebuild():
    with tempfile.TemporaryDirectory() as tmp:
        out=Path(tmp)/'freeze';build(out);require(inventory(out)==inventory(HERE/'frozen-001'),'Frozen plan drift')
    print('PASS: eight one-call repair/control slots, four exact payloads, two unique failing bases; original 812 files preserved; zero model/Dafny calls.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--write',type=Path);args=parser.parse_args()
    if args.write:build(args.write)
    else:rebuild()
