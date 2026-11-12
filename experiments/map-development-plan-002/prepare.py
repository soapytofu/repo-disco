"""Offline prospective freeze. No model client, network or process invocation."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile

HERE=Path(__file__).resolve().parent
EXP=HERE.parent
REPO=EXP.parent


def load(p):return json.loads(p.read_text())
def save(p,data):p.write_text(json.dumps(data,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def require(value,message):
    if not value:raise ValueError(message)
def files(p):return {x.name:x.read_text() for x in p.glob('*.dfy')}
def module(path):
    spec=importlib.util.spec_from_file_location(path.parent.parent.name+'_'+path.stem,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def validate(plan,tasks):
    require(plan['study']=='map-development-plan-002','Fresh study identity')
    require(not any(plan[k] for k in ['semantic_hints_added','prior_responses_reused','prior_unused_calls_reassigned']),'Fresh syntax-only scope')
    ids={t['task_id'] for t in tasks}
    require(len(tasks)==len(ids)==8,'Eight workspaces required')
    require(plan['proposed_calls']==16 and plan['samples_per_workspace']==2,'Sixteen-call bound')
    require(plan['max_output_tokens_total']==16*plan['inference_config']['maxTokens'],'Output bound')
    require(plan['sdk_total_max_attempts']==1 and plan['fresh_context_per_request'],'Fresh requests/no retry')
    require(not any(plan[k] for k in ['execution_authorized','automatic_retries','feedback','reassign_unused','slurm_requeue']),'Unapproved scope')
    reps=plan['replicates'];require(len(reps)==2,'Two samples')
    for seq in reps:require(len(seq)==8 and set(seq)==ids,'Each workspace once per sample')
    flat=sum(reps,[]);require(all(a!=b for a,b in zip(flat,flat[1:])),'Adjacent duplicate request')
    require(Counter(flat)=={tid:2 for tid in ids},'Independent slot counts')
    for pos in range(4):
        cells=[]
        for rep in reps:
            for instance in plan['semantic_instances']:
                row=[x for x in rep if x.startswith(instance+'-')]
                cells.append(row[pos][len(instance)+1:])
        require(set(cells)==set(plan['cells']),'Relative cell-position balance')


def source_map(seed):
    return {n:dict(includes=re.findall(r'^include "([^"]+)"',s,re.M),
        imports=[dict(alias=a,module=m,view=v or 'default') for a,m,v in
            re.findall(r'^\s*import (\w+) = (\w+)(?:`(\w+))?',s,re.M)]) for n,s in sorted(seed.items())}


def prompt(task,seed,rules):
    parts=['Complete the empty Prove bodies so the entire supplied workspace verifies.',
        'Required response keys and shape (replace the empty strings with proof bodies): '+json.dumps(dict.fromkeys(task['editable_files'],'')),
        (HERE/'syntax.txt').read_text().strip(),
        'Parameters: '+', '.join(rules['variables']),
        'Allowed lemma calls (argument counts): '+json.dumps(rules['calls'],sort_keys=True),
        'Allowed pure functions (argument counts): '+json.dumps(rules['pure'],sort_keys=True),
        'Only the explicitly listed calls are allowed, even if other definitions are visible in provider source. All files and declarations outside the requested empty bodies are immutable.',
        'Declared include/import map:\n'+json.dumps(source_map(seed),indent=2)]
    parts.extend(f'FILE {n}\n```dafny\n{s}```' for n,s in sorted(seed.items()))
    parts.append('Return exactly one JSON object. Supply every requested body; omit outer lemma braces and do not modify contracts or imports.')
    return '\n\n'.join(parts)+'\n'


def evidence(root):
    inputs=[root/'manifest.json',root/'tasks.json',root/'checks.json']
    for n,h in load(root/'manifest.json').items():require(sha(root/n)==h,'Runtime/source drift: '+n)
    checks=load(root/'checks.json');rows=[]
    for phase,outname in [('core','verification-001'),('negatives','verification-002')]:
        report=load(root/(outname+'-review.json'));out=root/outname
        selected=[c for c in checks if c['phase']==phase];raw=load(out/'summary.json')
        require(report['all_expected'] and report['planned']==report['matched']==len(selected),'Incomplete phase')
        require(report['manifest_sha256']==sha(root/'manifest.json')==sha(out/'manifest.json'),'Phase freeze drift')
        require(report['summary_sha256']==sha(out/'summary.json'),'Phase summary drift')
        require(raw['completed']==len(raw['results'])==len(selected),'Incomplete evidence')
        inputs += [root/(outname+'-review.json'),out/'summary.json',out/'environment.json',out/'manifest.json']
        for c,r in zip(selected,raw['results']):
            path=out/(c['task_id']+'-'+c['variant']+'.json')
            require(load(path)==r and r['task_id']==c['task_id'] and r['variant']==c['variant'],'Record association')
            require(r['source_sha256']==c['source_sha256']==inventory(root/c['path'])==inventory(out/c['path']),'Fixture drift')
            require(r['matched'] and r['diagnostic']==c['expected'],'Diagnostic mismatch')
            require(r['exit_code']=={'success':0,'proof_failure':4,'resolution_failure':2}[c['expected']],'Wrong exit')
            require(r['model_calls']==0 and r['attempts']==1 and '--verify-included-files' in r['command'],'Wrong provenance')
            require('warning' not in (r['stdout']+r['stderr']).lower() and 'parse errors' not in r['stdout'].lower(),'Warning/parse mismatch')
            inputs.append(path);rows.append(dict(task_id=c['task_id'],variant=c['variant'],diagnostic=r['diagnostic'],evidence_path=str(path.relative_to(REPO)),evidence_sha256=sha(path),source_sha256=r['source_sha256']))
    require(len(rows)==38 and Counter(r['diagnostic'] for r in rows)==dict(success=4,proof_failure=30,resolution_failure=4),'Control coverage')
    return rows,inputs


def measurement(out,tasks):
    """Bind the measured logger schema, fixed dependency scope and raw controls."""
    root=EXP/'target-completion-diagnostic-001'
    analyzer=module(root/'review_targets.py');report=load(root/'target-review.json')
    require(report['new_model_calls']==0 and report['analyst_controls'],'Not an analyst gate')
    require(report['analysis_code_sha256']==sha(root/'review_targets.py'),'Analysis code drift')
    inputs=[root/'review_targets.py',root/'test_review.py',root/'target-review.json']
    for sub,expected,reported in [
        (root,analyzer.EXPECTED,report['cases']),
        (root/'restriction-001',analyzer.RESTRICTION_EXPECTED,[report['restriction_compatibility']])]:
        arch=sub/'verification-001';cases=load(arch/'cases.json')
        require(load(sub/'manifest.json')==load(arch/'manifest.json'),'Logger manifest drift')
        for n,h in load(arch/'manifest.json').items():
            require(sha(arch/n)==h and sha(sub/n)==h,'Logger input drift: '+n)
        require(len(cases)==len(reported),'Logger coverage drift')
        for case,result in zip(cases,reported):
            raw=load(arch/(case['case_id']+'.json'))
            require(raw['source_sha256']==case['source_sha256']==inventory(arch/case['path']),'Logger fixture drift')
            require(raw['attempts']==1 and raw['model_calls']==0,'Logger provenance')
            score=analyzer.scores(raw['csv'],case,expected)
            require(all(result[k]==v for k,v in score.items()),'Logger interpretation drift')
            require(raw['exit_code']==case['expected_exit'],'Logger exit mismatch')
            require(raw['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy'],'Logger command drift')
            for n,t in raw['csv'].items():
                require((arch/'raw-csv'/case['case_id']/n).read_text()==t,'Raw CSV mismatch')
                require(hashlib.sha256(t.encode()).hexdigest()==raw['csv_sha256'][n],'CSV hash mismatch')
        inputs += [sub/'manifest.json',*[p for p in arch.rglob('*') if p.is_file()]]
    scopes={}
    for task in tasks:
        shared=task['sharing']=='shared'
        units=analyzer.EXPECTED if task['semantic_instance']=='fresh_move' else analyzer.RESTRICTION_EXPECTED
        scopes[task['task_id']]=dict(
            expected_units={n:sorted(kinds) for n,kinds in units.items()},
            editable_targets=['HelperA.Prove'] if shared else ['HelperA.Prove','HelperB.Prove'],
            target_dependencies={'HelperA.Prove':[],'HelperB.Prove':['HelperA.Prove'] if shared else [],
                'ClientA.Target':['HelperA.Prove'],'ClientB.Target':['HelperB.Prove']})
        require(task['editable_files']==(['HelperA.dfy'] if shared else ['HelperA.dfy','HelperB.dfy']),'Editable metric denominator')
    save(out/'target-scope.json',dict(tasks=scopes,
        unit='Named lemma contract, all obligations; never individual CSV rows or ensures clauses',
        supplied_clients_are_model_credit=False,provider_obligations_are_model_credit=False,
        missing_or_malformed_csv='Measurement unavailable and execution review required; never infer target success',
        invalid_output='Primary non-pass; no credited editable completion; per-declaration verification unavailable',
        primary='Guard admission plus strict whole-workspace exit zero without warnings',
        diagnostic_report_sha256=sha(root/'target-review.json'),
        interpretation_sha256=sha(root/'review_targets.py')))
    return inputs


def prior_cohort(out):
    """Read-only provenance: no old output or diagnostic is placed in a prompt."""
    old=EXP/'map-development-plan-001';pilot=EXP/'map-development-pilot-001'
    diag=EXP/'map-order-diagnostic-001';plan=load(HERE/'plan.json')
    require(sha(old/'frozen-001/freeze.json')==plan['prior_proposal_freeze_sha256'],'Prior freeze drift')
    freeze=load(old/'frozen-001/freeze.json')
    for n,h in freeze['files'].items():require(sha(old/'frozen-001'/n)==h,'Prior frozen file changed: '+n)
    hashes=load(pilot/'model-001-sha256.json')
    require(len(hashes)==646,'Prior archive count')
    for n,h in hashes.items():require(sha(pilot/'model-001'/n)==h,'Prior archive changed: '+n)
    ledger=load(pilot/'model-001/requests/ledger.json');results=load(pilot/'results-review.json')
    require(ledger['closed'] and ledger['closed_reason']=='transport_or_response_failure','Prior run must stay closed')
    require([r['status'] for r in ledger['reservations']]==['COMPLETED']*9+['AMBIGUOUS_OR_UNSAVED'],'Prior request accounting')
    require((results['dispatched'],results['returned'],results['verified'],results['all_completed'])==(10,9,6,False),'Prior outcome accounting')
    diagnostic=load(diag/'results-review.json')
    require(diagnostic['all_expected'] and diagnostic['model_calls']==0 and diagnostic['prior_score_unchanged'],'Diagnostic provenance')
    require([c['actual_exit'] for c in diagnostic['checks']]==[4,0,0,0],'Diagnostic outcomes')
    require(diagnostic['reviewer_sha256']==sha(diag/'review.py'),'Diagnostic reviewer drift')
    inputs=[old/'frozen-001/freeze.json',old/'syntax.txt',old/'system.txt',
        pilot/'model-001-sha256.json',pilot/'model-001/requests/ledger.json',pilot/'results-review.json',
        diag/'results-review.json',diag/'review.py',diag/'manifest.json']
    save(out/'prior-cohort-provenance.json',dict(
        preserved_model_archive_files=len(hashes),prior_dispatched=10,prior_returned=9,
        prior_strict_passes=6,prior_ambiguous_requests=1,prior_undispatched=6,
        prior_run_closed=True,prior_scores_unchanged=True,new_calls_proposed=16,
        calls_or_responses_reassigned=0,diagnostic_model_calls=0,
        diagnostic_is_analyst_authored=True,
        evidence_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs}))
    return inputs


def syntax_only_review(out):
    """Assert that every task-facing byte outside the syntax instructions is fixed."""
    old=EXP/'map-development-plan-001';frozen=old/'frozen-001'
    for name in ['tasks.json','reviewed-controls.json','policy-bindings.json','target-scope.json']:
        require((out/name).read_bytes()==(frozen/name).read_bytes(),'Non-syntax metadata change: '+name)
    for name in ['seeds','policy']:
        require(inventory(out/name)==inventory(frozen/name),'Non-syntax source change: '+name)
    before=(old/'syntax.txt').read_text().strip();after=(HERE/'syntax.txt').read_text().strip()
    rows=[]
    for path in sorted((out/'requests').glob('*.json')):
        original=load(frozen/'requests'/path.name);current=load(path)
        text=original['messages'][0]['content'][0]['text']
        require(text.count(before)==1,'Ambiguous old syntax segment')
        original['messages'][0]['content'][0]['text']=text.replace(before,after)
        original['system']=[dict(text=(HERE/'system.txt').read_text())]
        require(original==current,'Unexpected request change: '+path.name)
        rows.append(dict(request=path.name,prior_sha256=sha(frozen/'requests'/path.name),new_sha256=sha(path)))
    previous=load(frozen/'trials.json');current=load(out/'trials.json')
    require(not {r['trial_id'] for r in previous}&{r['trial_id'] for r in current},'Trial ID reused')
    for a,b in zip(previous,current):
        require(all(a[k]==b[k] for k in ['sequence','sample','position','task_id','request_path']),'Trial order change')
    save(out/'syntax-change-review.json',dict(requests=rows,changed_prompt_sections=['system','syntax_instructions'],
        tasks_guards_metrics_and_order_unchanged=True,semantic_hints_added=False,
        policy_changes=0,saved_response_reuse=0,all_trial_ids_fresh=True))


def build(out):
    plan=load(HERE/'plan.json');tasks=[];roots={};inputs=[];reviewed=[]
    for instance,rel in plan['source_experiments'].items():
        root=EXP/rel;rows,paths=evidence(root);reviewed+=rows;inputs+=paths
        for task in load(root/'tasks.json'):
            require(task['semantic_instance']==instance and not task['held_out'],'Task family/split mismatch')
            roots[task['task_id']]=root;tasks.append(task)
    validate(plan,tasks)
    prior=load(EXP/'varied-calibration-plan-001/plan.json')
    for key in ['model_id','region','inference_config','verifier']:require(plan[key]==prior[key],'Prior setting mismatch')
    out.mkdir(exist_ok=False);(out/'requests').mkdir();(out/'policy').mkdir();(out/'seeds').mkdir()
    inputs+=prior_cohort(out)
    save(out/'tasks.json',tasks);save(out/'settings.json',plan);save(out/'reviewed-controls.json',reviewed)
    inputs+=measurement(out,tasks)
    input_names=['prepare.py','test_plan.py','syntax.txt','system.txt','plan.json']
    inputs += [HERE/n for n in input_names]+[EXP/'varied-calibration-plan-001/plan.json',EXP/'matched-corpus-002/plan.json']
    paths={};sizes=[];bindings={}
    for task in tasks:
        tid=task['task_id'];instance=task['semantic_instance'];root=roots[tid]
        gpath=root/'policy/body_guard.py';epath=root/'policy/extract_response.py';guard=module(gpath);envelope=module(epath)
        target=out/'policy'/instance
        if not target.exists():
            target.mkdir();(target/'body_guard.py').write_bytes(gpath.read_bytes());(target/'extract_response.py').write_bytes(epath.read_bytes())
        bindings[tid]=dict(body_guard='policy/'+instance+'/body_guard.py',envelope='policy/'+instance+'/extract_response.py',guard_version=guard.VERSION)
        seedpath=root/'fixtures'/tid/'empty';refpath=root/'fixtures'/tid/'reference'
        seed=files(seedpath);reference=files(refpath);bodies={}
        require(inventory(seedpath)==task['source_sha256'],'Seed drift')
        for n in task['editable_files']:
            prefix,suffix=guard.split_seed(seed[n]);require(reference[n].startswith(prefix) and reference[n].endswith(suffix),'Protected reference drift')
            bodies[n]=reference[n][len(prefix):-len(suffix)]
        candidate,_=envelope.parse_response(json.dumps(bodies),seed,task,guard)
        require(candidate==reference,'Reference reconstruction changed')
        text=prompt(task,seed,guard.policy(task))
        require(all(body not in text for body in bodies.values()),'Reference proof in prompt')
        payload=dict(modelId=plan['model_id'],system=[dict(text=(HERE/'system.txt').read_text())],messages=[dict(role='user',content=[dict(text=text)])],inferenceConfig=plan['inference_config'])
        paths[tid]='requests/'+tid+'.json';save(out/paths[tid],payload)
        dest=out/'seeds'/tid;dest.mkdir()
        for n,s in seed.items():(dest/n).write_text(s)
        sizes.append(dict(task_id=tid,request_utf8_bytes=(out/paths[tid]).stat().st_size,editable_body_count=len(task['editable_files']),token_count=None))
        inputs += [gpath,epath,*seedpath.glob('*.dfy'),*refpath.glob('*.dfy')]
    trials=[]
    for sample,rep in enumerate(plan['replicates'],1):
        for pos,tid in enumerate(rep,1):
            trials.append(dict(trial_id=f'map-balanced-{len(trials)+1:02d}',sequence=len(trials)+1,sample=sample,position=pos,task_id=tid,request_path=paths[tid],request_sha256=sha(out/paths[tid])))
    save(out/'policy-bindings.json',bindings);save(out/'trials.json',trials);save(out/'request-sizes.json',sizes)
    syntax_only_review(out)
    save(out/'freeze.json',dict(source_commit=plan['source_commit'],proposed_calls=16,execution_authorized=False,
        files=inventory(out),repository_inputs_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted(set(inputs))}))


def rebuild():
    with tempfile.TemporaryDirectory() as temp:
        p=Path(temp)/'freeze';build(p);require(inventory(p)==inventory(HERE/'frozen-001'),'Exact freeze changed')
    print('PASS: eight requests / sixteen fresh slots, 76 reviewed controls, syntax-only prompt changes, 646 original model files preserved; no model/verifier/network calls.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write',type=Path);a=p.parse_args()
    if a.write:build(a.write)
    else:rebuild()
