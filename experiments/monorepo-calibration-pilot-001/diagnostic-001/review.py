"""Review separate diagnostic evidence and bind it to unchanged original responses."""
import hashlib,json
from pathlib import Path
import guard
ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 out=ROOT/'verification-001';cases=load(ROOT/'cases.json');rows=[]
 for n,h in load(out/'manifest.json').items():
  p=out/n
  if p.exists():assert sha(p.read_bytes())==h
 for c in cases:
  p=ROOT.parent/'model-001'/c['trial_id'];assert sha((p/'response.json').read_bytes())==c['original_response_sha256']
  task=c['task'];original,_=guard.extract(load(p/'response.json')['text'],task['editable_files'])
  seed={f.name:f.read_bytes() for f in (ROOT.parent/'frozen-001/tasks'/task['task_id']).glob('*.dfy')}
  expected=dict(seed);expected.update({n:(s if s.endswith('\n') else s+'\n').encode() for n,s in original.items()})
  fs={p.name:p.read_bytes() for p in (out/c['path']).glob('*.dfy')}
  assert fs==expected=={p.name:p.read_bytes() for p in (ROOT/c['path']).glob('*.dfy')}
  assert {n:sha(b) for n,b in fs.items()}==c['candidate_sha256']
  guard.validate_files({n:fs[n].decode() for n in task['editable_files']},{n:b.decode() for n,b in seed.items()},task)
  v=load(out/(c['trial_id']+'.json'));assert v['source_sha256']==c['candidate_sha256'];assert '--verify-included-files' in v['command']
  assert v['exit_code'] in (0,2,4)
  rows.append(dict(trial_id=c['trial_id'],task_id=task['task_id'],original_outcome='OUTPUT_REJECTED',diagnostic_exit=v['exit_code'],diagnostic_verified=v['exit_code']==0,original_reason=c['original_reason'],appended_lf=c['appended_lf'],response_sha256=c['original_response_sha256'],candidate_sha256=c['candidate_sha256']))
 assert len(rows)==11;env=load(out/'environment.json');assert env['model_calls']==0
 # Main score stays fixed; no accepted records or original sources are rewritten.
 assert load(ROOT.parent/'results-review.json')['verified']==18
 report=dict(job_id=env['job_id'],new_model_calls=0,candidates=11,verified=sum(r['diagnostic_verified'] for r in rows),original_strict_score='18/32 unchanged',excluded_wrapper_failures=3,post_hoc_diagnostic=True,rows=rows)
 (ROOT/'results-review.json').write_text(json.dumps(report,indent=2)+'\n')
 (ROOT/'verification-001-sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()},indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
if __name__=='__main__':main()
