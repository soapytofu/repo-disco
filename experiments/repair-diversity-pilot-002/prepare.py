"""Offline preparation only; a coordinator gate is mandatory before prompt freeze."""
from collections import Counter
from pathlib import Path, PurePosixPath
import csv
import hashlib
import importlib.util
import io
import json
import re
import shutil
import tempfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
OPEN='<verifier_feedback>\n'
CLOSE='\n</verifier_feedback>'
NOTICE='Detailed verifier diagnostics are not supplied for this attempt.'
METRIC_TARGETS={'HelperA.Prove','HelperB.Prove','ClientA.Target','ClientB.Target'}
POLICY_FILES=('body_guard.py','extract_response.py','repair_protocol.py','registry.json')


def load(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashes(files): return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(files.items())}
def files(path): return {p.name:p.read_bytes().decode('utf-8') for p in sorted(Path(path).glob('*.dfy'))}
def save(path,value): Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def safe(root,name):
    rel=PurePosixPath(name)
    assert rel.parts and not rel.is_absolute() and '..' not in rel.parts
    path=Path(root)/str(rel)
    assert path.resolve().is_relative_to(Path(root).resolve()) and not path.is_symlink()
    return path


def module(path):
    spec=importlib.util.spec_from_file_location(Path(path).stem+'_repair_plan',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def validate_plan(plan):
    assert plan['study']=='repair-diversity-pilot-002'
    assert plan['proposed_calls']==32 and plan['max_calls_per_trial']==1 and plan['sdk_total_max_attempts']==1
    assert plan['replicates_per_cell']==2 and plan['unique_semantic_instances']==4
    assert plan['unique_failing_workspaces']==8 and plan['unique_payloads']==16
    assert plan['inference_config']=={'temperature':1.0,'maxTokens':4096}
    assert plan['model_id']=='global.anthropic.claude-opus-4-5-20251101-v1:0' and plan['region']=='us-east-1'
    assert plan['max_output_tokens_total']==32*4096 and plan['fresh_context_per_request']
    assert not any(plan[k] for k in ('execution_authorized','automatic_retries','reassign_unused','slurm_requeue','feedback_after_repair'))
    assert plan['failure_origin']=='analyst_constructed' and plan['family_split']=='development'
    assert plan['aggregate_approval']['approved_new_requests_total']==128
    assert plan['aggregate_approval']['proposed_allocation']==32
    assert plan['aggregate_approval']['deadline_utc']=='2026-11-16T04:05:12Z'
    assert not plan['aggregate_approval']['separate_user_approval_required']
    assert set(plan['source_roots'])==set(plan['source_instances'])=={'arithmetic','sequence','witness','maps'}
    expected={(instance,sharing,arm) for instance in plan['semantic_instances']
              for sharing in plan['sharing_conditions'] for arm in plan['feedback_conditions']}
    cells=[tuple(c) for c in plan['order']]
    assert len(expected)==16 and len(cells)==32 and len(set(cells[:16]))==16
    assert set(cells)==expected and cells[16:]==list(reversed(cells[:16]))
    assert all(n==2 for n in Counter(cells).values())
    assert all(sum(i+1 for i,c in enumerate(cells) if c==cell)==33 for cell in expected)


def reviewed_groups(plan):
    """Read only exact reviewed sources; this never initiates verification."""
    validate_plan(plan);groups={}
    for name,relative in plan['source_roots'].items():
        root=safe(REPO,relative);review=load(root/'results-review.json')
        assert review['all_expected'] and review['model_calls']==0
        cases=load(root/'cases.json');tasks=load(root/'tasks.json')
        assert review['planned']==review['reviewed']==len(cases)==len(review['checks'])
        by_id={r['case_id']:r for r in review['checks']}
        assert len(by_id)==len(cases) and all(r['matched'] and not r['unverified_providers'] for r in by_id.values())
        assert len(tasks)==2 and {t['sharing'] for t in tasks}=={'shared','separate'}
        assert all(t['semantic_instance']==plan['source_instances'][name] for t in tasks)
        for filename in ('fixture-manifest.json','runtime-manifest.json'):
            for path,digest in load(root/filename).items(): assert sha(safe(root,path))==digest,path
        records={}
        for case in cases:
            assert hashes(files(root/case['path']))==case['source_sha256']
            archived=root/'verification-001'/case['path']
            assert hashes(files(archived))==case['source_sha256']
            evidence=root/'verification-001'/(case['case_id']+'.json')
            record=load(evidence);row=by_id[case['case_id']]
            assert sha(evidence)==row['evidence_sha256']
            assert record['source_sha256']==case['source_sha256']
            assert record['attempts']==1 and record['model_calls']==0
            records[case['case_id']]=record
        groups[name]={'root':root,'review':review,'tasks':tasks,'cases':cases,'records':records,
                      'case_by_id':{c['case_id']:c for c in cases},'review_by_id':by_id}
    return groups


def checked_protocol(plan):
    root=safe(REPO,plan['protocol_root']);freeze=load(root/plan['protocol_freeze_file'])
    assert freeze['policy_version']=='repair-diversity-bodies-v1-development'
    assert freeze['offline_test_methods_passed']>=20 and freeze['model_calls']==freeze['verifier_invocations']==0
    assert freeze['admitted_workspaces']>=70 and freeze['hidden_controls_rejected']==8
    for name,digest in freeze['files_sha256'].items(): assert sha(safe(root,name))==digest,name
    assert set(POLICY_FILES)<=set(freeze['files_sha256'])
    envelope=safe(REPO,plan['envelope_root']);envelope_freeze=load(envelope/'policy-freeze.json')
    assert envelope_freeze['policy_version']=='repair-envelope-v2-explicit-json-001'
    for name,digest in envelope_freeze['files_sha256'].items(): assert sha(safe(envelope,name))==digest,name
    assert sha(root/'extract_response.py')==sha(envelope/'extract_response.py')
    return root,freeze


def feedback(record):
    assert record['exit_code']==4 and record['attempts']==1 and record['model_calls']==0
    lines=record['stdout'].splitlines(keepends=True)
    removed=[line for line in lines if line.startswith('Results File: ')]
    assert len(removed)==1
    assert re.fullmatch(r'Results File: /tmp/repodisco-repair(?:-adapter)?-[^/\r\n]+/TestResults/[^\r\n]+(?:\r?\n)?',removed[0])
    return {'exit_code':4,'stdout':''.join(line for line in lines if line not in removed),'stderr':record['stderr']}


def render(task,base,rules,diagnostic):
    parts=['The supplied candidate fails whole-workspace verification. Repair the requested lemma bodies while preserving the full repository contracts.',
        'Editable files: '+json.dumps(task['editable_files']),
        'Proof-body syntax:\n'+(HERE/'syntax.txt').read_text(),
        'Parameters: '+json.dumps(rules['variables']),
        'Allowed lemma calls (arity): '+json.dumps(rules['calls'],sort_keys=True),
        'Allowed pure functions/predicates (arity): '+json.dumps(rules['pure'],sort_keys=True),
        'Only listed symbols are permitted in replacement bodies. Other definitions remain protected context.',
        'Declared file includes:\n'+json.dumps({n:re.findall(r'^include "([^"]+)"',s,re.M) for n,s in sorted(base.items())},indent=2)]
    parts += [f'FILE {name}\n```dafny\n{source}```' for name,source in sorted(base.items())]
    parts += [OPEN+diagnostic+CLOSE,
        'Return one JSON object containing every requested complete replacement body, without the enclosing lemma braces.']
    return '\n\n'.join(parts)+'\n'


def expected_units(csv_files,interpreter):
    result={}
    assert csv_files
    for text in csv_files.values():
        reader=csv.DictReader(io.StringIO(text));assert reader.fieldnames==interpreter.HEADER
        for row in reader:
            match=interpreter.NAME.fullmatch(row[interpreter.HEADER[0]])
            assert match and row[interpreter.HEADER[1]]=='Passed'
            symbol,kind,_=match.groups();result.setdefault(symbol,set()).add(kind)
    assert METRIC_TARGETS<set(result), 'Distinct provider obligations required'
    return result


def assemble_measurements(plan,groups=None):
    groups=reviewed_groups(plan) if groups is None else groups
    interpreter_path=safe(REPO,plan['measurement_interpreter']);metrics=module(interpreter_path)
    scopes={};controls=[]
    for group in groups.values():
        for task in group['tasks']:
            tid=task['task_id'];reference=group['records'][tid+'-reference']
            units=expected_units(reference['csv'],metrics)
            scope={'expected_units':{n:sorted(k) for n,k in sorted(units.items())},
                   'editable_targets':['HelperA.Prove']+(['HelperB.Prove'] if task['sharing']=='separate' else []),
                   'target_dependencies':{'HelperA.Prove':[],
                       'HelperB.Prove':['HelperA.Prove'] if task['sharing']=='shared' else [],
                       'ClientA.Target':['HelperA.Prove'],'ClientB.Target':['HelperB.Prove']},
                   'recursion':'Self-recursion is checked within the named lemma; it is not a cyclic cross-target edge.',
                   'reference_evidence_path':str((group['root']/'verification-001'/(tid+'-reference.json')).relative_to(REPO)),
                   'reference_evidence_sha256':sha(group['root']/'verification-001'/(tid+'-reference.json'))}
            scopes[tid]=scope
            for variant in ('reference','alternative','faulty'):
                case_id=tid+'-'+variant;record=group['records'][case_id]
                score=metrics.scores(record['csv'],scope,units)
                assert score['supplied_providers_verified']
                if variant=='faulty':
                    assert score['editable_local']['passed']==0 and score['supplied_clients_closed']['passed']==0
                else:
                    assert score['editable_local']['passed']==len(scope['editable_targets'])
                    assert score['supplied_clients_closed']['passed']==2
                controls.append({'case_id':case_id,'evidence_path':str((group['root']/'verification-001'/(case_id+'.json')).relative_to(REPO)),
                                 'evidence_sha256':sha(group['root']/'verification-001'/(case_id+'.json')),**score})
    assert len(scopes)==8 and len(controls)==24
    return {'interpreter_sha256':sha(interpreter_path),'interpreter_path':plan['measurement_interpreter'],
            'tasks':scopes,'control_measurements':controls,'model_calls':0,'new_verifier_invocations':0,
            'unit':'Four constructed semantic instances; eight fixed failing workspaces, not32 independent tasks.'}


def binding_snapshot(plan,groups=None):
    groups=reviewed_groups(plan) if groups is None else groups
    protocol,_=checked_protocol(plan)
    return {'source_groups':{name:{'path':str(g['root'].relative_to(REPO)),
               'results_review_sha256':sha(g['root']/'results-review.json'),
               'fixture_manifest_sha256':sha(g['root']/'fixture-manifest.json'),
               'runtime_manifest_sha256':sha(g['root']/'runtime-manifest.json')} for name,g in groups.items()},
            'protocol_freeze_path':str((protocol/plan['protocol_freeze_file']).relative_to(REPO)),
            'protocol_freeze_sha256':sha(protocol/plan['protocol_freeze_file']),
            'measurement_scope_sha256':sha(HERE/'measurement-scope.json')}


def write_measurements():
    plan=load(HERE/'plan.json');groups=reviewed_groups(plan)
    checked_protocol(plan)
    result=assemble_measurements(plan,groups)
    path=HERE/'measurement-scope.json'
    if path.exists(): assert load(path)==result,'Existing measurement scope changed'
    else: save(path,result)
    draft={'schema':'repair-diversity-freeze-gate-v1','coordinator_reviewed':False,'all_expected':True,
           'source_commit':None,'model_calls':0,**binding_snapshot(plan,groups),
           'note':'All underlying verifier reviews are positive; coordinator must approve these exact bindings and source commit before freeze.'}
    save(HERE/'freeze-gate-draft.json',draft)
    return {'tasks':8,'control_measurements':24,'provider_obligations_preserved':True,
            'coordinator_gate_ready':False,'frozen_created':False}


def validated_freeze_gate(plan,groups):
    gate=load(HERE/'freeze-gate.json')
    assert gate['schema']=='repair-diversity-freeze-gate-v1'
    assert gate['coordinator_reviewed'] and gate['all_expected'] and gate['model_calls']==0
    assert isinstance(gate['source_commit'],str) and re.fullmatch('[0-9a-f]{40}',gate['source_commit'])
    assert plan['source_commit']==gate['source_commit']
    current=binding_snapshot(plan,groups)
    assert all(gate[k]==v for k,v in current.items())
    assert load(HERE/'measurement-scope.json')==assemble_measurements(plan,groups)
    return gate


def build(out):
    """No output directory is created until all reviewed gates validate."""
    plan=load(HERE/'plan.json');groups=reviewed_groups(plan);protocol_root,policy_freeze=checked_protocol(plan)
    gate=validated_freeze_gate(plan,groups)
    guard=module(protocol_root/'body_guard.py');envelope=module(protocol_root/'extract_response.py');adapter=module(protocol_root/'repair_protocol.py')
    out=Path(out);out.mkdir(exist_ok=False)
    for directory in ('parents','requests','policy'): (out/directory).mkdir()
    inputs={HERE/n for n in ('prepare.py','test_plan.py','plan.json','syntax.txt','system.txt','freeze-gate.json','measurement-scope.json')}
    inputs.add(safe(REPO,plan['measurement_interpreter']))
    for name in policy_freeze['files_sha256']:
        shutil.copy2(protocol_root/name,out/'policy'/name);inputs.add(protocol_root/name)
    shutil.copy2(protocol_root/plan['protocol_freeze_file'],out/'policy'/plan['protocol_freeze_file'])
    inputs.add(protocol_root/plan['protocol_freeze_file'])
    parents={};requests={};replays=[];pairs=[]
    for group in groups.values():
        root=group['root']
        inputs.update(root/n for n in ('tasks.json','cases.json','fixture-manifest.json','runtime-manifest.json','results-review.json'))
        for task in group['tasks']:
            task=dict(task,development_only=True,held_out=False,failure_origin='analyst_constructed')
            tid=task['task_id'];case=group['case_by_id'][tid+'-faulty'];empty=group['case_by_id'][tid+'-empty']
            base=files(root/case['path']);template=files(root/empty['path'])
            assert hashes(template)==task['source_sha256'] and hashes(base)==case['source_sha256']
            record=group['records'][case['case_id']];clean=feedback(record)
            parent=out/'parents'/tid;parent.mkdir()
            for label,workspace in [('base',base),('template',template)]:
                (parent/label).mkdir()
                for name,text in workspace.items(): (parent/label/name).write_bytes(text.encode())
            save(parent/'task.json',task);save(parent/'verification.json',record);save(parent/'feedback.json',clean)
            evidence_path=root/'verification-001'/(case['case_id']+'.json')
            parents[tid]={'task_id':tid,'semantic_instance':task['semantic_instance'],'sharing':task['sharing'],
                'failure_origin':'analyst_constructed','source_sha256':hashes(base),'template_sha256':hashes(template),
                'base_path':f'parents/{tid}/base','template_path':f'parents/{tid}/template','task_path':f'parents/{tid}/task.json',
                'feedback_path':f'parents/{tid}/feedback.json','original_verifier_path':f'parents/{tid}/verification.json',
                'evidence_sha256':sha(evidence_path)}
            messages={}
            for arm in plan['feedback_conditions']:
                diagnostic=json.dumps(clean,indent=2) if arm=='verifier_diagnostics' else NOTICE
                text=render(task,base,guard.policy(task),diagnostic);messages[arm]=text
                if task.get('failure_type'): assert task['failure_type'] not in text
                payload={'modelId':plan['model_id'],'system':[{'text':(HERE/'system.txt').read_text()}],
                    'messages':[{'role':'user','content':[{'text':text}]}],'inferenceConfig':plan['inference_config']}
                path=out/'requests'/(tid+'-'+arm+'.json');save(path,payload);requests[(tid,arm)]=path
            assert messages['verifier_diagnostics'].replace(OPEN+json.dumps(clean,indent=2)+CLOSE,OPEN+NOTICE+CLOSE)==messages['failure_notice_only']
            pairs.append({'task_id':tid,'only_feedback_differs':True,'original_evidence_sha256':sha(evidence_path),'removed_results_file_lines':1})
            for variant in ('faulty','reference','alternative'):
                state=group['case_by_id'][tid+'-'+variant];src=files(root/state['path']);body={}
                for name in task['editable_files']:
                    prefix,suffix=guard.split_seed(template[name])
                    assert src[name].startswith(prefix) and src[name].endswith(suffix)
                    body[name]=src[name][len(prefix):-len(suffix)]
                    if variant!='faulty': assert all(body[name] not in text for text in messages.values())
                rebuilt,_=adapter.apply_response(json.dumps(body),base,template,task,hashes(base),guard,envelope)
                assert rebuilt==src
                replays.append({'task_id':tid,'variant':variant,'exact':True,'source_sha256':hashes(src)})
                inputs.update((root/state['path']).glob('*.dfy'))
                inputs.add(root/'verification-001'/(state['case_id']+'.json'))
            inputs.update((root/empty['path']).glob('*.dfy'));inputs.add(evidence_path)
    trials=[]
    for i,(instance,sharing,arm) in enumerate(plan['order'],1):
        tid=instance+'-'+sharing;path=requests[(tid,arm)]
        trials.append({'trial_id':f'repair-diversity-{i:02d}','sequence':i,'parent_id':tid,'task_id':tid,
            'semantic_instance':instance,'sharing':sharing,'feedback_condition':arm,'replicate':1 if i<=16 else 2,
            'request_path':str(path.relative_to(out)),'request_sha256':sha(path),'max_calls':1})
    settings=dict(plan,status='FROZEN_PENDING_BOUNDED_RUNTIME')
    for name,value in [('parents.json',parents),('trials.json',trials),('settings.json',settings)]: save(out/name,value)
    shutil.copy2(HERE/'measurement-scope.json',out/'measurement-scope.json')
    save(out/'validation-gate.json',{'all_expected':True,'planned_controls':sum(g['review']['planned'] for g in groups.values()),
        'model_calls':0,'source_groups':gate['source_groups'],'protocol_freeze_sha256':gate['protocol_freeze_sha256']})
    save(out/'offline-review.json',{'new_model_calls':0,'feedback_pairs':pairs,'body_replays':replays,
        'corrected_proofs_in_model_context':False,'failure_labels_in_model_context':False,
        'unique_semantic_instances':4,'unique_workspaces':8,'unique_payloads':16,'planned_new_requests':32,
        'order_mean_position_per_cell':16.5,'fresh_contexts':True,
        'limitations':['Constructed development faults, not natural model-error prevalence','Four semantic instances, not32 independent tasks',
            'Separate has two copyable editable bodies and different output workload','No depth factor or general causal sharing/depth/held-out claims']})
    save(out/'request-sizes.json',{str(p.relative_to(out)):{'bytes':p.stat().st_size,'characters':len(p.read_text())} for p in requests.values()})
    save(out/'freeze.json',{'proposal':'repair-diversity-pilot-002','source_commit':gate['source_commit'],
        'proposed_calls':32,'execution_authorized':False,'aggregate_approval_window':plan['aggregate_approval']['window'],
        'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
        'repository_inputs_sha256':{str(p.relative_to(REPO)):sha(p) for p in sorted(inputs)}})


def status():
    plan=load(HERE/'plan.json');validate_plan(plan);missing=[]
    for path in [*(safe(REPO,p)/'results-review.json' for p in plan['source_roots'].values()),
                 safe(REPO,plan['protocol_root'])/plan['protocol_freeze_file'],
                 HERE/'measurement-scope.json',HERE/'freeze-gate.json']:
        if not path.exists(): missing.append(str(path.relative_to(REPO)))
    return {'proposed_calls':32,'model_calls':0,'frozen_exists':(HERE/'frozen-001').exists(),'missing_gates':missing,
            'coordinator_ready':not missing and load(HERE/'freeze-gate.json').get('coordinator_reviewed',False)}


def rebuild():
    with tempfile.TemporaryDirectory() as temp:
        out=Path(temp)/'frozen';build(out)
        expected={str(p.relative_to(HERE/'frozen-001')):sha(p) for p in (HERE/'frozen-001').rglob('*') if p.is_file()}
        assert {str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}==expected


if __name__=='__main__':
    import sys
    args=sys.argv[1:]
    if not args or args==['status']: print(json.dumps(status(),indent=2))
    elif args==['measurements']: print(json.dumps(write_measurements(),indent=2))
    elif args==['freeze']: build(HERE/'frozen-001')
    elif args==['check']: rebuild()
    else: raise SystemExit('prepare.py [status|measurements|freeze|check]')
