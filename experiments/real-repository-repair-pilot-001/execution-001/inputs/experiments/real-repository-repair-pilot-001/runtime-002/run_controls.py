"""Six fixed verifier-only seed/empty checks; no model or provider client."""
import json,os,shutil,socket,zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from capture import capture,digest,write
from gates.vmc import protocol as dg
from gates.vest import protocol_v2 as vg
ROOT=Path(__file__).resolve().parent
QUAL=ROOT.parent.parent/'real-repository-qualification-001'
def qualification_file(n):
 return ROOT/'qualification-evidence'/n if n.endswith('/review-001.json') else QUAL/n
def files(root,exclude_results=False):
 return {p.relative_to(root).as_posix():digest(p.read_bytes()) for p in root.rglob('*') if p.is_file() and not(exclude_results and p.relative_to(root).as_posix().startswith('TestResults/'))}
def main():
 assert os.environ.get('SLURM_JOB_ID') and 'login' not in socket.gethostname().lower()
 for n,h in json.loads((ROOT/'runtime-manifest.json').read_bytes()).items():assert digest((ROOT/n).read_bytes())==h,n
 for n,h in json.loads((ROOT/'qualification-pins.json').read_bytes()).items():assert digest(qualification_file(n).read_bytes())==h,n
 out=ROOT/'verification-001';out.mkdir(exist_ok=False)
 tasks={t['id']:t for t in json.loads((ROOT/'tasks.json').read_bytes())};controls=json.loads((ROOT/'controls.json').read_bytes())
 profiles={k:json.loads((QUAL/p).read_bytes()) for k,p in [('dafny-vmc','coverage-001/profile.json'),('vest','vest-coverage-001/profile.json')]}
 projects={p['id']:p for p in json.loads((QUAL/'source-manifest.json').read_bytes())}
 write(out/'environment.json',dict(job_id=os.environ['SLURM_JOB_ID'],host=socket.gethostname(),model_calls=0,manifest_sha256=digest((ROOT/'runtime-manifest.json').read_bytes())))
 for name in projects:
  assert files(QUAL/'upstream'/name)==projects[name]['files']
 for img in ['container-003','vest-container-004']:
  pinned=json.loads((QUAL/img/'results/image.json').read_bytes());assert digest((QUAL/img/'runtime.sif').read_bytes())==pinned['sif_sha256']
 # Check exact installed tool files against the successful qualification closures.
 for base,record in [(QUAL/'toolchains/dafny-vmc/unpacked','coverage-001/results/tool-closure.json'),(QUAL/'vest-container-002/tools/unpacked','vest-container-004/results/verus-tool-closure.json')]:
  closure=json.loads((QUAL/record).read_bytes())
  for n,h in closure.items():assert digest((base/n).read_bytes())==h,n
 def one(c):
  t=tasks[c['task']];project=t['project'];base=profiles[project];label=c['id'];work=ROOT/'work'/label
  shutil.copytree(QUAL/'upstream'/project,work);replacement=(ROOT/c['fixture']).read_bytes();assert digest(replacement)==c['sha256']
  (work/t['file']).write_bytes(replacement);expected={**projects[project]['files'],t['file']:c['sha256']};assert files(work)==expected
  env=dict(os.environ)
  if project=='dafny-vmc':
   logical=['verify','dfyconfig.toml',*sorted(base['explicit_sources']),'--resource-limit','20000','--log-format','csv']
   prefix=['singularity','exec','--cleanenv','--bind',str(QUAL.parent)+':'+str(QUAL.parent),'--pwd',str(work),'--env','DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1',str(QUAL/'container-003/runtime.sif'),str(QUAL/'toolchains/dafny-vmc/unpacked/dafny/dafny')]
   cmd=prefix+logical;limit=180;gate=dg;required=base['required_units']
  else:
   prefix=json.loads((QUAL/'vest-container-004/results/invocation-prefix.json').read_bytes())['prefix'];prefix[prefix.index('--bind')+1]=str(QUAL.parent)+':'+str(QUAL.parent);prefix[prefix.index('--pwd')+1]=str(work);prefix[-1:-1]=['--env','CARGO_BUILD_JOBS=4']
   target=ROOT/'targets'/label;assert not target.exists()
   logical=['cargo','verus','verify','-p','vest_dev','--locked','--offline','--check-toolchain','--target-dir','<FRESH_TARGET>','--','--expand-errors','--output-json','--time-expanded','--num-threads','3']
   cmd=prefix+[str(target) if x=='<FRESH_TARGET>' else x for x in logical];limit=900;gate=vg;required=base['required']
  record=capture(label,cmd,ROOT,out,env,limit);d=out/label
  raw={n:(d/n).read_bytes() for n in ['stdout.txt','stderr.txt','resources.txt']}
  if project=='dafny-vmc':
   for f in work.rglob('*.csv'):
    n='csv/'+f.relative_to(work).as_posix();raw[n]=f.read_bytes();p=d/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw[n])
  after=files(work,exclude_results=project=='dafny-vmc');assert after==expected
  profile=dict(task=t,control=c,source_sha256=expected,logical_command=logical,toolchain=base['toolchain'],required=required)
  bound=dict(run_id=os.environ['SLURM_JOB_ID']+':'+label,profile_sha256=gate.sha(gate.canonical(profile)),source_sha256=expected,source_after_sha256=after,logical_command=logical,toolchain=base['toolchain'],raw_sha256={n:gate.sha(b) for n,b in sorted(raw.items())},model_calls=0,attempts=1,exit_code=record['exit_code'],elapsed_seconds=record['elapsed_seconds'])
  write(d/'profile.json',profile);write(d/'bound-record.json',bound);gate.check_record(bound,profile,bound['run_id'],raw)
  if project=='dafny-vmc':o=dg.dafny_observation(record['exit_code'],raw['stdout.txt'],raw['stderr.txt'],{n:b for n,b in raw.items() if n.startswith('csv/')},required)
  else:o=vg.verus_observation(record['exit_code'],raw['stdout.txt'],raw['stderr.txt'],required)
  write(d/'observation.json',o)
  return dict(id=label,exit_code=record['exit_code'],category=o['category'],model_calls=0)
 try:
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(one,controls))
  write(out/'complete.json',dict(controls=results,model_calls=0,expectations_not_inferred=True))
 except Exception as e:
  write(out/'failure.json',dict(type=type(e).__name__,message=str(e)));raise
if __name__=='__main__':main()
