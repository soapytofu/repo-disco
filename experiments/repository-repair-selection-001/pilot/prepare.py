"""Offline preparation; explicit coordinator review precedes every prompt freeze."""
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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OPEN = '<verifier_feedback>\n'
CLOSE = '\n</verifier_feedback>'
NOTICE = 'Detailed verifier diagnostics are not supplied for this attempt.'
ARMS = {'diagnostics':'verifier_diagnostics', 'notice':'failure_notice_only'}
GRAPH = {'HelperA.Prove':[], 'HelperB.Prove':['HelperA.Prove'],
         'ClientA.Target':['HelperB.Prove'], 'ClientB.Target':['HelperB.Prove']}
TARGETS = set(GRAPH)
EDITABLE = ['HelperA.dfy', 'HelperB.dfy']
POLICY_FILES = {'body_guard.py','syntax_guard.py','extract_response.py','repair_protocol.py','registry.json'}
POLICY_ID = 'repository-repair-selection-bodies-v1-development'
ABI = 'repair-diversity-bodies-v1-development'


def load(path): return json.loads(Path(path).read_bytes())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def hashes(source): return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(source.items())}
def files(path): return {p.name:p.read_bytes().decode('utf-8') for p in sorted(Path(path).glob('*.dfy'))}
def save(path,value): Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def safe(root,name):
    rel = PurePosixPath(name)
    assert rel.parts and not rel.is_absolute() and '..' not in rel.parts
    path = Path(root)/str(rel)
    assert path.resolve().is_relative_to(Path(root).resolve()) and not path.is_symlink()
    return path


def module(path):
    spec = importlib.util.spec_from_file_location(Path(path).stem+'_repair_selection',path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def task_metadata(plan):
    result = {}
    for group,path in plan['source_roots'].items():
        tasks = load(safe(REPO,path)/'tasks.json')
        assert len(tasks)==2
        for task in tasks:
            tid = task['task_id']
            assert tid not in result and plan['task_groups'][tid]==group
            assert task['sharing']=='pipeline' and task['editable_files']==EDITABLE
            result[tid] = task
    assert set(result)==set(plan['task_groups']) and len(result)==4
    return result


def reviewed_auditor_inputs(plan):
    """Validate and retain every transitive study-review dependency, not just its entry point."""
    root = safe(REPO,plan['source_review_code']).parent
    manifest = root/'review-manifest.json'
    pins = load(manifest)
    assert isinstance(pins,dict) and pins
    required = {str(safe(REPO,plan[key]).relative_to(root)) for key in ('source_review_code','source_review_scope')}
    required.add('review-inputs/review_verification.py')
    assert required<=set(pins), 'Incomplete study-review provenance'
    result = {manifest}
    for name,digest in pins.items():
        assert isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest)
        path = safe(root,name)
        assert sha(path)==digest, 'Study-review dependency changed: '+name
        result.add(path)
    return result


