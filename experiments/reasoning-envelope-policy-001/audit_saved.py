"""Replay saved model text only. No generation, verifier calls, or old rescoring."""
import hashlib,importlib.util,json
from collections import Counter
from pathlib import Path
import extract_response
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1];pins={}
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
 p=Path(p);b=p.read_bytes();pins[str(p.relative_to(REPO))]=sha(b);return b.decode()
def load(p):return json.loads(read(p))
def sources(p):return {f.name:read(f) for f in sorted(p.glob('*.dfy'))}
gp=ROOT.parent/'monorepo-policy-integration-001/body_guard.py';read(gp)
spec=importlib.util.spec_from_file_location('unchanged_v4',gp);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
catalog={t['task_id']:t for t in load(ROOT.parent/'monorepo-policy-integration-001/task-catalog.json')['tasks']}
rows=[]
def check(trial,task,seed,rawpath,expected,original,evidence):
 response=load(rawpath);raw=response['text'];payload,span=extract_response.extract_json(raw)
 candidate,decision=extract_response.parse_response(raw,seed,task,guard)
 actual={n:sha(s.encode()) for n,s in candidate.items()};assert actual==expected,trial
 for n in seed:
  if n not in task['editable_files']:assert candidate[n]==seed[n]
 bodies=json.loads(payload,object_pairs_hook=extract_response.unique)
 for n,b in bodies.items():
  prefix,suffix=guard.split_seed(seed[n]);assert candidate[n]==prefix+b+suffix
 rows.append(dict(trial_id=trial,task_id=task['task_id'],original_outcome=original,
  response_path=str(rawpath.relative_to(REPO)),original_evidence=evidence,extraction=span,
  candidate_sha256=actual,body_strings_preserved=True,protected_sources_preserved=True,semantic_verification_performed=False))

audit=load(ROOT.parent/'reasoning-output-policy-002/compatibility-audit.json')
for prior in audit['saved_responses']:
 cat=catalog[prior['task_id']];tasks=load(REPO/cat['task_metadata_path']);task=next(t for t in tasks if t['task_id']==cat['task_id'])
 check(prior['trial_id'],task,sources(REPO/cat['seed_path']),REPO/prior['response_path'],prior['candidate_sha256'],prior['original_outcome'],'experiments/reasoning-output-policy-002/compatibility-audit.json')

pilot=ROOT.parent/'conditional-monotonicity-pilot-001';cases={c['case_id']:c for c in load(pilot/'extraction-diagnostic-001/cases.json')}
for folder in sorted((pilot/'model-001').glob('monotone-*')):
 if not folder.is_dir():continue
 task=load(folder/'task.json');seed=sources(ROOT.parent/'conditional-monotonicity-001/fixtures'/task['task_id']/'empty')
 if folder.name in cases:
  expected=cases[folder.name]['candidate_sha256'];ev='experiments/conditional-monotonicity-pilot-001/extraction-diagnostic-001/verification-001'
 else:expected=load(folder/'candidate-hashes.json')['candidate_sha256'];ev=str((folder/'verification.json').relative_to(REPO))
 check(folder.name,task,seed,folder/'response.json',expected,load(folder/'result.json')['outcome'],ev)

pilot=ROOT.parent/'monorepo-balanced-calibration-pilot-001'
for trial in load(pilot/'frozen-001/trials.json'):
 if not trial['task_id'].startswith('witness-'):continue
 folder=pilot/'model-001'/trial['trial_id'];task=load(folder/'task.json');cat=catalog[task['task_id']]
 expected=load(folder/'verification.json')['source_sha256']
 check(folder.name,task,sources(REPO/cat['seed_path']),folder/'response.json',expected,load(folder/'result.json')['outcome'],str((folder/'verification.json').relative_to(REPO)))
assert len(rows)==40
for name,h in pins.items():assert sha((REPO/name).read_bytes())==h
report=dict(policy_version=extract_response.VERSION,extractor_sha256=sha((ROOT/'extract_response.py').read_bytes()),
 body_guard_sha256=pins[str(gp.relative_to(REPO))],audit_script_sha256=sha(Path(__file__).read_bytes()),
 new_model_calls=0,new_verifier_invocations=0,admitted=len(rows),exact_prior_candidate_matches=len(rows),
 original_outcomes=dict(Counter(r['original_outcome'] for r in rows)),
 interpretation='Compatibility replay of development evidence, not new model trials or replacement scores. Mathematical failures remain failures.',
 input_sha256=pins,results=rows)
(ROOT/'saved-response-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['input_sha256','results']},indent=2))
