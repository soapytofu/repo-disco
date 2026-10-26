"""Read saved reviewed evidence only; no verification or model calls."""
from pathlib import Path
import json,hashlib,re,sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from proof_usage_metrics import measure_multiclient
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
def read(path):
 p=ROOT/path;sources[str(path)]=sha(p);return json.loads(p.read_text())
def registry(symbols):return dict(targets={c+'.Prove':{'F':'Facts'} for c in ['ClientA','ClientB']},symbols=['Facts.'+s for s in symbols])
def write(name,payload):
 (OUT/(name+'-input.json')).write_text(json.dumps(payload,indent=2)+'\n')
 (OUT/(name+'-metrics.json')).write_text(json.dumps(measure_multiclient(payload['observations'],payload['repositories'],payload.get('ablations')),indent=2)+'\n')
# Model evidence from the completed eight-trial batch.
rows=[];repos={};calls=read('experiments/sharing-depth-pilot-001/observed-calls.json');review=read('experiments/sharing-depth-pilot-001/model-review.json')
assert review['summary']['calls_dispatched']==8 and all(t['outcome']=='SUCCESS' for t in review['trials'])
for trial in calls:
 repo='depth/'+trial['tier']+'/'+trial['condition'];repos[repo]=registry(['LiftA','JoinA','LiftB','JoinB','Finish'])
 for filename,data in trial['clients'].items():
  target=Path(filename).stem+'.Prove';symbols=[re.match(r'(F\.\w+)\(',line)[1] for line in data['calls']]
  # Read the recorded repeat identifier from the reviewed trial.
  repeat=next(t['repeat'] for t in review['trials'] if t['sequence']==trial['sequence'])
  evidence=f"experiments/sharing-depth-pilot-001/model-001/{trial['sequence']:02d}-{trial['tier']}-{trial['condition']}-r{repeat}/result.json"
  assert read(evidence)['outcome']=='SUCCESS'
  rows.append(dict(repository=repo,trial=trial['sequence'],target=target,outcome='SUCCESS',called_symbols=symbols,evidence=evidence))
write('depth',dict(repositories=repos,observations=rows))
# Reference observations and contract interventions are distinct from model samples.
sensitivity=read('experiments/branch-contract-ablation-001/sensitivity.json');rows=[];repos={};abl=[]
for condition in ['shared','separate']:
 repo='branch-reference/'+condition;repos[repo]=registry(['Case0A','Case1A','Case0B','Case1B'])
 for client in ['ClientA','ClientB']:
  prefix=Path('experiments/branch-contract-ablation-001/verification-001');folder=prefix/'fixtures'/f'{condition}_reference';p=ROOT/folder/(client+'.dfy');sources[str(p.relative_to(ROOT))]=sha(p)
  symbols=re.findall(r'^\s+(F\.\w+)\(',p.read_text(),re.M)
  evidence=str(prefix/'logs'/f'{condition}_reference'/client/'result.json');assert read(evidence)['exit_code']==0
  rows.append(dict(repository=repo,trial='reference',target=client+'.Prove',outcome='SUCCESS',called_symbols=symbols,evidence=evidence))
for item in sensitivity['rows']:
 evidence='experiments/branch-contract-ablation-001/'+item['evidence']+'/result.json';result=read(evidence);assert result['exit_code']==item['ablated_exit']
 abl.append(dict(repository='branch-reference/'+item['repository_condition'],symbol=item['provider_symbol'],target=item['client_target'],baseline_exit=item['baseline_exit'],ablated_exit=item['ablated_exit'],evidence=evidence))
write('branch',dict(repositories=repos,observations=rows,ablations=abl))
(OUT/'source-hashes.json').write_text(json.dumps(sources,indent=2)+'\n')