def validate_plan(plan,design=None,tasks=None):
    assert plan['study']==plan['batch_id']=='repository-repair-selection-001'
    assert plan['proposed_calls']==32 and plan['max_calls_per_trial']==plan['sdk_total_max_attempts']==1
    assert plan['replicates_per_cell']==4 and plan['unique_semantic_instances']==4
    assert plan['unique_failing_workspaces']==4 and plan['unique_payloads']==8
    assert plan['sharing_conditions']==['pipeline']
    assert plan['feedback_conditions']==list(ARMS.values())
    assert plan['model_id']=='global.anthropic.claude-opus-4-5-20251101-v1:0'
    assert plan['region']=='us-east-1' and plan['inference_config']=={'temperature':1.0,'maxTokens':4096}
    assert plan['max_output_tokens_total']==32*4096 and plan['fresh_context_per_request']
    assert not any(plan[k] for k in ('execution_authorized','automatic_retries','reassign_unused','slurm_requeue','feedback_after_repair'))
    assert plan['failure_origin']=='analyst_constructed' and plan['family_split']=='development'
    assert plan['aggregate_approval']['approved_new_requests_total']==128
    assert plan['aggregate_approval']['proposed_allocation']==32
    assert plan['aggregate_approval']['deadline_utc']=='2026-11-16T04:05:12Z'
    assert not plan['aggregate_approval']['separate_user_approval_required']
    assert set(plan['source_roots'])=={'witness','maps'}
    assert plan['target_dependencies']==GRAPH and plan['editable_files']==EDITABLE
    if design is None:
        path = safe(REPO,plan['design_plan_path'])
        assert sha(path)==plan['design_plan_sha256'], 'Prospective design changed'
        design = load(path)
    tasks = task_metadata(plan) if tasks is None else tasks
    assert {t['task_id'] for t in design['tasks']}==set(tasks)
    assert design['proposed_calls']==32 and design['responses_per_task_arm']==4
    assert design['architecture']['target_dependencies']==GRAPH
    assert plan['order_slots']==design['order'], 'Do not choose a new order after seeing outcomes'
    expected = [(tasks[s['task_id']]['semantic_instance'],'pipeline',ARMS[s['feedback_condition']]) for s in design['order']]
    assert plan['order']==[list(c) for c in expected]
    assert [s['position'] for s in design['order']]==list(range(1,33))
    cells = set(expected)
    assert len(cells)==8 and all(n==4 for n in Counter(expected).values())
    for block in range(4):
        assert set(expected[block*8:(block+1)*8])==cells
        assert all(s['replicate_block']==block+1 for s in design['order'][block*8:(block+1)*8])
    assert all(sum(i+1 for i,c in enumerate(expected) if c==cell)==66 for cell in cells)
    assert plan['semantic_instances']==[tasks[t['task_id']]['semantic_instance'] for t in design['tasks']]


def reviewed_groups(plan):
    validate_plan(plan)
    groups = {}
    for name,relative in plan['source_roots'].items():
        root = safe(REPO,relative)
        review_path = safe(REPO,plan['source_reviews'][name])
        review = load(review_path)
        cases,tasks = load(root/'cases.json'),load(root/'tasks.json')
        assert review['all_expected'] and review['model_calls']==0
        assert review['reference_gate_complete'] and review['declared_target_dependencies']==GRAPH
        assert review['runtime_manifest_sha256']==sha(root/'runtime-manifest.json')
        assert review['fixture_manifest_sha256']==sha(root/'fixture-manifest.json')
        assert review['scope_sha256']==sha(safe(REPO,plan['source_review_scope']))
        assert review['planned']==review['reviewed']==len(cases)==len(review['checks'])
        by_id = {r['case_id']:r for r in review['checks']}
        assert len(by_id)==len(cases) and all(r['matched'] and not r['unverified_providers'] for r in by_id.values())
        assert len(tasks)==2 and all(t['sharing']=='pipeline' for t in tasks)
        for filename in ('fixture-manifest.json','runtime-manifest.json'):
            manifest = load(root/filename)
            assert manifest
            for path,digest in manifest.items():
                assert sha(safe(root,path))==digest,path
                assert sha(safe(root/'verification-001',path))==digest,path
        records = {}
        for case in cases:
            assert hashes(files(root/case['path']))==case['source_sha256']
            assert hashes(files(root/'verification-001'/case['path']))==case['source_sha256']
            evidence = root/'verification-001'/(case['case_id']+'.json')
            record,row = load(evidence),by_id[case['case_id']]
            assert sha(evidence)==row['evidence_sha256']
            assert record['source_sha256']==case['source_sha256']
            assert record['attempts']==1 and record['model_calls']==0 and record['matched']
            assert record['exit_code']==case['expected_exit'] and record['actual']==case['expected']
            records[case['case_id']] = record
        groups[name] = dict(root=root,review=review,review_path=review_path,tasks=tasks,cases=cases,records=records,
                            case_by_id={c['case_id']:c for c in cases},review_by_id=by_id)
    return groups


