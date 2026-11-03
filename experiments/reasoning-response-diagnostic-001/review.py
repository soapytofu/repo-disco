"""Offline review of exact diagnostic bytes and distinct exit categories."""
import collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PILOT=ROOT.parent/'monorepo-reasoning-calibration-pilot-001'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def review():
 out=ROOT/'verification-001';manifest=load(ROOT/'manifest.json')
 assert sha(ROOT/'manifest.json')=='b719150f64f7116cb728f22ad1a797ae3d35673ca5feee892141824ea026c099'
 assert sha(out/'snapshot/manifest.json')==sha(ROOT/'manifest.json')
 for n,h in manifest.items():assert sha(ROOT/n)==sha(out/'snapshot'/n)==h,n
 cases=load(ROOT/'cases.json');summary=load(out/'summary.json');rows=[]
 assert summary['completed_cases']==len(cases)==6 and summary['model_calls']==0
 env=load(out/'environment.json')
 assert env['job_id']=='57167108' and 'login' not in env['host'] and env['model_calls']==0
 assert env['dafny']=='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
 assert env['z3']=='Z3 version 4.12.1 - 64 bit'
 for case,record in zip(cases,summary['results']):
  path=out/(case['case_id']+'.json');assert load(path)==record and record['case']==case and record['model_calls']==0
  original=PILOT/'model-001'/case['original_trial']
  assert sha(original/'response.json')==case['original_response_sha256']
  assert sha(original/'result.json')==case['original_result_sha256']
  v=record['evidence'];hashes={p.name:sha(p) for p in (out/'snapshot'/case['path']).glob('*.dfy')}
  assert hashes==case['candidate_sha256']==v['source_sha256']
  assert v['command']==['timeout','-k','5s','60s','dafny','verify','--verify-included-files','All.dfy']
  assert v['attempts']==1 and v['model_calls']==0
  diagnostic=v['stdout']+'\n'+v['stderr'];code=v['exit_code']
  if code==0:
   assert '0 errors' in diagnostic and 'Error:' not in diagnostic
   category='strict_success'
  elif code==4:
   assert 'assertion might not hold' in diagnostic and 'parse error' not in diagnostic.lower()
   category='assertion_failure'
  elif code==2:
   assert '0 errors' in diagnostic and 'Error:' not in diagnostic
   assert 'Could not find a trigger for this quantifier' in diagnostic
   assert 'Compilation failed because warnings were found and --allow-warnings is false' in diagnostic
   category='warning_only_nonzero_exit'
  else:raise ValueError('Unexpected diagnostic exit')
  rows.append(dict(case_id=case['case_id'],original_trial=case['original_trial'],original_outcome=case['original_outcome'],
   source_sha256=hashes,record_sha256=sha(path),unchanged_body_strings=case['unchanged_body_strings'],
   mutation=case['mutation'],exit_code=code,diagnostic_category=category,stdout=v['stdout'],stderr=v['stderr']))
 old_manifest=load(PILOT/'model-001-sha256.json')
 assert {str(p.relative_to(PILOT/'model-001')):sha(p) for p in (PILOT/'model-001').rglob('*') if p.is_file()}==old_manifest
 original=load(PILOT/'results-review.json');assert original['verified']==18 and original['returned']==24
 report=dict(job_id='57167108',new_model_calls=0,diagnostic_verifier_runs=6,
  counts=dict(collections.Counter(row['diagnostic_category'] for row in rows)),
  unchanged_rejected_body_strict_successes=sum(row['unchanged_body_strings'] and row['exit_code']==0 for row in rows),
  inserted_fact_repair_strict_success=next(row['exit_code']==0 for row in rows if row['mutation']),
  original_pilot_score='18/24 unchanged',original_model_archive_hashes_unchanged=True,rows=rows,
  interpretation='One-off hash-pinned diagnostic, not a revised output policy or retrospective acceptance. Warnings are not strict successes or parse/proof failures.')
 (ROOT/'diagnostic-review.json').write_text(json.dumps(report,indent=2)+'\n')
 (ROOT/'verification-001-sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
if __name__=='__main__':review()
