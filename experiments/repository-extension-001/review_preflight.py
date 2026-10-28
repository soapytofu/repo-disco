"""Review exact archived source hashes and expected diagnostics offline."""
import hashlib,json
from extension import ROOT,sources,prepare,hashes

def load(p):return json.loads(p.read_text())
def main():
 out=ROOT/'verification-001';manifest=load(out/'manifest.json')
 checked=[]
 for name,digest in manifest.items():
  p=out/name
  if p.exists():
   assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name;checked.append(name)
 tasks=load(out/'tasks.json');rows=[]
 for folder in sorted(out.iterdir()):
  if not folder.is_dir() or not (folder/'verification.json').exists():continue
  r=load(folder/'verification.json');fs=sources(folder/'sources')
  assert hashes(fs)==r['source_sha256']
  if r['name'].startswith('seed-'):assert fs==sources(out/'seeds'/r['name'][5:])
  else:
   task_id,label=r['name'].rsplit('-',1);task=next(t for t in tasks if t['id']==task_id)
   seed=sources(out/'seeds'/task['family'])
   assert fs==prepare(seed,task,(out/'controls'/task_id/(label+'.json')).read_text())
  assert r['exit_code']==r['expected_exit'] and '--verify-included-files' in r['command']
  if r['expected_exit']==4:
   assert any(t in r['stdout'].lower() for t in ['postcondition','precondition'])
   assert not any(t in r['stdout'].lower() for t in ['parse errors','unresolved identifier','resolution/type errors'])
  rows.append(dict(name=r['name'],exit_code=r['exit_code'],source_sha256=r['source_sha256']))
 assert len(rows)==14 and sum(r['exit_code']==0 for r in rows)==6
 assert load(out/'environment.json')['model_calls']==0
 result=dict(job='55810726',all_expected=True,checks=14,reference_and_seed_passes=6,proof_failures=8,model_calls=0,pinned_files_checked=len(checked),results=rows)
 (ROOT/'preflight-review.json').write_text(json.dumps(result,indent=2)+'\n');print('14/14 reviewed; six passes, eight targeted proof failures; zero model calls')
if __name__=='__main__':main()
