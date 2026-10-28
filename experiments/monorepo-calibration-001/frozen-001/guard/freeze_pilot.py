"""Offline 32-trial freeze. Refuses unreviewed fixtures; never calls a model."""
import hashlib,json,random,re,shutil
from pathlib import Path
import catalog,output_guard
ROOT=Path(__file__).resolve().parent
FAMILIES=['conditional_preconditions','sequence_induction','relational_join','finite_map_frames']
CELLS=['shallow_shared','shallow_separate','deep_shared','deep_separate']
SYSTEM='You are completing formally verified Dafny helper proofs in one monorepo workspace. Preserve all supplied interfaces and source outside the permitted lemma bodies. Return only the requested JSON file object. The whole workspace, including providers and both clients, will be verified.'

def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def prompt(task,files):
 names=task['editable_files']
 imports={n:re.findall(r'import (\w+) = ([A-Za-z_0-9`]+)',s) for n,s in files.items()}
 lines=[f'Complete the Prove lemma body in each of: {", ".join(names)}.',
 'Return a single JSON object whose exact keys are these filenames and whose values are the COMPLETE file strings. Preserve every byte outside each Prove body, including whitespace, imports, exports, attributes, contracts and decreases. Do not return any other files.',
 'Allowed proof-body syntax: if/else, assert, task-allowed lemma calls; parameter variables, integer/Boolean literals, + and -, comparisons, &&, ||, ==> and !; parentheses, length |s|, empty sequence [], sequence indexing/slicing, and map updates m[k := v]. No comments, declarations, loops, quantifiers, assume, reveal, attributes, assert-by blocks, or arbitrary qualified calls. Assertions and calls still must verify. Copying proof text between editable bodies is permitted; delegating to another helper is not.',
 'Allowed parameters: '+', '.join(task['variables'])+'.',
 'Allowed statement calls (name: arity): '+json.dumps(task['calls'],sort_keys=True)+'.',
 'Allowed pure expression calls (name: arity): '+json.dumps(output_guard.PURE[task['family']],sort_keys=True)+'.',
 'Output limits: 256 KiB response; 64 KiB and 8192 tokens per body; 256 statements; expression depth 32 and statement depth 24.',
 'Entry point: All.dfy. Each listed file belongs to this same monorepo workspace. Imports and includes below are structural context, not proof steps.',
 'Declared file map: '+json.dumps({'includes':task['includes'],'imports':imports},sort_keys=True),
 'Full source:']
 for n,s in sorted(files.items()):lines+=['\nFILE '+n+'\n```dafny\n'+s+'```']
 return '\n\n'.join(lines)+'\n'

def gate(tasks):
 selected=[]
 for t in tasks:
  folder=ROOT/t['fixture_root'];report=json.loads((folder/'results-review.json').read_text())
  rows=report.get('results',report.get('rows'))
  rows=[r for r in rows if r['task_id']==t['task_id']]
  expected=json.loads((folder/'checks.json').read_text());expected=[c for c in expected if c['task_id']==t['task_id']]
  if len(rows)!=len(expected):raise ValueError('Missing reviewed controls')
  if 'results' in report and not all(r['matched'] for r in rows):raise ValueError('Unvalidated task: '+t['task_id'])
  if 'rows' in report and not report['all_expected']:raise ValueError('Unvalidated legacy task')
  fs=catalog.sources(t)
  if {n:sha(s.encode()) for n,s in fs.items()}!=t['source_sha256']:raise ValueError('Seed drift')
  ref=catalog.sources(t,'reference')
  output_guard.validate_files({n:ref[n] for n in t['editable_files']},fs,t)
  selected.append(dict(task_id=t['task_id'],review=str((folder/'results-review.json').relative_to(ROOT)),review_sha256=sha((folder/'results-review.json').read_bytes()),control_count=len(rows),job_id=report['job_id']))
 return selected

def main():
 tasks=catalog.tasks()
 if len(tasks)!=16 or len({t['task_id'] for t in tasks})!=16:raise ValueError('Catalog size')
 reviewed=gate(tasks);out=ROOT/'frozen-001';out.mkdir(exist_ok=False)
 settings=dict(model_id='global.anthropic.claude-opus-4-5-20251101-v1:0',region='us-east-1',inference_config={'maxTokens':4096,'temperature':1.0},max_calls=32,independent_samples_per_variant=2,attempts_per_sample=1,automatic_retries=False,reassign_unused=False,status='FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION',context='full_source_plus_declared_file_map',parser='calibration-body-v1',verify_timeout_seconds=30,stop_rule='Stop on transport ambiguity, source drift, verifier infrastructure errors or interrupted dispatch; no automatic recovery. Parser/guard/proof failures are completed outcomes.')
 save(out/'settings.json',settings);save(out/'preflight-gate.json',reviewed)
 (out/'system.txt').write_text(SYSTEM+'\n')
 code=out/'guard';code.mkdir()
 for n in ['output_guard.py','catalog.py','test_output_guard.py','freeze_pilot.py','test_freeze.py']:shutil.copy2(ROOT/n,code/n)
 task_metadata=[]
 for t in tasks:
  p=out/'tasks'/t['task_id'];p.mkdir(parents=True);fs=catalog.sources(t)
  for n,s in fs.items():(p/n).write_text(s)
  text=prompt(t,fs);(p/'prompt.txt').write_text(text)
  meta={**t,'prompt_sha256':sha(text.encode()),'prompt_utf8_bytes':len(text.encode()),'editable_body_count':len(t['editable_files'])}
  save(p/'task.json',meta);task_metadata.append(meta)
 save(out/'tasks.json',task_metadata)
 rng=random.Random(20261028);families=FAMILIES.copy();rng.shuffle(families)
 rows={f:i for i,f in enumerate(families)};trials=[]
 for sample in [1,2]:
  family_order=families if sample==1 else families[::-1]
  for position in range(4):
   for family in family_order:
    row=rows[family];cells=CELLS[row:]+CELLS[:row]
    if sample==2:cells=cells[::-1]
    cell=cells[position];t=next(t for t in task_metadata if t['family']==family and t['depth']+'_'+t['sharing']==cell)
    trials.append(dict(trial_id='trial-%02d'%(len(trials)+1),task_id=t['task_id'],family=family,cell=cell,sample=sample,latin_row=row,within_family_position=position,prompt_path='tasks/'+t['task_id']+'/prompt.txt',prompt_sha256=t['prompt_sha256'],system_path='system.txt',system_sha256=sha((SYSTEM+'\n').encode()),fresh_context=True,feedback=False))
 save(out/'trials.json',trials)
 save(out/'order-design.json',dict(seed=20261028,cells=CELLS,latin_row_by_family=rows,design='Four cyclic Latin rows once each; interleave families; reverse cell and family order for sample two. No output is shared across samples.'))
 save(out/'freeze.json',dict(status='FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION',model_calls=0,trial_count=32,files={str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}))
 print('Frozen 32 proposed independent trials; zero model calls')
if __name__=='__main__':main()
