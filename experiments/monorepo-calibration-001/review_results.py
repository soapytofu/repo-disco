"""Review immutable calibration evidence offline; no Dafny or model calls."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return {f.name:f.read_bytes() for f in p.glob('*.dfy')}
def main():
 out=ROOT/'verification-001';manifest=load(out/'manifest.json');checked=0
 for name,digest in manifest.items():
  p=out/name
  if p.exists():assert sha(p)==digest,name;checked+=1
 checks=load(out/'checks.json');tasks=load(out/'tasks.json');rows=[]
 for c in checks:
  p=out/c['path'];fs=files(p)
  assert {n:hashlib.sha256(v).hexdigest() for n,v in fs.items()}==c['source_sha256']
  assert fs==files(ROOT/c['path'])
  r=load(out/(c['task_id']+'-'+c['variant']+'.json'))
  assert r['source_sha256']==c['source_sha256'] and '--verify-included-files' in r['command']
  diagnostic=r['stdout']+'\n'+r['stderr']
  expected={'success':0,'proof_failure':4,'resolution_failure':2}[c['expected']]
  assert r['exit_code']==expected
  if expected==4:assert any(w in diagnostic.lower() for w in ['precondition','postcondition','assertion']) and 'parse errors' not in diagnostic.lower()
  if expected==2:assert 'unresolved identifier: Direct' in diagnostic and 'resolution/type errors' in diagnostic and 'parse errors' not in diagnostic.lower()
  if expected==0:assert '0 errors' in diagnostic
  rows.append(dict(task_id=c['task_id'],variant=c['variant'],expected=c['expected'],actual_exit=r['exit_code'],verified_source_hashes=True))
 for t in tasks:
  ref=files(out/'fixtures'/t['task_id']/'reference')
  for c in [c for c in checks if c['task_id']==t['task_id']]:
   fs=files(out/c['path'])
   for name in ['Kernel.dfy','Stage1.dfy','Stage2.dfy','Stage3.dfy','ClientA.dfy','ClientB.dfy','All.dfy']:assert fs[name]==ref[name]
  assert t['client_count']==2
 assert len(rows)==26
 assert sum(r['actual_exit']==0 for r in rows)==4
 assert sum(r['actual_exit']==4 for r in rows)==20
 assert sum(r['actual_exit']==2 for r in rows)==2
 assert load(out/'environment.json')['model_calls']==0
 report=dict(job_id='55978267',all_expected=True,checks=26,reference_passes=4,proof_failures=20,hidden_shortcut_resolution_failures=2,parse_errors=0,model_calls=0,pinned_files_checked=checked,rows=rows,limitations='Reference-relative helper proof depth; shared mode adds a forwarding edge and edits one body versus two. No model-performance finding.')
 (ROOT/'results-review.json').write_text(json.dumps(report,indent=2)+'\n')
 (ROOT/'verification-001-sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and '__pycache__' not in p.parts},indent=2)+'\n')
 print('Reviewed26/26:4passes20proof failures2resolution failures;zero model calls')
if __name__=='__main__':main()