def checked_protocol(plan):
    root = safe(REPO,plan['protocol_root'])
    freeze = load(root/plan['protocol_freeze_file'])
    assert freeze['policy_id']==POLICY_ID and freeze['adapter_abi']==ABI
    assert freeze['model_calls']==freeze['verifier_invocations']==0
    assert freeze['offline_test_methods_passed']>=18
    assert POLICY_FILES<=set(freeze['files_sha256'])
    for name,digest in freeze['files_sha256'].items():
        assert sha(safe(root,name))==digest,name
    guard = module(root/'body_guard.py')
    assert guard.POLICY_ID==POLICY_ID and guard.VERSION==ABI
    metadata = task_metadata(plan)
    assert set(guard.registry())==set(metadata)
    for task in metadata.values(): guard.task_entry(task)
    runtime = safe(REPO,plan['execution_runtime_root'])
    assert sha(root/'repair_protocol.py')==sha(runtime/'repair_protocol.py')
    envelope = safe(REPO,plan['envelope_root'])
    efreeze = load(envelope/'policy-freeze.json')
    assert efreeze['policy_version']=='repair-envelope-v2-explicit-json-001'
    for name,digest in efreeze['files_sha256'].items(): assert sha(safe(envelope,name))==digest,name
    assert sha(root/'extract_response.py')==sha(envelope/'extract_response.py')
    return root,freeze


def feedback(record):
    assert record['exit_code']==4 and record['attempts']==1 and record['model_calls']==0
    lines = record['stdout'].splitlines(keepends=True)
    removed = [line for line in lines if line.startswith('Results File: ')]
    assert len(removed)==1
    assert re.fullmatch(r'Results File: /tmp/repodisco-repair(?:-adapter)?-[^/\r\n]+/TestResults/[^\r\n]+(?:\r?\n)?',removed[0])
    return dict(exit_code=4,stdout=''.join(s for s in lines if s not in removed),stderr=record['stderr'])


def render(task,base,file_rules,diagnostic):
    """Whitelist visible data; never dump task/case/plan metadata into a prompt."""
    assert task['editable_files']==EDITABLE and set(file_rules)==set(EDITABLE)
    parts = ['The supplied candidate fails whole-workspace verification. Repair the eligible lemma bodies while preserving every repository contract.',
             'Editable files: '+json.dumps(EDITABLE),
             'Return both complete bodies. You may preserve either body unchanged.',
             'Proof-body syntax:\n'+(HERE/'syntax.txt').read_text()]
    for filename in EDITABLE:
        rules = file_rules[filename]
        parts.append('Body environment for '+filename+':\n'+json.dumps({
            'parameters':[{'name':n,'type':rules['parameter_types'][n]} for n in rules['variables']],
            'lemma_calls':{n:{'arguments':rules['call_types'][n]} for n in sorted(rules['calls'])},
            'pure_symbols':{n:rules['pure_types'][n] for n in sorted(rules['pure'])}},indent=2))
    parts += ['Only the symbols registered for a file may occur in its replacement body. Other definitions remain protected context.',
              'Declared file includes:\n'+json.dumps({n:re.findall(r'^include "([^"]+)"',s,re.M) for n,s in sorted(base.items())},indent=2)]
    parts += [f'FILE {name}\n```dafny\n{source}```' for name,source in sorted(base.items())]
    parts += [OPEN+diagnostic+CLOSE,'Return one JSON object containing both complete replacement bodies, without the enclosing lemma braces.']
    return '\n\n'.join(parts)+'\n'


def expected_units(csv_files,interpreter):
    units = {}
    assert csv_files
    for text in csv_files.values():
        reader = csv.DictReader(io.StringIO(text))
        assert reader.fieldnames==interpreter.HEADER
        for row in reader:
            match = interpreter.NAME.fullmatch(row[interpreter.HEADER[0]])
            assert match and row[interpreter.HEADER[1]]=='Passed'
            symbol,kind,_ = match.groups()
            units.setdefault(symbol,set()).add(kind)
    assert TARGETS<set(units), 'Distinct immutable provider obligations required'
    return units


def measure_task(task,records,interpreter):
    tid = task['task_id']
    units = expected_units(records[tid+'-reference']['csv'],interpreter)
    scope = dict(expected_units={n:sorted(k) for n,k in sorted(units.items())},
                 editable_targets=['HelperA.Prove','HelperB.Prove'],target_dependencies=GRAPH,
                 interpretation='Declared module graph; actual helper-call use is reported separately. Not a necessary-depth or minimal-proof claim.')
    controls = []
    for variant in ('reference','alternative','faulty'):
        case_id = tid+'-'+variant
        score = interpreter.scores(records[case_id]['csv'],scope,units)
        assert score['supplied_providers_verified'], 'A supplied provider did not verify'
        assert score['supplied_clients_local']['passed']==2
        assert score['editable_local']['total']==2
        if variant=='faulty':
            assert score['editable_local']['passed']==1, 'Require one sound local helper and one failing local helper'
            assert score['supplied_clients_closed']['passed']==0
        else:
            assert score['editable_local']['passed']==2 and score['supplied_clients_closed']['passed']==2
        controls.append(dict(case_id=case_id,**score))
    return scope,controls


