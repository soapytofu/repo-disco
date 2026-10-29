"""Freeze a new offline proposal only after full source/evidence validation.
No provider, credential, queue or submission code. Cannot authorize model calls.
"""
import hashlib,json,random,re,shutil,sys
from pathlib import Path
import catalog_v2
ROOT=Path(__file__).resolve().parent
# Unified v2.1 protocol is additive; do not overwrite the map experiment's code.
sys.path.insert(0,str(ROOT/'remaining-families-001'))
import body_protocol,grammar
FAMILIES=['conditional_preconditions','sequence_offset','interval_witness','map_transfer']
CELLS=['shallow_shared','shallow_separate','deep_shared','deep_separate']
SYSTEM='Complete Dafny helper proof bodies in one monorepo workspace. Return only the requested JSON object of body strings, without outer lemma braces or file declarations. The host preserves all supplied interfaces and assembles files. The entire workspace, including providers and both clients, will be verified.'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def load(p):return json.loads(p.read_text())

def prompt(t,files):
 mapping={'includes':{n:re.findall(r'include "([^"]+)"',s) for n,s in files.items()},'imports':{n:re.findall(r'import (\w+) = ([A-Za-z_0-9`]+)',s) for n,s in files.items()}}
 lines=[f'Complete the Prove lemma body in each of: {", ".join(t["editable_files"])}.',
 'Return one JSON object with exactly these filenames as keys and proof BODY STRINGS as values. Do not include the surrounding lemma braces, signature, contract, imports, or whole file. The host inserts the strings inside the existing body braces. JSON escaping must be correct and decoded exactly once. Return plain JSON or one whole-response ```json fence; no prose, extra keys, duplicate keys or other wrappers.',
 'Allowed syntax: if/else statements, assert, listed statement calls; parameters, integer/Boolean literals, + and -, comparisons, &&, ||, ==> and !; parentheses, length |s|, empty sequence [], indexing/slicing, map updates m[k := v], and pure if CONDITION then EXPR else EXPR. No comments, declarations, assignments, loops, quantifiers, multiplication, assume, reveal, attributes, assert-by blocks or unlisted calls. Assertions and all calls must verify. Copying equivalent proof text between bodies is allowed; delegation to another helper is not.',
 'Allowed parameters: '+', '.join(t['variables'])+'.',
 'Allowed statement calls (name: arity): '+json.dumps(t['calls'],sort_keys=True)+'.',
 'Allowed pure expression calls (name: arity): '+json.dumps(grammar.PURE[t['family']],sort_keys=True)+'.',
 'Limits: 256 KiB UTF-8 response; 64 KiB/8192 tokens per body; 256 statements; expression nesting 32 and statement nesting 24. Empty bodies are syntactically accepted but must satisfy the protected contracts.',
 'Entry point: All.dfy. All listed files are one monorepo workspace. The map describes declared structure, not a proof strategy.',
 'Declared file map: '+json.dumps(mapping,sort_keys=True),'Full immutable seed context:']
 for n,s in sorted(files.items()):lines+=['FILE '+n+'\n```dafny\n'+s+'```']
 return '\n\n'.join(lines)+'\n'

def reference_payload(t,seed,ref):
 bodies={}
 for n in t['editable_files']:
  pre,suf=grammar.split_seed(seed[n]);assert ref[n].startswith(pre) and ref[n].endswith(suf)
  bodies[n]=ref[n][len(pre):-len(suf)]
 return json.dumps(bodies)

def gate(tasks):
 selected=[]
 for t in tasks:
  folder=ROOT/t['fixture_root'];report=load(folder/'results-review.json')
  checks=[c for c in load(folder/'checks.json') if c['task_id']==t['task_id']]
  reviewed=[c for c in report.get('rows',report.get('results',[])) if c['task_id']==t['task_id']]
  if len(checks)!=len(reviewed) or {c['variant'] for c in checks}!={c['variant'] for c in reviewed}:raise ValueError('Incomplete control review')
  if not all(r.get('matched',r.get('verified_source_hashes',False)) for r in reviewed):raise ValueError('Selected task has an unmatched reviewed control')
  archive=folder/'verification-001'
  archived_checks=[c for c in load(archive/'checks.json') if c['task_id']==t['task_id']]
  if checks!=archived_checks:raise ValueError('Control list drift')
  evidence=[]
  for c in checks:
   files={p.name:p.read_bytes() for p in (folder/c['path']).glob('*.dfy')}
   archived={p.name:p.read_bytes() for p in (archive/c['path']).glob('*.dfy')}
   if files!=archived or {n:sha(b) for n,b in files.items()}!=c['source_sha256']:raise ValueError('Verified source drift')
   log=archive/(t['task_id']+'-'+c['variant']+'.json');v=load(log)
   if v['source_sha256']!=c['source_sha256'] or not v['matched']:raise ValueError('Verifier mismatch')
   if v['expected']!=c['expected'] or '--verify-included-files' not in v['command']:raise ValueError('Verifier scope mismatch')
   expected_code={'success':0,'proof_failure':4,'termination_failure':4,'resolution_failure':2}[c['expected']]
   if v['exit_code']!=expected_code:raise ValueError('Unexpected exit')
   text=(v['stdout']+'\n'+v['stderr']).lower()
   if c['expected']=='proof_failure' and (not any(s in text for s in ['postcondition','precondition','assertion','for this call']) or 'parse errors' in text):raise ValueError('Not a proof diagnostic')
   if c['expected']=='termination_failure' and not any(s in text for s in ['termination','decreases']):raise ValueError('Not a termination diagnostic')
   if c['expected']=='resolution_failure' and ('direct' not in text or not any(s in text for s in ['unresolved','not found','not a member','does not exist'])):raise ValueError('Not a hidden-helper diagnostic')
   evidence.append(dict(variant=c['variant'],expected=c['expected'],source_sha256=c['source_sha256'],log_path=str(log.relative_to(ROOT.parent.parent)),log_sha256=sha(log.read_bytes())))
  seed=catalog_v2.sources(t);ref=catalog_v2.sources(t,'reference')
  if {n:sha(s.encode()) for n,s in seed.items()}!=t['source_sha256']:raise ValueError('Seed hash drift')
  candidate,decision=body_protocol.parse_response(reference_payload(t,seed,ref),seed,t)
  if candidate!=ref:raise ValueError('Protocol does not reconstruct verified source')
  selected.append(dict(task_id=t['task_id'],review_path=str((folder/'results-review.json').resolve().relative_to(ROOT.parent.parent.resolve())),review_sha256=sha((folder/'results-review.json').read_bytes()),job_id=report['job_id'],whole_original_run_all_expected=report['all_expected'],selected_controls_all_expected=True,control_count=len(checks),evidence=evidence,reference_body_protocol=decision['version']))
 return selected

