"""Offline source, protected-boundary, named-scope and diagnostic audit."""
import csv,hashlib,io,json,re,sys
from collections import Counter
from pathlib import Path
BASE=Path(__file__).resolve().parent
TOOLCHAIN='4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2'
COMMAND=['timeout','-k','5s','60s','dafny','verify','--verify-included-files','--log-format','csv','All.dfy']
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def categorize(ev):
 text=ev['stdout']+'\n'+ev['stderr'];code=ev['exit_code']
 summaries=re.findall(r'^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$',text,re.M)
 if re.search(r'parse errors? detected',text,re.I):return 'parse_failure'
 if code==2 and re.search(r'resolution/type errors? detected',text,re.I):return 'resolution_failure'
 if len(summaries)!=1:return 'incomplete_verifier_evidence'
 verified,errors=map(int,summaries[0]);warnings='warning' in text.lower()
 if code==0 and verified>0 and errors==0 and ': Error:' not in text and not warnings:return 'success'
 if warnings:return 'warning_or_other'
 if code==4 and errors>0:
  return 'termination_failure' if re.search(r'decreases|termination',text,re.I) else 'proof_failure'
 return 'other'
def names(files):
 result=set()
 for n,b in files.items():
  t=b.decode();modules=re.findall(r'^module (\w+)\s*\{',t,re.M)
  assert len(modules)<=1,(n,modules)
  if not modules:continue
  for lemma in re.findall(r'\blemma\s+(?:\{:[^}]*\}\s*)*(\w+)\s*\(',t):result.add(modules[0]+'.'+lemma)
 return result
def review(root):
 for manifest in ['runtime-manifest.json','fixture-manifest.json']:
  for n,h in load(root/manifest).items():assert sha((root/n).read_bytes())==h,n
 out=root/'verification-001';cases=load(root/'cases.json');tasks={t['task_id']:t for t in load(root/'tasks.json')};summary=load(out/'summary.json')
 assert summary['planned']==len(cases) and summary['completed']==len(cases)
 assert summary['model_calls']==0
 env=load(out/'environment.json');assert env['model_calls']==0 and env['dafny']==TOOLCHAIN and 'login' not in env['host']
 submission=load(root/'submission-001.json');assert env['job_id']==submission['job_id']
 assert 'PreemptMode=OFF' in submission['live_partition'] and submission['no_requeue']
 assert sha((root/'runtime-manifest.json').read_bytes())==submission['runtime_manifest_sha256']
 assert sha((root/'fixture-manifest.json').read_bytes())==submission['fixture_manifest_sha256']
 # The verifier's source snapshot must match the exact submitted bytes.
 for p in out.rglob('*.dfy'):
  rel=p.relative_to(out);assert (root/rel).read_bytes()==p.read_bytes(),str(rel)
 for name in ['tasks.json','cases.json','verify.py','fixture-manifest.json']:
  assert (out/name).read_bytes()==(root/name).read_bytes(),name
 scope_by_task={};rows=[];protected=0;boundaries=0
 for c in cases:
  fs={p.name:p.read_bytes() for p in sorted((root/c['path']).glob('*.dfy'))}
  assert {n:sha(b) for n,b in fs.items()}==c['source_sha256']
  ev=load(out/(c['case_id']+'.json'))
  assert ev['command']==COMMAND and ev['attempts']==1 and ev['model_calls']==0
  assert ev['source_sha256']==c['source_sha256']
  assert {n:sha(s.encode()) for n,s in ev['csv'].items()}==ev['csv_sha256']
  actual=categorize(ev);text=ev['stdout']+'\n'+ev['stderr'];tid=c['task_id'];task=tasks[tid]
  template_path=root/'templates'/tid
  if not template_path.is_dir():template_path=root/'fixtures'/tid/'empty'
  template={p.name:p.read_bytes() for p in template_path.glob('*.dfy')}
  assert {n:sha(b) for n,b in template.items()}==task['source_sha256']
  for name,body in fs.items():
   if name not in task['editable_files']:assert body==template[name],(c['case_id'],name);protected+=1
   else:
    # These generator-owned templates have one empty Prove body, fixed suffix.
    empty=template[name].decode();at=empty.index('  {\n',empty.index('lemma {:induction false} Prove'))+4
    end=empty.rindex('  }\n}\n');assert at==end
    candidate=body.decode();assert candidate.startswith(empty[:at]) and candidate.endswith(empty[end:]),(c['case_id'],name)
    boundaries+=1
  csvrows=[row for raw in ev['csv'].values() for row in csv.DictReader(io.StringIO(raw))]
  units={row['TestResult.DisplayName']:row['TestResult.Outcome'] for row in csvrows}
  assert len(units)==len(csvrows),'Duplicate verification unit'
  unverified_providers=[]
  if actual in ['success','proof_failure','termination_failure']:
   assert csvrows and set(units.values())<={'Passed','Failed'}
   declarations={re.sub(r' \([^)]*\)$','',n) for n in units}
   assert names(fs)<=declarations,(c['case_id'],'missing lemma coverage',names(fs)-declarations)
   if tid not in scope_by_task:scope_by_task[tid]=sorted(units)
   assert sorted(units)==scope_by_task[tid],(c['case_id'],'changed verification scope')
   unverified_providers=[n for n,v in units.items() if not n.startswith(('HelperA.','HelperB.')) and v!='Passed']
   if actual=='success':assert all(v=='Passed' for v in units.values())
   elif actual in ['proof_failure','termination_failure']:assert 'Failed' in units.values()
  diagnostic=c.get('primary_diagnostic',c.get('expected_diagnostic'))
  diag_ok=not diagnostic or diagnostic=='none' or diagnostic.lower() in text.lower()
  if diagnostic=='missing export member':diag_ok=bool(re.search(r'unresolved identifier|does not exist|has not been declared|no member',text,re.I))
  primary_error_files=re.findall(r'(?m)^([^\n(]+\.dfy)\([^\n]*\): Error:',text)
  helper_errors_only=all(Path(n).name in task['editable_files'] for n in primary_error_files)
  matched=actual==c['expected'] and diag_ok and not unverified_providers and (actual=='success' or helper_errors_only)
  rows.append(dict(case_id=c['case_id'],task_id=tid,variant=c['variant'],expected=c['expected'],actual=actual,expected_diagnostic=diagnostic,diagnostic_match=diag_ok,matched=matched,
   unverified_providers=unverified_providers,primary_error_files=primary_error_files,named_units=len(units),failed_units=[n for n,v in units.items() if v!='Passed'],evidence_sha256=sha((out/(c['case_id']+'.json')).read_bytes())))
 result=dict(job_id=env['job_id'],model_calls=0,planned=len(cases),reviewed=len(rows),all_expected=all(r['matched'] for r in rows),counts=dict(Counter(r['actual'] for r in rows)),
  protected_file_comparisons=protected,protected_body_boundaries=boundaries,scope_by_task=scope_by_task,checks=rows,claim='Verifier-only development controls; no model result, minimum-depth or causal sharing claim')
 save(root/'results-review.json',result)
 save(root/'verification-001-sha256.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()})
 print(json.dumps({k:v for k,v in result.items() if k not in ['checks','scope_by_task']},indent=2))
 return result
if __name__=='__main__':
 assert len(sys.argv)==2;root=(BASE/sys.argv[1]).resolve();assert root.is_relative_to(BASE) and root!=BASE
 result=review(root);raise SystemExit(0 if result['all_expected'] else 1)