def assemble_measurements(plan,groups=None):
    groups = reviewed_groups(plan) if groups is None else groups
    path = safe(REPO,plan['measurement_interpreter'])
    interpreter = module(path)
    scopes,controls = {},[]
    for group in groups.values():
        for task in group['tasks']:
            tid = task['task_id']
            scope,rows = measure_task(task,group['records'],interpreter)
            reference = group['root']/'verification-001'/(tid+'-reference.json')
            scope.update(reference_evidence_path=str(reference.relative_to(REPO)),reference_evidence_sha256=sha(reference))
            scopes[tid] = scope
            for row in rows:
                evidence = group['root']/'verification-001'/(row['case_id']+'.json')
                controls.append(dict(evidence_path=str(evidence.relative_to(REPO)),evidence_sha256=sha(evidence),**row))
    assert len(scopes)==4 and len(controls)==12
    return dict(interpreter_path=plan['measurement_interpreter'],interpreter_sha256=sha(path),tasks=scopes,
                control_measurements=controls,model_calls=0,new_verifier_invocations=0,
                unit='Four constructed failing workspaces; 32 responses are not 32 independent tasks.')


def binding_snapshot(plan,groups=None):
    groups = reviewed_groups(plan) if groups is None else groups
    protocol,_ = checked_protocol(plan)
    reviewed_auditor_inputs(plan)
    return dict(source_groups={name:{'path':str(g['root'].relative_to(REPO)),
                     'results_review_path':str(g['review_path'].relative_to(REPO)),
                     'results_review_sha256':sha(g['review_path']),
                     'fixture_manifest_sha256':sha(g['root']/'fixture-manifest.json'),
                     'runtime_manifest_sha256':sha(g['root']/'runtime-manifest.json')} for name,g in groups.items()},
                protocol_freeze_path=str((protocol/plan['protocol_freeze_file']).relative_to(REPO)),
                protocol_freeze_sha256=sha(protocol/plan['protocol_freeze_file']),
                source_review_scope_sha256=sha(safe(REPO,plan['source_review_scope'])),
                source_review_manifest_sha256=sha(safe(REPO,plan['source_review_code']).parent/'review-manifest.json'),
                measurement_scope_sha256=sha(HERE/'measurement-scope.json'),
                design_plan_sha256=plan['design_plan_sha256'],plan_sha256=sha(HERE/'plan.json'),
                syntax_sha256=sha(HERE/'syntax.txt'),system_sha256=sha(HERE/'system.txt'))


def write_measurements():
    plan = load(HERE/'plan.json')
    groups = reviewed_groups(plan)
    checked_protocol(plan)
    result = assemble_measurements(plan,groups)
    path = HERE/'measurement-scope.json'
    if path.exists(): assert load(path)==result, 'Existing measurement scope changed'
    else: save(path,result)
    draft = dict(schema='repository-repair-selection-freeze-gate-v1',coordinator_reviewed=False,
                 all_expected=True,source_commit=None,model_calls=0,**binding_snapshot(plan,groups))
    save(HERE/'freeze-gate-draft.json',draft)
    return dict(tasks=4,control_measurements=12,provider_obligations_preserved=True,coordinator_gate_ready=False,frozen_created=False)


def validated_freeze_gate(plan,groups):
    gate = load(HERE/'freeze-gate.json')
    assert gate['schema']=='repository-repair-selection-freeze-gate-v1'
    assert gate['coordinator_reviewed'] and gate['all_expected'] and gate['model_calls']==0
    assert isinstance(gate['source_commit'],str) and re.fullmatch('[0-9a-f]{40}',gate['source_commit'])
    assert all(gate[k]==v for k,v in binding_snapshot(plan,groups).items())
    assert load(HERE/'measurement-scope.json')==assemble_measurements(plan,groups)
    return gate


