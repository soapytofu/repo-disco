"""Two explicitly analyst-authored diagnostics; original pilot remains untouched."""
import hashlib,importlib.util,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent;EXP=ROOT.parent;PILOT=EXP/'witness-map-calibration-pilot-001'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(fs):return {n:hashlib.sha256(s.encode()).hexdigest() for n,s in sorted(fs.items())}
def files(p):return {f.name:f.read_text() for f in sorted(p.glob('*.dfy'))}
def module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def transform(body,variant):
 if variant=='added_inner_fact':
  needle='O2.DropAt(outer,k,q);';assert body.count(needle)==2
  return body.replace(needle,needle+'\n        if q != j { O2.PutAt(m,k,x,q); }'),2
 needle='(map q | q in m[k := x][j := y] && q != k :: m[k := x][j := y][q])'
 assert body.count(needle)==2
 return body.replace(needle,'K.Drop(K.Put(K.Put(m,k,x),j,y),k)'),2

def main():
 guardpath=PILOT/'frozen-001/policy/body_guard.py';envelopepath=PILOT/'frozen-001/policy/extract_response.py'
 guard=module('diag_guard',guardpath);envelope=module('diag_envelope',envelopepath)
 cases=[];checks=[];inputpins={}
 for index,variant in [(6,'added_inner_fact'),(15,'alias_comprehension')]:
  trial=f'witness-map-{index:02d}';parent=PILOT/'model-001'/trial;task=load(parent/'task.json')
  seedpath=PILOT/'inputs/experiments/witness-map-strengthening-001/fixtures'/task['task_id']/'empty'
  seeds=files(seedpath);response=load(parent/'response.json');original,decision=envelope.parse_response(response['text'],seeds,task,guard)
  assert original==files(parent/'candidate')
  raw,span=envelope.extract_json(response['text']);bodies=json.loads(raw);new={};edits={}
  for name,body in bodies.items():new[name],edits[name]=transform(body,variant)
  payload=json.dumps(new,indent=2)+'\n';candidate,newdecision=envelope.parse_response(payload,seeds,task,guard)
  for name in seeds:
   if name not in task['editable_files']:assert candidate[name]==original[name]==seeds[name]
  dest=ROOT/'fixtures'/variant;dest.mkdir(parents=True,exist_ok=False)
  for n,s in candidate.items():(dest/n).write_text(s)
  source=ROOT/'parents'/variant;source.mkdir(parents=True,exist_ok=False)
  for n in ['task.json','result.json','response.json','verification.json','extraction.json']:
   shutil.copy2(parent/n,source/n);inputpins[str((parent/n).relative_to(EXP.parent))]=sha(parent/n)
  shutil.copytree(parent/'candidate',source/'candidate');shutil.copytree(seedpath,source/'seed')
  for p in [*sorted((parent/'candidate').glob('*.dfy')),*sorted(seedpath.glob('*.dfy'))]:inputpins[str(p.relative_to(EXP.parent))]=sha(p)
  (source/'analyst-body.json').write_text(payload);(source/'analyst-extraction.json').write_text(json.dumps(newdecision,indent=2)+'\n')
  cases.append(dict(variant=variant,source_trial=trial,task_id=task['task_id'],original_outcome=load(parent/'result.json')['outcome'],analyst_authored=True,new_model_calls=0,edit_sites_per_body=edits,original_source_sha256=hashes(original),candidate_sha256=hashes(candidate),protected_contracts_preserved=True))
  checks.append(dict(task_id=task['task_id'],variant=variant,path='fixtures/'+variant,expected='success',source_sha256=hashes(candidate)))
 for name,d in [('cases.json',cases),('checks.json',checks),('original-input-sha256.json',inputpins)]:
  with (ROOT/name).open('x') as f:f.write(json.dumps(d,indent=2)+'\n')
 shutil.copy2(guardpath,ROOT/'body_guard.py');shutil.copy2(envelopepath,ROOT/'extract_response.py')
 base=EXP/'witness-map-strengthening-001/alternative-proof-001'
 shutil.copytree(base/'code',ROOT/'code')
 for n in ['preflight.py','review.py']:
  s=(base/n).read_text().replace('len(checks)!=8','len(checks)!=2').replace('fixed 8 controls','fixed 2 controls');(ROOT/n).write_text(s)
 for n in ['verify.sbatch','ops.py']:
  s=(base/n).read_text().replace('witness-map-strengthening-001/alternative-proof-001','witness-map-diagnostic-001').replace('witness-map-alt','witness-map-diag');(ROOT/n).write_text(s)
 print('Two analyst candidates prepared; originals unchanged; zero model/verifier calls.')
if __name__=='__main__':main()
