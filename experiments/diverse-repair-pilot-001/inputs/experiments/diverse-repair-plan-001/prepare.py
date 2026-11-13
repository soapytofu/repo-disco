"""Deterministic offline prompt/feedback freeze for constructed development faults."""
from pathlib import Path
from collections import Counter
import hashlib,importlib.util,json,re,shutil,tempfile
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
TASKS=HERE.parent/'diverse-repair-tasks-001'
CURRENT=TASKS/'revision-003'
OPEN='<verifier_feedback>\n';CLOSE='\n</verifier_feedback>'
NOTICE='Detailed verifier diagnostics are not supplied for this attempt.'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=lambda p:{x.name:x.read_text() for x in sorted(p.glob('*.dfy'))}
hashes=lambda fs:{n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(fs.items())}

def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def module(p):
    spec=importlib.util.spec_from_file_location(p.stem+'_freeze',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def feedback(ev):
    assert ev['exit_code']==4 and ev['model_calls']==0 and ev['attempts']==1
    lines=ev['stdout'].splitlines(keepends=True);removed=[s for s in lines if s.startswith('Results File: ')]
    assert len(removed)==1 and re.fullmatch(r'Results File: /tmp/repodisco-targets-[^/]+/TestResults/[^\n]+\n?',removed[0])
    return dict(exit_code=4,stdout=''.join(s for s in lines if s not in removed),stderr=ev['stderr'])

def render(task,base,rules,diagnostic):
    parts=['The supplied candidate fails whole-workspace verification. Repair the requested lemma bodies while preserving the full repository contracts.',
      'Editable files: '+json.dumps(task['editable_files']),
      'Proof-body syntax:\n'+(HERE/'syntax.txt').read_text(),
      'Parameters: '+json.dumps(rules['variables']),
      'Allowed lemma calls (arity): '+json.dumps(rules['calls'],sort_keys=True),
      'Allowed pure functions/predicates (arity): '+json.dumps(rules['pure'],sort_keys=True),
      'Only listed symbols are permitted in replacement bodies. Other definitions may be visible as context but remain protected.',
      'Declared file includes:\n'+json.dumps({n:re.findall(r'^include "([^"]+)"',s,re.M) for n,s in sorted(base.items())},indent=2)]
    parts.extend(f'FILE {n}\n```dafny\n{s}```' for n,s in sorted(base.items()))
    parts.extend([OPEN+diagnostic+CLOSE,'Return one JSON object containing every requested complete replacement body, without the enclosing lemma braces.'])
    return '\n\n'.join(parts)+'\n'

def validate(plan,tasks):
    assert plan['proposed_calls']==24 and plan['max_calls_per_trial']==1 and plan['sdk_total_max_attempts']==1
    assert plan['max_output_tokens_total']==24*plan['inference_config']['maxTokens']
    assert not any(plan[k] for k in ('execution_authorized','automatic_retries','reassign_unused','slurm_requeue','feedback_after_repair'))
    assert len(tasks)==6 and len({t['semantic_instance'] for t in tasks})==3
    cells=[tuple(x) for x in plan['order']];assert len(cells)==24 and cells[12:]==list(reversed(cells[:12]))
    expected={(t['semantic_instance'],t['sharing'],a) for t in tasks for a in plan['feedback_conditions']}
    assert set(cells)==expected and all(n==2 for n in Counter(cells).values()) and len(set(cells[:12]))==12
    for c in expected:assert sum(i+1 for i,x in enumerate(cells) if x==c)==25
    assert all(t['development_only'] and not t['held_out'] and t['failure_origin']=='analyst_constructed' for t in tasks)

def build(out):
    plan=load(HERE/'plan.json');tasks=load(CURRENT/'tasks.json');validate(plan,tasks)
    gate=load(TASKS/'validation-gate.json');assert gate['all_expected'] and gate['planned_controls']==36 and gate['model_calls']==0
    assert gate['source_manifest_sha256']==sha(CURRENT/'manifest.json') and gate['assembler_sha256']==sha(TASKS/'assemble_gate.py')
    for n,h in load(CURRENT/'manifest.json').items():assert sha(CURRENT/n)==h,n
    for row in gate['checks']:
        assert sha(TASKS/row['evidence_path'])==row['evidence_sha256'] and sha(TASKS/row['review_path'])==row['review_sha256']
        assert hashes(files(CURRENT/row['path']))==row['source_sha256']
    out.mkdir(exist_ok=False);(out/'parents').mkdir();(out/'requests').mkdir();(out/'policy').mkdir()
    inputs=[HERE/n for n in ('prepare.py','test_plan.py','plan.json','syntax.txt','system.txt')]
    inputs += [TASKS/n for n in ('validation-gate.json','assemble_gate.py','measurement-scope.json','target_metrics.py','results-review.json','verification-001-sha256.json')]
    inputs += [CURRENT/n for n in ('manifest.json','tasks.json','all-cases.json','results-review.json','verification-001-sha256.json')]
    inputs += [TASKS/r['evidence_path'] for r in gate['checks']]
    for n in ('body_guard.py','extract_response.py','repair_protocol.py'):
        shutil.copy2(CURRENT/n,out/'policy'/n);inputs.append(CURRENT/n)
    guard=module(CURRENT/'body_guard.py');envelope=module(CURRENT/'extract_response.py');protocol=module(CURRENT/'repair_protocol.py')
    parents={};requests={};replays=[];feedback_pairs=[]
    for task in tasks:
        tid=task['task_id'];row=next(r for r in gate['checks'] if r['case_id']==tid+'-faulty')
        base=files(CURRENT/'fixtures'/tid/'faulty');template=files(CURRENT/'templates'/tid)
        ev=load(TASKS/row['evidence_path']);assert ev['source_sha256']==hashes(base)
        assert task['failure_type']  # Metadata stays outside model context.
        clean=feedback(ev);parent=out/'parents'/tid;parent.mkdir()
        for label,data in [('base',base),('template',template)]:
            (parent/label).mkdir()
            for n,s in data.items():(parent/label/n).write_text(s)
        save(parent/'task.json',task);save(parent/'verification.json',ev);save(parent/'feedback.json',clean)
        parents[tid]=dict(task_id=tid,semantic_instance=task['semantic_instance'],sharing=task['sharing'],failure_origin='analyst_constructed',
            source_sha256=hashes(base),template_sha256=hashes(template),
            base_path=f'parents/{tid}/base',template_path=f'parents/{tid}/template',task_path=f'parents/{tid}/task.json',
            feedback_path=f'parents/{tid}/feedback.json',original_verifier_path=f'parents/{tid}/verification.json',evidence_sha256=row['evidence_sha256'])
        messages={}
        for arm in plan['feedback_conditions']:
            text=render(task,base,guard.policy(task),json.dumps(clean,indent=2) if arm=='verifier_diagnostics' else NOTICE)
            assert task['failure_type'] not in text
            payload=dict(modelId=plan['model_id'],system=[dict(text=(HERE/'system.txt').read_text())],
                messages=[dict(role='user',content=[dict(text=text)])],inferenceConfig=plan['inference_config'])
            path=out/'requests'/(tid+'-'+arm+'.json');save(path,payload);requests[(tid,arm)]=path;messages[arm]=text
        assert messages['verifier_diagnostics'].replace(OPEN+json.dumps(clean,indent=2)+CLOSE,OPEN+NOTICE+CLOSE)==messages['failure_notice_only']
        feedback_pairs.append(dict(task_id=tid,only_feedback_differs=True,original_evidence_sha256=row['evidence_sha256'],removed_lines=1))
        for variant in ('faulty','reference','alternative'):
            src=files(CURRENT/'fixtures'/tid/variant);payload={}
            for n in task['editable_files']:
                pre,suf=guard.split_seed(template[n]);payload[n]=src[n][len(pre):-len(suf)]
                if variant!='faulty':assert all(payload[n] not in message for message in messages.values())
            rebuilt,_=protocol.apply_response(json.dumps(payload),base,template,task,hashes(base),guard,envelope)
            assert rebuilt==src
            replays.append(dict(task_id=tid,variant=variant,exact=True,source_sha256=hashes(src)))
            inputs += list((CURRENT/'fixtures'/tid/variant).glob('*.dfy'))
        inputs+=list((CURRENT/'templates'/tid).glob('*.dfy'))
    trials=[]
    for i,(instance,sharing,arm) in enumerate(plan['order'],1):
        tid=instance+'-'+sharing;p=requests[(tid,arm)]
        trials.append(dict(trial_id=f'diverse-repair-{i:02d}',sequence=i,parent_id=tid,task_id=tid,
            semantic_instance=instance,sharing=sharing,feedback_condition=arm,replicate=1 if i<=12 else 2,
            request_path=str(p.relative_to(out)),request_sha256=sha(p),max_calls=1))
    save(out/'parents.json',parents);save(out/'trials.json',trials);save(out/'settings.json',plan)
    shutil.copy2(TASKS/'validation-gate.json',out/'validation-gate.json')
    shutil.copy2(TASKS/'measurement-scope.json',out/'measurement-scope.json')
    save(out/'offline-review.json',dict(new_model_calls=0,feedback_pairs=feedback_pairs,body_replays=replays,
         corrected_proofs_in_model_context=False,failure_labels_in_model_context=False,unique_workspaces=6,unique_payloads=12,planned_new_requests=24,
         limitations=['Constructed development faults; not natural model errors','Three familiar development families; no held-out claim','Separate has twice as many editable bodies; copying allowed','Per-family results required; no pooled causal depth/sharing conclusion']))
    save(out/'request-sizes.json',{str(p.relative_to(out)):dict(bytes=p.stat().st_size,characters=len(p.read_text())) for p in requests.values()})
    save(out/'freeze.json',dict(proposal='diverse-repair-plan-001',source_commit=plan['source_commit'],proposed_calls=24,execution_authorized=False,
        files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
        repository_inputs_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted(set(inputs))}))

def rebuild():
    with tempfile.TemporaryDirectory() as d:
        out=Path(d)/'frozen';build(out)
        expected={str(p.relative_to(HERE/'frozen-001')):sha(p) for p in (HERE/'frozen-001').rglob('*') if p.is_file()}
        assert {str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}==expected

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['check']:rebuild()
    elif not sys.argv[1:]:build(HERE/'frozen-001')
    else:raise SystemExit('prepare.py [check]')
