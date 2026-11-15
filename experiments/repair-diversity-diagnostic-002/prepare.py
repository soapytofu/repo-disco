"""Analyst-only sufficiency diagnostic. Rebuild exact edits; never touch parents."""
from pathlib import Path
import hashlib,importlib.util,json,re
ROOT=Path(__file__).resolve().parent
EDIT_PREFIX={
    'exact_gap_pair':('var u := a;','var u := if a < c-gap then c-gap else a;'),
    'saturating_assoc':('O.Low(c,a,b); O.Low(c,b,d);',
                        'if a+b <= c { O.Low(c,a,b); } if b+d <= c { O.Low(c,b,d); }')}

def load(p):return json.loads(p.read_text())
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(p):return digest(p.read_bytes())
def files(path):return {p.name:p.read_bytes() for p in sorted(path.glob('*.dfy'))}
def hashes(fs):return {n:digest(b) for n,b in sorted(fs.items())}
def save(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def policy(root=ROOT):
    return tuple(module('diagnostic_'+name,root/'frozen-001/policy'/f'{name}.py') for name in ('body_guard','extract_response','repair_protocol'))

def validate_inputs(root=ROOT):
    provenance=load(root/'provenance.json');frozen=root/'frozen-001'
    assert sha(frozen/'freeze.json')==provenance['primary_proposal_freeze_sha256']
    actual={p.relative_to(frozen).as_posix():sha(p) for p in frozen.rglob('*') if p.is_file()};actual.pop('freeze.json')
    assert actual==load(frozen/'freeze.json')['files']
    assert sha(root/'primary-archive-manifest.json')==provenance['primary_archive_manifest_sha256']
    manifest=load(root/'primary-archive-manifest.json');assert len(manifest)==provenance['prior_archive_files_preserved']==1845
    for name,item in provenance['parent_copies'].items():assert sha(root/name)==item['sha256']==manifest[item['primary_path']],name
    for name,h in provenance['unchanged_runtime_copies'].items():assert sha(root/name)==h,name
    summary=load(root/'primary-metadata/summary.json')
    assert summary['maximum_calls']==32 and summary['verified']==27 and summary['all_trials_processed']
    assert sha(root/'target_metrics.py')==load(frozen/'measurement-scope.json')['interpreter_sha256']
    return provenance

def calls(body):
    return re.findall(r'\b([A-Za-z_][A-Za-z_0-9]*\.[A-Za-z_][A-Za-z_0-9]*)\s*\(([^;{}]*)\)\s*;',body)

def transform(body,instance):
    before,after=EDIT_PREFIX[instance]
    assert body.startswith(before),'Hypothesis only applies to the exact original leading statements'
    changed=after+body[len(before):]
    assert changed[len(after):]==body[len(before):]
    assert calls(body)==calls(changed),'No lemma calls may be added, removed, reordered or rewritten'
    return changed,dict(start_char=0,end_char=len(before),before=before,after=after,
                        preserved_suffix_sha256=digest(body[len(before):].encode()),
                        lemma_call_sequence_unchanged=True)

def candidates(root=ROOT):
    prov=validate_inputs(root);guard,envelope,adapter=policy(root)
    frozen=root/'frozen-001';parents=load(frozen/'parents.json')
    trials={t['trial_id']:t for t in load(frozen/'trials.json')}
    primary={r['trial_id']:r for r in load(root/'primary-metadata/results.json')}
    rows=[]
    for tid in prov['parent_trials']:
        origin=root/'parents'/tid;trial=trials[tid];parent=parents[trial['parent_id']]
        task=load(origin/'task.json');assert task==load(frozen/parent['task_path'])
        assert trial==load(origin/'trial.json') and load(origin/'result.json')==primary[tid]
        assert primary[tid]['outcome']=='PROOF_FAILURE' and primary[tid]['stop'] is False
        evidence=load(origin/'verification.json');assert evidence['exit_code']==4 and ': Error:' in evidence['stdout']
        assert re.search(r'Dafny program verifier finished with \d+ verified, [1-9][0-9]* errors?',evidence['stdout'])
        original=files(origin/'candidate');assert hashes(original)==evidence['source_sha256']==load(origin/'candidate-hashes.json')['candidate_sha256']
        base=files(frozen/parent['base_path']);template=files(frozen/parent['template_path'])
        initial=load(origin/'initial.json');head=load(origin/'final-head.json')
        assert initial['source_sha256']==hashes(base)==head['source_sha256'] and initial['revision']==head['revision']
        assert hashes(base)==parent['source_sha256'] and hashes(template)==parent['template_sha256']==task['source_sha256']
        raw=load(origin/'response.json')['text'];payload,original_span=envelope.extract_json(raw)
        original_replay,_=adapter.apply_response(raw,{n:b.decode() for n,b in base.items()},
            {n:b.decode() for n,b in template.items()},task,parent['source_sha256'],guard,envelope)
        assert {n:s.encode() for n,s in original_replay.items()}==original,'Original frozen guard replay differs'
        bodies=json.loads(payload,object_pairs_hook=envelope.unique,parse_constant=envelope.reject_constant)
        assert set(bodies)==set(task['editable_files'])
        edits={};new_bodies={};direct=dict(original)
        for name in task['editable_files']:
            before=bodies[name];after,edit=transform(before,task['semantic_instance']);new_bodies[name]=after;edits[name]=edit
            pre,suf=guard.split_seed(template[name].decode())
            assert original[name].decode()==pre+before+suf
            direct[name]=(pre+after+suf).encode()
        proposed=json.dumps(new_bodies,ensure_ascii=False,indent=2)+'\n'
        case=dict(case_id=tid+'-analyst',parent_trial=tid,task_id=task['task_id'],semantic_instance=task['semantic_instance'],
            sharing=trial['sharing'],feedback_condition=trial['feedback_condition'],original_outcome='PROOF_FAILURE',
            original_response_sha256=sha(origin/'response.json'),original_verification_sha256=sha(origin/'verification.json'),
            original_source_sha256=hashes(original),original_envelope_span=original_span,edits=edits,
            analyst_authored=True,model_calls=0,original_primary_score='27/32 unchanged',expected_category='strict_success',
            expected_verified_obligations=9 if task['semantic_instance']=='exact_gap_pair' else 7,
            payload_path='payloads/'+tid+'.json',path='fixtures/'+tid+'-analyst',new_lemma_calls=0)
        try:
            candidate,decision=adapter.apply_response(proposed,{n:b.decode() for n,b in original.items()},
                {n:b.decode() for n,b in template.items()},task,hashes(original),guard,envelope)
        except (ValueError,TypeError,UnicodeError,RecursionError) as error:
            case.update(admitted=False,diagnostic='body_guard_rejection',error_type=type(error).__name__,reason=str(error));rows.append((case,None,proposed));continue
        candidate={n:s.encode() for n,s in candidate.items()};assert candidate==direct
        protected=0
        for name in original:
            if name not in task['editable_files']:assert candidate[name]==original[name];protected+=1
        case.update(admitted=True,source_sha256=hashes(candidate),protected_file_comparisons=protected,
                    protected_body_boundaries=len(task['editable_files']),guard_decision=decision,
                    edited_body_sha256={n:digest(s.encode()) for n,s in new_bodies.items()})
        rows.append((case,candidate,proposed))
    assert len(rows)==5
    return rows

def write(root=ROOT):
    rows=candidates(root);(root/'fixtures').mkdir(exist_ok=False);(root/'payloads').mkdir(exist_ok=False)
    for case,source,payload in rows:
        (root/case['payload_path']).write_bytes(payload.encode())
        if source is not None:
            folder=root/case['path'];folder.mkdir()
            for name,raw in source.items():(folder/name).write_bytes(raw)
    save(root/'cases.json',[c for c,_,_ in rows])
    print(json.dumps(dict(cases=len(rows),admitted=sum(c['admitted'] for c,_,_ in rows),model_calls=0,
        new_verifier_invocations=0,protected_files=sum(c.get('protected_file_comparisons',0) for c,_,_ in rows),
        protected_boundaries=sum(c.get('protected_body_boundaries',0) for c,_,_ in rows),original_score='27/32 unchanged'),indent=2))

if __name__=='__main__':write()