def build(out):
    """No directory or real prompt is created before the reviewed gate passes."""
    plan = load(HERE/'plan.json')
    groups = reviewed_groups(plan)
    protocol,pfreeze = checked_protocol(plan)
    gate = validated_freeze_gate(plan,groups)
    auditor_inputs = reviewed_auditor_inputs(plan)
    guard,envelope,adapter = (module(protocol/n) for n in ('body_guard.py','extract_response.py','repair_protocol.py'))
    out = Path(out)
    out.mkdir(exist_ok=False)
    for folder in ('parents','requests','policy'): (out/folder).mkdir()
    inputs = {HERE/n for n in ('prepare.py','test_plan.py','plan.json','syntax.txt','system.txt','measurement-scope.json','freeze-gate.json')}
    inputs.update(safe(REPO,plan[n]) for n in ('measurement_interpreter','design_plan_path','source_review_scope','source_review_code'))
    inputs.update(auditor_inputs)
    # Copy every nested policy dependency, never filter by basename.
    for name in pfreeze['files_sha256']:
        target = safe(out/'policy',name)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(protocol/name,target)
        inputs.add(protocol/name)
    shutil.copyfile(protocol/plan['protocol_freeze_file'],out/'policy'/plan['protocol_freeze_file'])
    inputs.add(protocol/plan['protocol_freeze_file'])
    parents,requests,replays,pairs = {},{},[],[]
    for group in groups.values():
        root = group['root']
        # Full reviewed input inventory, including negative evidence and nested runtime dependencies.
        for manifest in ('fixture-manifest.json','runtime-manifest.json'):
            inputs.add(root/manifest)
            inputs.update(safe(root,n) for n in load(root/manifest))
        inputs.update(p for p in group['review_path'].parent.rglob('*') if p.is_file())
        inputs.update(p for p in (root/'verification-001').rglob('*') if p.is_file())
        for task in group['tasks']:
            tid = task['task_id']
            case,empty = (group['case_by_id'][tid+'-'+v] for v in ('faulty','empty'))
            base,template = files(root/case['path']),files(root/empty['path'])
            assert hashes(template)==task['source_sha256'] and hashes(base)==case['source_sha256']
            record = group['records'][case['case_id']]
            clean = feedback(record)
            parent = out/'parents'/tid
            parent.mkdir()
            for label,workspace in [('base',base),('template',template)]:
                (parent/label).mkdir()
                for name,text in workspace.items(): (parent/label/name).write_bytes(text.encode())
            # No task-value normalization: the registry binds the exact supplied metadata.
            save(parent/'task.json',task)
            save(parent/'verification.json',record)
            save(parent/'feedback.json',clean)
            evidence = root/'verification-001'/(tid+'-faulty.json')
            parents[tid] = dict(task_id=tid,semantic_instance=task['semantic_instance'],sharing='pipeline',
                failure_origin='analyst_constructed',source_sha256=hashes(base),template_sha256=hashes(template),
                base_path=f'parents/{tid}/base',template_path=f'parents/{tid}/template',task_path=f'parents/{tid}/task.json',
                feedback_path=f'parents/{tid}/feedback.json',original_verifier_path=f'parents/{tid}/verification.json',evidence_sha256=sha(evidence))
            messages = {}
            rules = guard.task_entry(task)['file_rules']
            for arm in plan['feedback_conditions']:
                diagnostic = json.dumps(clean,indent=2) if arm=='verifier_diagnostics' else NOTICE
                text = render(task,base,rules,diagnostic)
                messages[arm] = text
                payload = dict(modelId=plan['model_id'],system=[{'text':(HERE/'system.txt').read_text()}],
                    messages=[{'role':'user','content':[{'text':text}]}],inferenceConfig=plan['inference_config'])
                path = out/'requests'/(tid+'-'+arm+'.json')
                save(path,payload)
                requests[(tid,arm)] = path
            assert messages['verifier_diagnostics'].replace(OPEN+json.dumps(clean,indent=2)+CLOSE,OPEN+NOTICE+CLOSE)==messages['failure_notice_only']
            pairs.append(dict(task_id=tid,only_feedback_differs=True,source_sections_exact_base=True,original_evidence_sha256=sha(evidence),removed_results_file_lines=1))
            for variant in ('faulty','reference','alternative'):
                state = group['case_by_id'][tid+'-'+variant]
                source,body = files(root/state['path']),{}
                for name in EDITABLE:
                    prefix,suffix = guard.split_seed(template[name])
                    assert source[name].startswith(prefix) and source[name].endswith(suffix)
                    body[name] = source[name][len(prefix):-len(suffix)]
                rebuilt,_ = adapter.apply_response(json.dumps(body),base,template,task,hashes(base),guard,envelope)
                assert rebuilt==source
                replays.append(dict(task_id=tid,variant=variant,exact=True,source_sha256=hashes(source)))
    metadata = task_metadata(plan)
    trials = []
    for slot in plan['order_slots']:
        tid,arm = slot['task_id'],ARMS[slot['feedback_condition']]
        path = requests[(tid,arm)]
        trials.append(dict(trial_id=f"repair-selection-{slot['position']:02d}",sequence=slot['position'],parent_id=tid,task_id=tid,
            semantic_instance=metadata[tid]['semantic_instance'],sharing='pipeline',feedback_condition=arm,replicate=slot['replicate_block'],
            request_path=str(path.relative_to(out)),request_sha256=sha(path),max_calls=1))
    settings = dict(plan,status='FROZEN_PENDING_SEPARATE_RUNTIME_ADMISSION',source_commit=gate['source_commit'])
    for name,value in [('parents.json',parents),('trials.json',trials),('settings.json',settings)]: save(out/name,value)
    shutil.copyfile(HERE/'measurement-scope.json',out/'measurement-scope.json')
    save(out/'validation-gate.json',dict(all_expected=True,planned_controls=sum(g['review']['planned'] for g in groups.values()),model_calls=0,
        source_groups=gate['source_groups'],protocol_freeze_sha256=gate['protocol_freeze_sha256']))
    save(out/'offline-review.json',dict(new_model_calls=0,feedback_pairs=pairs,body_replays=replays,source_context='Exact full failing sources only',
        empty_templates_in_context=False,reference_proofs_added_to_context=False,task_metadata_in_context=False,
        unique_semantic_instances=4,unique_workspaces=4,unique_payloads=8,planned_new_requests=32,order_mean_position_per_cell=16.5,
        fresh_contexts=True,limitations=plan['limitations']))
    save(out/'request-sizes.json',{str(p.relative_to(out)):{'bytes':p.stat().st_size,'characters':len(p.read_text())} for p in requests.values()})
    save(out/'freeze.json',dict(proposal=plan['study'],source_commit=gate['source_commit'],proposed_calls=32,execution_authorized=False,
        aggregate_approval_window=plan['aggregate_approval']['window'],
        files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
        repository_inputs_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted(inputs)}))


