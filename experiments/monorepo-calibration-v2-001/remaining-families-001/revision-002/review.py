"""Offline review of exact staged inputs and verifier categories, never rerun."""
import hashlib,json
from pathlib import Path
from preflight import matched
ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 out=ROOT/'verification-001';manifest=load(out/'manifest.json')
 assert manifest==load(ROOT/'manifest.json')
 for n,h in manifest.items():assert sha((out/n).read_bytes())==h==sha((ROOT/n).read_bytes()),n
 checks=load(out/'checks.json');summary=load(out/'summary.json');rows=[]
 assert summary['completed']==summary['planned']==len(checks)
 assert len(summary['results'])==len(checks)
 for check,original in zip(checks,summary['results']):
  row=load(out/(check['task_id']+'-'+check['variant']+'.json'));assert row==original
  assert row['task_id']==check['task_id'] and row['variant']==check['variant']
  files={p.name:sha(p.read_bytes()) for p in (out/check['path']).glob('*.dfy')}
  assert files==check['source_sha256']==row['source_sha256']
  assert '--verify-included-files' in row['command'];assert row['model_calls']==0 and row['attempts']==1
  assert row['matched']==matched(check,row)
  if check['variant']=='reference':
   payload=load(out/(check['task_id']+'-body-payload.json'))
   assert row['protocol_replayed'] and payload['decision']['candidate_sha256']==files
  rows.append(dict(task_id=check['task_id'],variant=check['variant'],expected=check['expected'],exit_code=row['exit_code'],matched=row['matched']))
 env=load(out/'environment.json');assert env['model_calls']==0
 report=dict(job_id=env['job_id'],planned=len(checks),matched=sum(r['matched'] for r in rows),all_expected=all(r['matched'] for r in rows),new_model_calls=0,rows=rows)
 (ROOT/'results-review.json').write_text(json.dumps(report,indent=2)+'\n')
 (ROOT/'verification-001-sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()},indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
if __name__=='__main__':main()
