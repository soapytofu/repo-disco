"""Deliberate sequence well-formedness correction; original run is immutable."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
OLD='    SplitReady(s, t) && Total(s[1..] + t) == Total(s[1..]) + Total(t)'
NEW='    |s| > 0 && SplitReady(s, t) && Total(s[1..] + t) == Total(s[1..]) + Total(t)'
def main():
 (ROOT/'fixtures').mkdir(exist_ok=False)
 checks=[]
 for old in json.loads((PARENT/'checks.json').read_text()):
  if not old['task_id'].startswith('sequence-'):continue
  c=dict(old);dst=ROOT/c['path'];dst.mkdir(parents=True)
  hashes={}
  for p in (PARENT/c['path']).glob('*.dfy'):
   s=p.read_text()
   if p.name=='Kernel.dfy':
    assert s.count(OLD)==1;s=s.replace(OLD,NEW)
   (dst/p.name).write_text(s);hashes[p.name]=hashlib.sha256(s.encode()).hexdigest()
  c['source_sha256']=hashes;checks.append(c)
 tasks=[]
 for old in json.loads((PARENT/'tasks.json').read_text()):
  if not old['task_id'].startswith('sequence-'):continue
  t=dict(old);fs=list((ROOT/'fixtures'/t['task_id']/'empty').glob('*.dfy'))
  t['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fs};t['bytes']=sum(p.stat().st_size for p in fs);tasks.append(t)
 for n,v in [('checks.json',checks),('tasks.json',tasks)]: (ROOT/n).write_text(json.dumps(v,indent=2)+'\n')
 shutil.copytree(PARENT/'code',ROOT/'code',ignore=shutil.ignore_patterns('__pycache__'))
 shutil.copy2(PARENT/'preflight.py',ROOT/'preflight.py')
 (ROOT/'build.py').write_text((ROOT/'build_revision.py').read_text())
 # The saved build.py is evidence only; rerun build_revision.py from this folder.
 (ROOT/'verify.sbatch').write_text((PARENT/'verify.sbatch').read_text().replace('remaining-families-001','remaining-families-001/revision-002').replace('calibration-remaining','calibration-seq-revision'))
 print(len(checks),'sequence checks; explicit bounds only; no requests')
if __name__=='__main__':main()
