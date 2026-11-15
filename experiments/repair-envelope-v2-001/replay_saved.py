"""Development compatibility audit of saved text, never fresh trials or rescoring."""
from pathlib import Path
from collections import Counter
import hashlib,importlib.util,json
import extract_response as e
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1];PINS={}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):
    raw=path.read_bytes();PINS[str(path.relative_to(REPO))]=sha(raw);return raw.decode()
def load(path):return json.loads(read(path))
def sources(path):return {p.name:read(p) for p in sorted(path.glob('*.dfy'))}
def module(name,path):
    read(path);spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def record(label,rawpath,raw,task,seeds,expected,guard,original,*,base=None,adapter=None):
    row=dict(dataset=label,response_path=str(rawpath.relative_to(REPO)),task_id=task['task_id'],original_outcome=original,
        response_sha256=PINS[str(rawpath.relative_to(REPO))],new_verifier_invocations=0,body_rewriting=False)
    try:payload,span=e.extract_json(raw)
    except ValueError as error:
        row.update(admitted=False,rejection_stage='envelope',reason=str(error));return row
    try:
        if adapter is None:candidate,decision=e.parse_response(raw,seeds,task,guard)
        else:candidate,decision=adapter.apply_response(raw,base,seeds,task,{n:sha(s.encode()) for n,s in base.items()},guard,e)
    except (ValueError,TypeError,UnicodeError,RecursionError) as error:
        row.update(admitted=False,rejection_stage='body_guard',reason=str(error));return row
    hashes={n:sha(s.encode()) for n,s in candidate.items()};assert hashes==expected,row['response_path']
    bodies=json.loads(payload,object_pairs_hook=e.unique,parse_constant=e.reject_constant)
    for n in seeds:
        if n not in task['editable_files']:assert candidate[n]==seeds[n]
        else:
            pre,suf=guard.split_seed(seeds[n]);assert candidate[n]==pre+bodies[n]+suf
    row.update(admitted=True,candidate_sha256=hashes,exact_expected_candidate_match=True,protected_files_preserved=True,body_strings_preserved=True,extraction=span)
    return row

def audit():
    rows=[];pilot=ROOT.parent/'diverse-repair-pilot-001';frozen=pilot/'frozen-001'
    original_manifest=load(pilot/'model-001-sha256.json');assert len(original_manifest)==1204
    assert {str(p.relative_to(pilot/'model-001')) for p in (pilot/'model-001').rglob('*') if p.is_file()}==set(original_manifest)
    for name,h in original_manifest.items():assert sha((pilot/'model-001'/name).read_bytes())==h,name
    read(frozen/'policy/extract_response.py')
    read(ROOT.parent/'reasoning-envelope-policy-001/test_extract.py')
    read(ROOT.parent/'reasoning-envelope-policy-001/policy-freeze.json')
    primary=load(pilot/'reviewed-results.json');primary_rows={r['trial_id']:r for r in primary['rows']}
    guard=module('original_diverse_guard',frozen/'policy/body_guard.py');adapter=module('original_diverse_adapter',frozen/'policy/repair_protocol.py')
    parents=load(frozen/'parents.json');diagnostic=load(ROOT.parent/'diverse-repair-extraction-diagnostic-001/cases.json');extracted={c['parent_trial']:c for c in diagnostic}
    for trial in load(frozen/'trials.json'):
        folder=pilot/'model-001'/trial['trial_id'];task=load(folder/'task.json');parent=parents[trial['parent_id']]
        base=sources(frozen/parent['base_path']);seeds=sources(frozen/parent['template_path'])
        assert {n:sha(s.encode()) for n,s in base.items()}==parent['source_sha256']
        response=load(folder/'response.json');original=primary_rows[trial['trial_id']]['outcome']
        expected=(load(folder/'candidate-hashes.json')['candidate_sha256'] if original=='VERIFIED' else extracted[trial['trial_id']]['source_sha256'])
        rows.append(record('diverse_repair_24',folder/'response.json',response['text'],task,seeds,expected,guard,original,base=base,adapter=adapter))
    old=load(ROOT.parent/'reasoning-envelope-policy-001/saved-response-audit.json')
    catalog={t['task_id']:t for t in load(ROOT.parent/'monorepo-policy-integration-001/task-catalog.json')['tasks']}
    guard=module('original_v4_guard',ROOT.parent/'monorepo-policy-integration-001/body_guard.py')
    for prior in old['results']:
        cat=catalog[prior['task_id']];task=next(t for t in load(REPO/cat['task_metadata_path']) if t['task_id']==prior['task_id'])
        seed=sources(REPO/cat['seed_path']);path=REPO/prior['response_path'];response=load(path)
        rows.append(record('earlier_envelope_40',path,response['text'],task,seed,prior['candidate_sha256'],guard,prior['original_outcome']))
    assert len(rows)==64
    for name,h in PINS.items():assert sha((REPO/name).read_bytes())==h,name
    by_dataset={name:dict(saved_responses=sum(r['dataset']==name for r in rows),envelope_and_body_admitted=sum(r['dataset']==name and r['admitted'] for r in rows),
        rejection_reasons=dict(Counter(r['reason'] for r in rows if r['dataset']==name and not r['admitted']))) for name in ('diverse_repair_24','earlier_envelope_40')}
    report=dict(policy_version=e.VERSION,extractor_sha256=sha((ROOT/'extract_response.py').read_bytes()),audit_script_sha256=sha(Path(__file__).read_bytes()),
        model_calls=0,new_verifier_invocations=0,primary_diverse_score_unchanged='16/24',primary_archive_files_preserved=1204,
        total_saved_responses=len(rows),datasets=by_dataset,exact_prior_candidate_matches=sum(r['admitted'] for r in rows),
        interpretation='Prospective protocol development on inspected saved responses. These are syntax/body compatibility replays, not new model successes, mathematical verification, blind evaluation or replacement scores.',
        input_sha256=PINS,results=rows)
    (ROOT/'saved-response-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('input_sha256','results')},indent=2))

if __name__=='__main__':audit()
