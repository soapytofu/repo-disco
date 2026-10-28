"""Review exact source evidence and diagnostics, retaining unexpected outcomes."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def review(root):
 out=root/'verification-001';checks=load(out/'checks.json');summary=load(out/'summary.json')
 if len(checks)!=summary['completed']:raise ValueError('Incomplete evidence')
 pinned=load(out/'manifest.json');verified=[]
 for n,h in pinned.items():
  p=out/n
  if p.exists():
   if sha(p)!=h:raise ValueError('Pin mismatch: '+n)
   verified.append(n)
 rows=[]
 for c in checks:
  fs={p.name:p.read_bytes() for p in (out/c['path']).glob('*.dfy')}
  hashes={n:hashlib.sha256(b).hexdigest() for n,b in fs.items()}
  if hashes!=c['source_sha256']:raise ValueError('Snapshot changed')
  if fs!={p.name:p.read_bytes() for p in (root/c['path']).glob('*.dfy')}:raise ValueError('Live fixture drift')
  r=load(out/(c['task_id']+'-'+c['variant']+'.json'));text=r['stdout']+'\n'+r['stderr']
  if r['source_sha256']!=hashes or '--verify-included-files' not in r['command']:raise ValueError('Verifier invocation/source mismatch')
  lower=text.lower()
  if r['exit_code']==0:category='success'
  elif 'parse errors' in lower:category='parse_failure'
  elif r['exit_code']==2 and 'unresolved identifier: Direct' in text:category='resolution_failure'
  elif r['exit_code']==4 and any(s in lower for s in ['out of range','index out of range','division by zero']):category='well_formedness_failure'
  elif r['exit_code']==4 and any(s in lower for s in ['decreases','termination']):category='termination_failure'
  elif r['exit_code']==4 and any(s in lower for s in ['precondition','postcondition','assertion','for this call']):category='proof_failure'
  else:category='unexpected_diagnostic'
  matched=category==c['expected'] or c['expected']=='proof_failure' and category=='termination_failure' and c['variant']=='nondecreasing_recursion'
  if c['variant']=='nondecreasing_recursion' and category!='termination_failure':matched=False
  # Non-target files remain exact, including trusted providers and immutable clients.
  ref=root/'fixtures'/c['task_id']/'reference'
  for n,b in fs.items():
   if n not in ['HelperA.dfy','HelperB.dfy'] and b!=(ref/n).read_bytes():raise ValueError('Protected control source drift')
  rows.append(dict(task_id=c['task_id'],variant=c['variant'],expected=c['expected'],category=category,exit_code=r['exit_code'],matched=matched,evidence=str((out/(c['task_id']+'-'+c['variant']+'.json')).relative_to(root)),source_sha256=hashes))
 env=load(out/'environment.json')
 if env['model_calls']!=0:raise ValueError('Unexpected model calls')
 report=dict(job_id=env['job_id'],model_calls=0,checks=len(rows),matched=sum(r['matched'] for r in rows),all_expected=all(r['matched'] for r in rows),pinned_files_reviewed=len(verified),results=rows)
 (root/'results-review.json').write_text(json.dumps(report,indent=2)+'\n')
 (root/'verification-001-sha256.json').write_text(json.dumps({str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and '__pycache__' not in p.parts},indent=2)+'\n')
 print(report['job_id'],report['matched'],'/',len(rows),'expected')
 for r in rows:
  if not r['matched']:print(r['task_id'],r['variant'],r['category'])
 return report
if __name__=='__main__':review(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT)
