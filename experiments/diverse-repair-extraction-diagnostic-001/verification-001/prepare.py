"""Exact saved-response extraction diagnosis; primary data/policies remain immutable."""
from pathlib import Path
import hashlib,importlib.util,json,re
ROOT=Path(__file__).resolve().parent
FENCE=re.compile(r'^```([^\r\n]*)\r?\n(.*?)^```[ \t]*(?:\r?\n|$)',re.M|re.S)

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def files(path):return {p.name:p.read_bytes() for p in sorted(path.glob('*.dfy'))}
def hashes(fs):return {n:digest(b) for n,b in sorted(fs.items())}
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def policy(root=ROOT):
    return tuple(module('diagnostic_'+name,root/'frozen-001/policy'/f'{name}.py') for name in ('body_guard','extract_response','repair_protocol'))

def extract_one_fence(raw,envelope):
    if not isinstance(raw,str) or len(raw.encode())>envelope.MAX_RESPONSE:raise ValueError('Response type/size')
    matches=list(FENCE.finditer(raw))
    if len(matches)!=1 or matches[0].group(1).strip()!='json':raise ValueError('Require exactly one json-tagged fence and no other fenced block')
    match=matches[0];payload=match.group(2)
    value=json.loads(payload,object_pairs_hook=envelope.unique,parse_constant=envelope.reject_constant)
    if not isinstance(value,dict):raise ValueError('Require a JSON object')
    return payload,dict(fence_start_char=match.start(),fence_end_char=match.end(),payload_start_char=match.start(2),payload_end_char=match.end(2),
        raw_text_sha256=digest(raw.encode()),payload_sha256=digest(payload.encode()),selection='sole explicit json fence; exact substring; no body rewriting')

def validate_inputs(root=ROOT):
    prov=load(root/'provenance.json');frozen=root/'frozen-001'
    assert sha(frozen/'freeze.json')==prov['primary_proposal_freeze_sha256']
    freeze=load(frozen/'freeze.json');actual={str(p.relative_to(frozen)):sha(p) for p in sorted(frozen.rglob('*')) if p.is_file()};actual.pop('freeze.json')
    assert actual==freeze['files'],'Original frozen bundle changed'
    assert sha(root/'primary-archive-manifest.json')==prov['primary_archive_manifest_sha256']
    assert len(load(root/'primary-archive-manifest.json'))==prov['prior_archive_files_preserved']==1204
    assert sha(root/'primary-reviewed-results.json')==prov['primary_results_sha256']
    manifest=load(root/'primary-archive-manifest.json')
    for n,item in prov['parent_copies'].items():assert sha(root/n)==item['sha256']==manifest[item['primary_path']],n
    for n,h in prov['unchanged_runtime_copies'].items():assert sha(root/n)==h,n
    return prov

def candidates(root=ROOT):
    prov=validate_inputs(root);guard,envelope,adapter=policy(root)
    primary=load(root/'primary-reviewed-results.json');primary_rows={r['trial_id']:r for r in primary['rows']}
    trials={t['trial_id']:t for t in load(root/'frozen-001/trials.json')};parents=load(root/'frozen-001/parents.json');rows=[]
    for tid in prov['parent_trials']:
        origin=root/'parents'/tid;trial=trials[tid];parent=parents[trial['parent_id']];task=load(origin/'task.json')
        assert task==load(root/'frozen-001'/parent['task_path'])
        assert trial==load(origin/'trial.json') and task['semantic_instance']=='weave_unweave'
        original_result=load(origin/'result.json');extraction=load(origin/'extraction.json');response=load(origin/'response.json');raw=response['text']
        assert primary_rows[tid]['outcome']==original_result['outcome']=='OUTPUT_REJECTED' and not extraction['accepted'] and extraction['stage']=='envelope'
        try:envelope.extract_json(raw)
        except ValueError as e:assert str(e)==extraction['reason']
        else:raise AssertionError('Original extraction rejection did not replay')
        base=files(root/'frozen-001'/parent['base_path']);template=files(root/'frozen-001'/parent['template_path'])
        assert hashes(base)==parent['source_sha256'] and hashes(template)==parent['template_sha256']==task['source_sha256']
        initial=load(origin/'initial.json');head=load(origin/'final-head.json')
        assert initial['source_sha256']==hashes(base)==head['source_sha256'] and initial['revision']==head['revision']
        payload,selection=extract_one_fence(raw,envelope)
        case=dict(case_id=tid+'-exact-fence',parent_trial=tid,task_id=task['task_id'],sharing=trial['sharing'],feedback_condition=trial['feedback_condition'],
            original_outcome='OUTPUT_REJECTED',original_rejection=extraction['reason'],response_sha256=sha(origin/'response.json'),original_body_policy_sha256=sha(root/'frozen-001/policy/body_guard.py'),
            source_base_sha256=hashes(base),payload_path='payloads/'+tid+'.json',selection=selection,body_rewriting=False,model_calls=0,expected_diagnostic='strict_success_hypothesis')
        try:
            candidate,decision=adapter.apply_response(payload,{n:b.decode() for n,b in base.items()},{n:b.decode() for n,b in template.items()},task,parent['source_sha256'],guard,envelope)
        except (ValueError,TypeError,UnicodeError,RecursionError) as e:
            case.update(admitted=False,diagnostic='body_guard_rejection',error_type=type(e).__name__,reason=str(e));rows.append((case,None,payload));continue
        raw_candidate={n:s.encode() for n,s in candidate.items()};assert set(raw_candidate)==set(base)
        boundaries=0;protected=0;body_shas={}
        parsed=json.loads(payload,object_pairs_hook=envelope.unique,parse_constant=envelope.reject_constant)
        assert set(parsed)==set(task['editable_files'])
        for n,b in base.items():
            if n not in task['editable_files']:assert raw_candidate[n]==b;protected+=1
            else:
                pre,suf=guard.split_seed(template[n].decode());text=raw_candidate[n].decode()
                assert text.startswith(pre) and text.endswith(suf)
                assert text[len(pre):-len(suf)]==parsed[n],'JSON body text changed'
                body_shas[n]=digest(parsed[n].encode());boundaries+=1
        case.update(admitted=True,path='fixtures/'+case['case_id'],source_sha256=hashes(raw_candidate),body_sha256=body_shas,
            protected_files=protected,protected_body_boundaries=boundaries,guard_decision=decision)
        rows.append((case,raw_candidate,payload))
    assert len(rows)==8
    return rows

def write():
    generated=candidates();(ROOT/'fixtures').mkdir(exist_ok=False);(ROOT/'payloads').mkdir(exist_ok=False)
    for row,fs,payload in generated:
        (ROOT/row['payload_path']).write_bytes(payload.encode())
        if fs is not None:
            dest=ROOT/row['path'];dest.mkdir()
            for n,b in fs.items():(dest/n).write_bytes(b)
    save(ROOT/'cases.json',[row for row,_,_ in generated])
    print(json.dumps(dict(model_calls=0,original_score='16/24 unchanged',saved_responses=len(generated),guard_admitted=sum(row['admitted'] for row,_,_ in generated),no_dafny_runs=True)))

if __name__=='__main__':write()