def make_order(metadata):
 rng=random.Random(20261029);families=FAMILIES.copy();rng.shuffle(families);rows={f:i for i,f in enumerate(families)};trials=[]
 for sample in [1,2]:
  for pos in range(4):
   for family in (families if sample==1 else families[::-1]):
    row=rows[family];cells=CELLS[row:]+CELLS[:row]
    if sample==2:cells=cells[::-1]
    cell=cells[pos];t=next(t for t in metadata if t['family']==family and t['depth']+'_'+t['sharing']==cell)
    trials.append(dict(trial_id='trial-%02d'%(len(trials)+1),task_id=t['task_id'],family=family,cell=cell,sample=sample,latin_row=row,within_family_position=pos,prompt_path='tasks/'+t['task_id']+'/prompt.txt',prompt_sha256=t['prompt_sha256'],system_path='system.txt',system_sha256=sha((SYSTEM+'\n').encode()),fresh_context=True,feedback=False))
 return trials,dict(seed=20261029,cells=CELLS,latin_row_by_family=rows,design='One cyclic Latin row per family; interleave families; reverse cell and family order for sample 2. Independent contexts; no feedback.')

def main():
 tasks=catalog_v2.tasks()
 if len(tasks)!=16 or len({t['task_id'] for t in tasks})!=16:raise ValueError('Expected 16 unique tasks')
 reviews=gate(tasks) # Must pass before any freeze is created.
 out=ROOT/'frozen-001';out.mkdir(exist_ok=False)
 previous=load(ROOT.parent/'monorepo-calibration-pilot-001/frozen-001/settings.json')
 settings={**previous,'parser':body_protocol.VERSION,'status':'FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION','max_calls':32,'model_calls_made':0,'output_scope':'JSON helper body strings; immutable host assembly','context':'full_source_plus_declared_file_map'}
 save(out/'settings.json',settings);save(out/'preflight-gate.json',reviews);(out/'system.txt').write_text(SYSTEM+'\n')
 (out/'guard').mkdir()
 for n in ['body_protocol.py','grammar.py']:shutil.copy2(ROOT/'remaining-families-001'/n,out/'guard'/n)
 metadata=[]
 for t in tasks:
  fs=catalog_v2.sources(t);text=prompt(t,fs);dest=out/'tasks'/t['task_id'];dest.mkdir(parents=True)
  for n,s in fs.items():(dest/n).write_text(s)
  (dest/'prompt.txt').write_text(text)
  meta={**t,'editable_scope':'Prove body strings only; body-json-v2.1','prompt_sha256':sha(text.encode()),'prompt_utf8_bytes':len(text.encode()),'editable_body_count':len(t['editable_files']),'client_count':2,'repository_boundary':'single_monorepo_workspace'}
  save(dest/'task.json',meta);metadata.append(meta)
 save(out/'tasks.json',metadata);trials,order=make_order(metadata);save(out/'trials.json',trials);save(out/'order-design.json',order)
 (out/'preparation').mkdir()
 for n in ['catalog_v2.py','freeze_pilot.py','test_freeze_v2.py']:shutil.copy2(ROOT/n,out/'preparation'/n)
 save(out/'freeze.json',dict(status='FROZEN_PROPOSAL_NO_MODEL_AUTHORIZATION',model_calls=0,trial_count=32,files={str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob('*')) if p.is_file()}))
 print('Frozen 32 proposed independent trials after',sum(r['control_count'] for r in reviews),'reviewed controls; zero model calls')
if __name__=='__main__':main()