def status():
    plan = load(HERE/'plan.json')
    validate_plan(plan)
    paths = [*(safe(REPO,p) for p in plan['source_reviews'].values()),
             safe(REPO,plan['protocol_root'])/plan['protocol_freeze_file'],HERE/'measurement-scope.json',HERE/'freeze-gate.json']
    missing = [str(p.relative_to(REPO)) for p in paths if not p.exists()]
    return dict(proposed_calls=32,model_calls=0,frozen_exists=(HERE/'frozen-001').exists(),missing_gates=missing,
                coordinator_ready=not missing and load(HERE/'freeze-gate.json').get('coordinator_reviewed',False))


def rebuild():
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary)/'frozen'
        build(target)
        expected = {str(p.relative_to(HERE/'frozen-001')):sha(p) for p in (HERE/'frozen-001').rglob('*') if p.is_file()}
        assert {str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()}==expected


if __name__=='__main__':
    import sys
    args = sys.argv[1:]
    if not args or args==['status']: print(json.dumps(status(),indent=2))
    elif args==['measurements']: print(json.dumps(write_measurements(),indent=2))
    elif args==['freeze']: build(HERE/'frozen-001')
    elif args==['check']: rebuild()
    else: raise SystemExit('prepare.py [status|measurements|freeze|check]')
